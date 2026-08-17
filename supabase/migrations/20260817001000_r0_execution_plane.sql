-- R0 execution plane: control-plane tables, forecast-versioned temporal storage,
-- and a dedicated least-privilege collector login.
--
-- Design notes that are load bearing:
--   * The execution plane lives outside `public`. Supabase only exposes `public`
--     and `graphql_public` through PostgREST, so operational tables are never
--     reachable with an anon or authenticated JWT.
--   * `zonepilot_temporal.feature_records` is append-only by construction: the
--     natural key includes `issued_at`, so a forecast re-issued for the same
--     `valid_at` becomes a NEW row instead of overwriting the earlier issue.
--   * The collector login gets INSERT/SELECT (plus UPDATE only where a run has to
--     be closed out). It never receives DELETE, TRUNCATE, DDL, or superuser.

-- ---------------------------------------------------------------------------
-- 0. Schemas
-- ---------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS zonepilot_exec;
CREATE SCHEMA IF NOT EXISTS zonepilot_temporal;

COMMENT ON SCHEMA zonepilot_exec IS
  'R0 execution control plane: runs, checkpoints, provider cursors, leases, artifacts.';
COMMENT ON SCHEMA zonepilot_temporal IS
  'Availability-aware, forecast-versioned observation storage (zonepilot.temporal_feature).';

REVOKE CREATE ON SCHEMA zonepilot_exec FROM PUBLIC;
REVOKE CREATE ON SCHEMA zonepilot_temporal FROM PUBLIC;
REVOKE ALL ON SCHEMA zonepilot_exec FROM PUBLIC;
REVOKE ALL ON SCHEMA zonepilot_temporal FROM PUBLIC;

-- ---------------------------------------------------------------------------
-- 1. Enumerations
-- ---------------------------------------------------------------------------

-- Strict run state machine. Every acquisition attempt ends in exactly one of
-- the terminal states; PENDING and RUNNING are the only non-terminal states.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = 'run_status' AND n.nspname = 'zonepilot_exec'
  ) THEN
    CREATE TYPE zonepilot_exec.run_status AS ENUM (
      'PENDING',
      'RUNNING',
      'SUCCESS',
      'PARTIAL',
      'FAILED',
      'DEGRADED',
      'SKIPPED_NO_CHANGE',
      'AUTH_REQUIRED',
      'RATE_LIMITED'
    );
  END IF;
END
$$;

-- Mirrors services/temporal/contracts.py::EvidenceClass exactly (nine values).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = 'evidence_class' AND n.nspname = 'zonepilot_temporal'
  ) THEN
    CREATE TYPE zonepilot_temporal.evidence_class AS ENUM (
      'OBSERVED',
      'PUBLIC_OFFICIAL',
      'PUBLIC_GEOGRAPHIC',
      'PROVIDER_ESTIMATED',
      'DERIVED',
      'SIMULATED',
      'ASSUMPTION',
      'STAGING_DO_NOT_USE',
      'TEST_ONLY'
    );
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION zonepilot_exec.is_terminal_status(status zonepilot_exec.run_status)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT status NOT IN ('PENDING', 'RUNNING');
$$;

-- ---------------------------------------------------------------------------
-- 2. collection_runs -- append-only audit log of every acquisition attempt
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS zonepilot_exec.collection_runs (
  run_id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider                 text NOT NULL CHECK (length(provider) BETWEEN 1 AND 128),
  dataset_id               text NOT NULL CHECK (length(dataset_id) BETWEEN 1 AND 128),
  dataset_version          text NOT NULL CHECK (length(dataset_version) BETWEEN 1 AND 128),
  provider_version         text NOT NULL CHECK (length(provider_version) BETWEEN 1 AND 128),
  -- Logical slot the run is trying to fill, e.g. the provider forecast cycle.
  logical_interval         text NOT NULL CHECK (length(logical_interval) BETWEEN 1 AND 256),
  -- sha256 over the canonicalised provider request (URL + sorted params, no secrets).
  request_fingerprint      char(64) NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
  status                   zonepilot_exec.run_status NOT NULL DEFAULT 'PENDING',
  runner_id                text NOT NULL CHECK (length(runner_id) BETWEEN 1 AND 256),
  environment              text NOT NULL CHECK (environment IN ('staging', 'production', 'local')),
  public_code_sha          char(40) CHECK (public_code_sha IS NULL OR public_code_sha ~ '^[0-9a-f]{40}$'),
  workflow_repository      text,
  workflow_run_id          text,
  workflow_run_attempt     integer CHECK (workflow_run_attempt IS NULL OR workflow_run_attempt >= 1),
  started_at               timestamptz NOT NULL DEFAULT now(),
  heartbeat_at             timestamptz,
  finished_at              timestamptz,
  records_written          integer NOT NULL DEFAULT 0 CHECK (records_written >= 0),
  records_deduplicated     integer NOT NULL DEFAULT 0 CHECK (records_deduplicated >= 0),
  failure_code             text CHECK (failure_code IS NULL OR failure_code ~ '^[A-Z0-9_]{1,64}$'),
  failure_message          text CHECK (failure_message IS NULL OR length(failure_message) <= 512),
  metadata                 jsonb NOT NULL DEFAULT '{}'::jsonb,

  CONSTRAINT collection_runs_terminal_requires_finish CHECK (
    zonepilot_exec.is_terminal_status(status) = (finished_at IS NOT NULL)
  ),
  CONSTRAINT collection_runs_finish_after_start CHECK (
    finished_at IS NULL OR finished_at >= started_at
  ),
  CONSTRAINT collection_runs_failure_fields_agree CHECK (
    (status IN ('FAILED', 'PARTIAL', 'DEGRADED', 'AUTH_REQUIRED', 'RATE_LIMITED'))
    OR (failure_code IS NULL AND failure_message IS NULL)
  )
);

COMMENT ON TABLE zonepilot_exec.collection_runs IS
  'One row per acquisition attempt. Append-only: retries add rows, they never rewrite history.';
COMMENT ON COLUMN zonepilot_exec.collection_runs.records_deduplicated IS
  'Rows the run re-derived but did not insert because the identical forecast issue already existed.';

CREATE INDEX IF NOT EXISTS collection_runs_slot_idx
  ON zonepilot_exec.collection_runs (provider, dataset_id, logical_interval, started_at DESC);
CREATE INDEX IF NOT EXISTS collection_runs_open_idx
  ON zonepilot_exec.collection_runs (status, heartbeat_at)
  WHERE status IN ('PENDING', 'RUNNING');

-- Enforce the state machine on transitions. Terminal states are final, and the
-- only legal moves out of PENDING/RUNNING are the ones listed here.
CREATE OR REPLACE FUNCTION zonepilot_exec.enforce_run_transition()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
  IF NEW.run_id <> OLD.run_id
     OR NEW.provider <> OLD.provider
     OR NEW.dataset_id <> OLD.dataset_id
     OR NEW.logical_interval <> OLD.logical_interval
     OR NEW.request_fingerprint <> OLD.request_fingerprint
     OR NEW.started_at <> OLD.started_at THEN
    RAISE EXCEPTION 'collection_runs identity and start are immutable (run %)', OLD.run_id
      USING ERRCODE = 'check_violation';
  END IF;

  IF NEW.status = OLD.status THEN
    RETURN NEW;
  END IF;

  IF zonepilot_exec.is_terminal_status(OLD.status) THEN
    RAISE EXCEPTION 'run % is already terminal in state %, refusing transition to %',
      OLD.run_id, OLD.status, NEW.status
      USING ERRCODE = 'check_violation';
  END IF;

  IF OLD.status = 'PENDING' AND NEW.status NOT IN (
       'RUNNING', 'FAILED', 'SKIPPED_NO_CHANGE', 'AUTH_REQUIRED', 'RATE_LIMITED'
     ) THEN
    RAISE EXCEPTION 'illegal transition PENDING -> % for run %', NEW.status, OLD.run_id
      USING ERRCODE = 'check_violation';
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS collection_runs_transition ON zonepilot_exec.collection_runs;
CREATE TRIGGER collection_runs_transition
  BEFORE UPDATE ON zonepilot_exec.collection_runs
  FOR EACH ROW EXECUTE FUNCTION zonepilot_exec.enforce_run_transition();

-- ---------------------------------------------------------------------------
-- 3. collection_checkpoints -- resumable progress inside a single run
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS zonepilot_exec.collection_checkpoints (
  checkpoint_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id            uuid NOT NULL REFERENCES zonepilot_exec.collection_runs (run_id) ON DELETE CASCADE,
  provider          text NOT NULL,
  dataset_id        text NOT NULL,
  sequence_no       integer NOT NULL CHECK (sequence_no >= 0),
  checkpoint_key    text NOT NULL CHECK (length(checkpoint_key) BETWEEN 1 AND 256),
  cursor_value      jsonb NOT NULL DEFAULT '{}'::jsonb,
  status            zonepilot_exec.run_status NOT NULL,
  records_written   integer NOT NULL DEFAULT 0 CHECK (records_written >= 0),
  created_at        timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT collection_checkpoints_sequence_unique UNIQUE (run_id, sequence_no),
  CONSTRAINT collection_checkpoints_key_unique UNIQUE (run_id, checkpoint_key)
);

CREATE INDEX IF NOT EXISTS collection_checkpoints_dataset_idx
  ON zonepilot_exec.collection_checkpoints (provider, dataset_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- 4. provider_states -- durable cursors that survive between runs
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS zonepilot_exec.provider_states (
  provider          text NOT NULL,
  dataset_id        text NOT NULL,
  state_key         text NOT NULL,
  state_value       jsonb NOT NULL,
  updated_at        timestamptz NOT NULL DEFAULT now(),
  updated_by_run_id uuid REFERENCES zonepilot_exec.collection_runs (run_id) ON DELETE SET NULL,

  PRIMARY KEY (provider, dataset_id, state_key)
);

COMMENT ON TABLE zonepilot_exec.provider_states IS
  'Last-known provider cursor (e.g. last observed forecast cycle) keyed per provider+dataset.';

-- ---------------------------------------------------------------------------
-- 5. scheduler_locks -- real lease semantics with fencing
-- ---------------------------------------------------------------------------

-- `lock_name` is the primary key, which is the UNIQUE constraint that makes a
-- double claim impossible: two concurrent claimants contend on the same row,
-- and the loser's ON CONFLICT branch re-evaluates the lease predicate against
-- the winner's freshly written expiry, so it returns zero rows.
CREATE TABLE IF NOT EXISTS zonepilot_exec.scheduler_locks (
  lock_name     text PRIMARY KEY CHECK (length(lock_name) BETWEEN 1 AND 256),
  lease_holder  text NOT NULL CHECK (length(lease_holder) BETWEEN 1 AND 256),
  fence_token   bigint NOT NULL CHECK (fence_token >= 1),
  acquired_at   timestamptz NOT NULL,
  expires_at    timestamptz NOT NULL,
  released_at   timestamptz,
  run_id        uuid REFERENCES zonepilot_exec.collection_runs (run_id) ON DELETE SET NULL,

  CONSTRAINT scheduler_locks_lease_is_forward CHECK (expires_at > acquired_at),
  CONSTRAINT scheduler_locks_release_after_acquire CHECK (
    released_at IS NULL OR released_at >= acquired_at
  )
);

COMMENT ON TABLE zonepilot_exec.scheduler_locks IS
  'Leased mutual exclusion. A crashed holder''s lease expires and becomes reclaimable; '
  'fence_token increments on every (re)acquisition so a resurrected zombie is detectable.';

-- Atomically acquire or reclaim a lease. Returns the fence token on success and
-- no row at all when another holder still owns a live lease.
CREATE OR REPLACE FUNCTION zonepilot_exec.acquire_scheduler_lock(
  p_lock_name text,
  p_lease_holder text,
  p_lease_seconds integer,
  p_run_id uuid DEFAULT NULL
)
RETURNS bigint
LANGUAGE sql
SET search_path = pg_catalog, pg_temp
AS $$
  INSERT INTO zonepilot_exec.scheduler_locks AS lock_row
        (lock_name, lease_holder, fence_token, acquired_at, expires_at, released_at, run_id)
  VALUES (p_lock_name, p_lease_holder, 1, now(),
          now() + make_interval(secs => p_lease_seconds), NULL, p_run_id)
  ON CONFLICT (lock_name) DO UPDATE
     SET lease_holder = excluded.lease_holder,
         fence_token  = lock_row.fence_token + 1,
         acquired_at  = excluded.acquired_at,
         expires_at   = excluded.expires_at,
         released_at  = NULL,
         run_id       = excluded.run_id
   WHERE lock_row.released_at IS NOT NULL
      OR lock_row.expires_at <= now()
  RETURNING lock_row.fence_token;
$$;

-- Release is fenced: only the current holder at the current token may release.
CREATE OR REPLACE FUNCTION zonepilot_exec.release_scheduler_lock(
  p_lock_name text,
  p_lease_holder text,
  p_fence_token bigint
)
RETURNS boolean
LANGUAGE sql
SET search_path = pg_catalog, pg_temp
AS $$
  WITH released AS (
    UPDATE zonepilot_exec.scheduler_locks
       SET released_at = now()
     WHERE lock_name = p_lock_name
       AND lease_holder = p_lease_holder
       AND fence_token = p_fence_token
       AND released_at IS NULL
    RETURNING 1
  )
  SELECT EXISTS (SELECT 1 FROM released);
$$;

-- ---------------------------------------------------------------------------
-- 6. artifact_registry -- content-addressed evidence for every retained payload
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS zonepilot_exec.artifact_registry (
  artifact_id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  artifact_hash             char(64) NOT NULL CHECK (artifact_hash ~ '^[0-9a-f]{64}$'),
  run_id                    uuid NOT NULL REFERENCES zonepilot_exec.collection_runs (run_id) ON DELETE CASCADE,
  provider                  text NOT NULL,
  provider_version          text NOT NULL,
  dataset_id                text NOT NULL,
  dataset_version           text NOT NULL,
  layer                     text NOT NULL CHECK (layer IN ('RAW', 'BRONZE', 'SILVER', 'GOLD', 'MANIFEST')),
  media_type                text NOT NULL,
  byte_size                 bigint NOT NULL CHECK (byte_size >= 0),
  record_count              integer NOT NULL DEFAULT 0 CHECK (record_count >= 0),
  uri                       text,
  request_fingerprint       char(64) CHECK (request_fingerprint IS NULL OR request_fingerprint ~ '^[0-9a-f]{64}$'),
  issued_at                 timestamptz NOT NULL,
  information_available_at  timestamptz NOT NULL,
  retrieved_at              timestamptz NOT NULL,
  evidence_class            zonepilot_temporal.evidence_class NOT NULL,
  recorded_at               timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT artifact_registry_unique_per_run UNIQUE (run_id, artifact_hash, layer),
  CONSTRAINT artifact_registry_availability_follows_issue CHECK (
    information_available_at >= issued_at
  ),
  CONSTRAINT artifact_registry_retrieval_follows_availability CHECK (
    retrieved_at >= information_available_at
  )
);

CREATE INDEX IF NOT EXISTS artifact_registry_hash_idx
  ON zonepilot_exec.artifact_registry (artifact_hash);

-- ---------------------------------------------------------------------------
-- 7. Temporal storage -- forecast-versioned, availability-aware
-- ---------------------------------------------------------------------------

-- feature_units is identical across every record of a dataset version, so it is
-- stored once and referenced by content hash rather than copied per row.
CREATE TABLE IF NOT EXISTS zonepilot_temporal.feature_unit_sets (
  unit_set_id  char(64) PRIMARY KEY CHECK (unit_set_id ~ '^[0-9a-f]{64}$'),
  units        jsonb NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zonepilot_temporal.feature_records (
  record_id                 text PRIMARY KEY CHECK (length(record_id) BETWEEN 1 AND 256),
  dataset_id                text NOT NULL CHECK (length(dataset_id) BETWEEN 1 AND 128),
  dataset_version           text NOT NULL CHECK (length(dataset_version) BETWEEN 1 AND 128),
  schema_name               text NOT NULL DEFAULT 'zonepilot.temporal_feature',
  schema_version            text NOT NULL DEFAULT '1.0.0',
  entity_id                 text NOT NULL CHECK (length(entity_id) BETWEEN 1 AND 128),
  zone_id                   text NOT NULL CHECK (length(zone_id) BETWEEN 1 AND 128),

  -- Availability-aware timeline. All five are mandatory.
  event_time                timestamptz NOT NULL,
  issued_at                 timestamptz NOT NULL,
  information_available_at  timestamptz NOT NULL,
  valid_at                  timestamptz NOT NULL,
  retrieved_at              timestamptz NOT NULL,

  provider                  text NOT NULL CHECK (length(provider) BETWEEN 1 AND 128),
  provider_version          text NOT NULL CHECK (length(provider_version) BETWEEN 1 AND 128),
  source                    text NOT NULL,
  source_version            text NOT NULL,
  evidence_class            zonepilot_temporal.evidence_class NOT NULL,

  features                  jsonb NOT NULL,
  feature_unit_set_id       char(64) NOT NULL
                              REFERENCES zonepilot_temporal.feature_unit_sets (unit_set_id),

  -- Evidence chain.
  run_id                    uuid NOT NULL REFERENCES zonepilot_exec.collection_runs (run_id),
  artifact_hash             char(64) NOT NULL CHECK (artifact_hash ~ '^[0-9a-f]{64}$'),
  request_fingerprint       char(64) NOT NULL CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
  ingested_at               timestamptz NOT NULL DEFAULT now(),

  -- The hard leakage boundary: a value can never be known before it was issued,
  -- and can never have been retrieved before it was available.
  CONSTRAINT feature_records_availability_follows_issue CHECK (
    information_available_at >= issued_at
  ),
  CONSTRAINT feature_records_retrieval_follows_availability CHECK (
    retrieved_at >= information_available_at
  ),
  CONSTRAINT feature_records_features_are_objects CHECK (
    jsonb_typeof(features) = 'object' AND features <> '{}'::jsonb
  ),

  -- Forecast versioning. `issued_at` is part of the key, so re-issuing a
  -- forecast for the same valid_at inserts an additional version instead of
  -- replacing the earlier one. Two runs inside the same provider issue cycle
  -- collide here, which is what makes re-runs idempotent.
  CONSTRAINT feature_records_forecast_version_unique UNIQUE (
    dataset_id, provider, provider_version, zone_id, valid_at, issued_at
  )
);

COMMENT ON TABLE zonepilot_temporal.feature_records IS
  'Append-only temporal observations. An issued forecast is never overwritten: '
  'issued_at participates in the natural key, so each provider issue cycle keeps its own row.';
COMMENT ON COLUMN zonepilot_temporal.feature_records.issued_at IS
  'Instant the provider issued this value (for NWP output, the model cycle initialisation time).';
COMMENT ON COLUMN zonepilot_temporal.feature_records.information_available_at IS
  'Instant the value first became knowable to ZonePilot. Hard leakage boundary; always >= issued_at.';

-- Point-in-time reads: "latest issue at or before decision_time for this cell".
CREATE INDEX IF NOT EXISTS feature_records_point_in_time_idx
  ON zonepilot_temporal.feature_records
     (dataset_id, zone_id, valid_at, information_available_at DESC, issued_at DESC);
CREATE INDEX IF NOT EXISTS feature_records_run_idx
  ON zonepilot_temporal.feature_records (run_id);
CREATE INDEX IF NOT EXISTS feature_records_issue_cycle_idx
  ON zonepilot_temporal.feature_records (provider, dataset_id, issued_at DESC);

-- Immutability: once an issue is recorded, it is evidence. Nothing rewrites it.
CREATE OR REPLACE FUNCTION zonepilot_temporal.reject_feature_record_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
  RAISE EXCEPTION 'zonepilot_temporal.feature_records is append-only (attempted % on %)',
    TG_OP, COALESCE(OLD.record_id, '?')
    USING ERRCODE = 'check_violation';
END;
$$;

DROP TRIGGER IF EXISTS feature_records_append_only ON zonepilot_temporal.feature_records;
CREATE TRIGGER feature_records_append_only
  BEFORE UPDATE OR DELETE ON zonepilot_temporal.feature_records
  FOR EACH ROW EXECUTE FUNCTION zonepilot_temporal.reject_feature_record_mutation();

-- ---------------------------------------------------------------------------
-- 8. Dedicated least-privilege collector login
-- ---------------------------------------------------------------------------

-- No password is set here. The owner sets it out of band (a SCRAM verifier is
-- preferred so the plaintext never leaves the operator's machine). A role with
-- LOGIN and no password cannot authenticate, so this is fail-closed.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zonepilot_r0_collector') THEN
    CREATE ROLE zonepilot_r0_collector WITH
      LOGIN
      NOSUPERUSER
      NOCREATEDB
      NOCREATEROLE
      NOINHERIT
      NOREPLICATION
      NOBYPASSRLS
      CONNECTION LIMIT 8;
  END IF;
END
$$;

COMMENT ON ROLE zonepilot_r0_collector IS
  'R0 acquisition login. Append rows and close out its own runs; no DELETE, TRUNCATE, or DDL.';

-- Connect + schema visibility only.
GRANT USAGE ON SCHEMA zonepilot_exec TO zonepilot_r0_collector;
GRANT USAGE ON SCHEMA zonepilot_temporal TO zonepilot_r0_collector;

-- Append-only data plane.
GRANT SELECT, INSERT ON zonepilot_temporal.feature_records      TO zonepilot_r0_collector;
GRANT SELECT, INSERT ON zonepilot_temporal.feature_unit_sets    TO zonepilot_r0_collector;
GRANT SELECT, INSERT ON zonepilot_exec.artifact_registry        TO zonepilot_r0_collector;
GRANT SELECT, INSERT ON zonepilot_exec.collection_checkpoints   TO zonepilot_r0_collector;

-- Control plane needs UPDATE to close a run out and to move a lease forward.
GRANT SELECT, INSERT, UPDATE ON zonepilot_exec.collection_runs  TO zonepilot_r0_collector;
GRANT SELECT, INSERT, UPDATE ON zonepilot_exec.provider_states  TO zonepilot_r0_collector;
GRANT SELECT, INSERT, UPDATE ON zonepilot_exec.scheduler_locks  TO zonepilot_r0_collector;

GRANT EXECUTE ON FUNCTION zonepilot_exec.acquire_scheduler_lock(text, text, integer, uuid)
  TO zonepilot_r0_collector;
GRANT EXECUTE ON FUNCTION zonepilot_exec.release_scheduler_lock(text, text, bigint)
  TO zonepilot_r0_collector;
GRANT EXECUTE ON FUNCTION zonepilot_exec.is_terminal_status(zonepilot_exec.run_status)
  TO zonepilot_r0_collector;

-- Every identifier above uses uuid/text keys, so there is nothing to grant today.
-- The default privilege keeps a future serial column from silently breaking the
-- collector without also handing it rights on anything else.
ALTER DEFAULT PRIVILEGES IN SCHEMA zonepilot_exec
  GRANT USAGE, SELECT ON SEQUENCES TO zonepilot_r0_collector;
ALTER DEFAULT PRIVILEGES IN SCHEMA zonepilot_temporal
  GRANT USAGE, SELECT ON SEQUENCES TO zonepilot_r0_collector;

-- Explicitly deny everything else, including the PostgREST-facing roles.
DO $$
DECLARE
  target text;
BEGIN
  FOREACH target IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = target) THEN
      EXECUTE format('REVOKE ALL ON SCHEMA zonepilot_exec FROM %I', target);
      EXECUTE format('REVOKE ALL ON SCHEMA zonepilot_temporal FROM %I', target);
      EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA zonepilot_exec FROM %I', target);
      EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA zonepilot_temporal FROM %I', target);
    END IF;
  END LOOP;
END
$$;

REVOKE ALL ON ALL TABLES IN SCHEMA zonepilot_exec FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA zonepilot_temporal FROM PUBLIC;

-- ---------------------------------------------------------------------------
-- 9. Read helper: the point-in-time view the forecaster will consume
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION zonepilot_temporal.features_as_of(
  p_dataset_id text,
  p_decision_time timestamptz,
  p_valid_from timestamptz,
  p_valid_to timestamptz
)
RETURNS SETOF zonepilot_temporal.feature_records
LANGUAGE sql
STABLE
SET search_path = pg_catalog, pg_temp
AS $$
  SELECT DISTINCT ON (zone_id, valid_at) *
    FROM zonepilot_temporal.feature_records
   WHERE dataset_id = p_dataset_id
     AND information_available_at <= p_decision_time
     AND valid_at >= p_valid_from
     AND valid_at < p_valid_to
   ORDER BY zone_id, valid_at, issued_at DESC, information_available_at DESC;
$$;

COMMENT ON FUNCTION zonepilot_temporal.features_as_of(text, timestamptz, timestamptz, timestamptz) IS
  'Leakage-safe read: the newest issue that was already available at p_decision_time.';

GRANT EXECUTE ON FUNCTION
  zonepilot_temporal.features_as_of(text, timestamptz, timestamptz, timestamptz)
  TO zonepilot_r0_collector;
