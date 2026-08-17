-- ZonePilot temporal correctness and workspace tenancy.
--
-- Two defects are closed here.
--
-- 1. services/temporal/contracts.py defines a leakage-safe record carrying
--    event_time, issued_at, valid_at, retrieved_at and information_available_at,
--    and enforces information_available_at <= decision_time. The observation
--    tables carried none of those columns, so data written through them could
--    not support a point-in-time join no matter how strict the Python contract
--    was. The contract guarded nothing.
--
-- 2. The evidence taxonomy existed only as a Python enum. Nothing in the
--    database would have rejected a TEST_ONLY row landing in an authoritative
--    table.
--
-- Tenancy is introduced in the same cycle because workspace_id appeared in no
-- migration, which made the API's workspace check unreachable: it is skipped
-- whenever the token carries no workspace claim, and no token could carry one.
--
-- Safe as a forward-only migration with NOT NULL columns and no backfill:
-- both observation tables are empty. No acquisition run has ever completed.

BEGIN;

-- ---------------------------------------------------------------------------
-- Evidence taxonomy as a database type
-- ---------------------------------------------------------------------------

CREATE TYPE zonepilot_evidence_class AS ENUM (
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

COMMENT ON TYPE zonepilot_evidence_class IS
  'Mirrors services.temporal.contracts.EvidenceClass. Authoritative observation '
  'tables reject STAGING_DO_NOT_USE and TEST_ONLY via CHECK constraint.';

CREATE TYPE zonepilot_workspace_role AS ENUM (
  'OWNER',
  'ADMIN',
  'RESEARCHER',
  'VIEWER',
  'INTEGRATION_USER',
  'COLLECTOR'
);

-- ---------------------------------------------------------------------------
-- Workspaces
-- ---------------------------------------------------------------------------

CREATE TABLE workspaces (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug        TEXT NOT NULL UNIQUE,
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT workspaces_slug_shape CHECK (slug ~ '^[a-z0-9][a-z0-9-]{1,62}$')
);

CREATE TABLE workspace_members (
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id      UUID NOT NULL,
  role         zonepilot_workspace_role NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX workspace_members_user_idx ON workspace_members (user_id);

-- SECURITY DEFINER so the membership lookup does not re-enter the RLS policy
-- that calls it. Migration 00003 already had to repair exactly that class of
-- recursion for the legacy tables.
CREATE OR REPLACE FUNCTION zonepilot_member_workspaces(target_user UUID)
RETURNS SETOF UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT workspace_id FROM workspace_members WHERE user_id = target_user;
$$;

REVOKE ALL ON FUNCTION zonepilot_member_workspaces(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION zonepilot_member_workspaces(UUID) TO authenticated;

ALTER TABLE workspaces        ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspaces_member_read ON workspaces
  FOR SELECT TO authenticated
  USING (id IN (SELECT zonepilot_member_workspaces(auth.uid())));

CREATE POLICY workspace_members_self_read ON workspace_members
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT zonepilot_member_workspaces(auth.uid())));

-- ---------------------------------------------------------------------------
-- Temporal columns on authoritative observation tables
-- ---------------------------------------------------------------------------

ALTER TABLE collector_runs
  ADD COLUMN workspace_id     UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  ADD COLUMN code_sha         TEXT,
  ADD COLUMN workflow_run_id  TEXT,
  ADD COLUMN dataset_version  TEXT;

-- weather_observations -------------------------------------------------------
ALTER TABLE weather_observations
  ADD COLUMN workspace_id             UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  ADD COLUMN zone_id                  TEXT NOT NULL,
  ADD COLUMN provider                 TEXT NOT NULL,
  ADD COLUMN provider_version         TEXT NOT NULL,
  ADD COLUMN event_time               TIMESTAMPTZ NOT NULL,
  ADD COLUMN issued_at                TIMESTAMPTZ NOT NULL,
  ADD COLUMN valid_at                 TIMESTAMPTZ NOT NULL,
  ADD COLUMN retrieved_at             TIMESTAMPTZ NOT NULL,
  ADD COLUMN information_available_at TIMESTAMPTZ NOT NULL,
  ADD COLUMN evidence_class           zonepilot_evidence_class NOT NULL,
  ADD COLUMN dataset_version          TEXT NOT NULL;

-- traffic_observations -------------------------------------------------------
ALTER TABLE traffic_observations
  ADD COLUMN workspace_id             UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  ADD COLUMN zone_id                  TEXT NOT NULL,
  ADD COLUMN provider                 TEXT NOT NULL,
  ADD COLUMN provider_version         TEXT NOT NULL,
  ADD COLUMN event_time               TIMESTAMPTZ NOT NULL,
  ADD COLUMN issued_at                TIMESTAMPTZ NOT NULL,
  ADD COLUMN valid_at                 TIMESTAMPTZ NOT NULL,
  ADD COLUMN retrieved_at             TIMESTAMPTZ NOT NULL,
  ADD COLUMN information_available_at TIMESTAMPTZ NOT NULL,
  ADD COLUMN evidence_class           zonepilot_evidence_class NOT NULL,
  ADD COLUMN dataset_version          TEXT NOT NULL;

-- ---------------------------------------------------------------------------
-- Temporal invariants
-- ---------------------------------------------------------------------------

-- An event cannot be knowable before it happens, and a payload cannot be
-- retrieved before its provider issued it. Together these make a point-in-time
-- join filtering on information_available_at leakage-safe by construction.
ALTER TABLE weather_observations
  ADD CONSTRAINT weather_information_not_before_event
    CHECK (information_available_at >= event_time),
  ADD CONSTRAINT weather_information_not_before_issue
    CHECK (information_available_at >= issued_at),
  ADD CONSTRAINT weather_retrieved_not_before_issue
    CHECK (retrieved_at >= issued_at),
  ADD CONSTRAINT weather_evidence_is_authoritative
    CHECK (evidence_class NOT IN ('STAGING_DO_NOT_USE', 'TEST_ONLY'));

ALTER TABLE traffic_observations
  ADD CONSTRAINT traffic_information_not_before_event
    CHECK (information_available_at >= event_time),
  ADD CONSTRAINT traffic_information_not_before_issue
    CHECK (information_available_at >= issued_at),
  ADD CONSTRAINT traffic_retrieved_not_before_issue
    CHECK (retrieved_at >= issued_at),
  ADD CONSTRAINT traffic_evidence_is_authoritative
    CHECK (evidence_class NOT IN ('STAGING_DO_NOT_USE', 'TEST_ONLY'));

-- ---------------------------------------------------------------------------
-- Idempotency: a provider re-run must not duplicate an observation
-- ---------------------------------------------------------------------------

CREATE UNIQUE INDEX weather_observation_identity
  ON weather_observations (workspace_id, provider, zone_id, event_time, valid_at, issued_at);

CREATE UNIQUE INDEX traffic_observation_identity
  ON traffic_observations (workspace_id, provider, zone_id, event_time, valid_at, issued_at);

-- Point-in-time join access path: "latest row visible as of a decision time".
CREATE INDEX weather_point_in_time
  ON weather_observations (workspace_id, zone_id, information_available_at DESC, valid_at DESC);

CREATE INDEX traffic_point_in_time
  ON traffic_observations (workspace_id, zone_id, information_available_at DESC, valid_at DESC);

-- ---------------------------------------------------------------------------
-- Row level security
-- ---------------------------------------------------------------------------

ALTER TABLE weather_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE traffic_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE collector_runs       ENABLE ROW LEVEL SECURITY;

CREATE POLICY weather_workspace_read ON weather_observations
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT zonepilot_member_workspaces(auth.uid())));

CREATE POLICY traffic_workspace_read ON traffic_observations
  FOR SELECT TO authenticated
  USING (workspace_id IN (SELECT zonepilot_member_workspaces(auth.uid())));

CREATE POLICY collector_runs_workspace_read ON collector_runs
  FOR SELECT TO authenticated
  USING (
    workspace_id IS NULL
    OR workspace_id IN (SELECT zonepilot_member_workspaces(auth.uid()))
  );

-- Writes are performed by the private execution plane using a dedicated role,
-- never by an end-user session. No INSERT/UPDATE policy is granted to
-- authenticated, so RLS denies writes by default.

COMMENT ON COLUMN traffic_observations.information_available_at IS
  'Hard leakage boundary. A feature build for decision time D may only read '
  'rows where information_available_at <= D.';
COMMENT ON COLUMN weather_observations.information_available_at IS
  'Hard leakage boundary. A forecast issued for a future valid_at is readable '
  'from information_available_at onward, never before.';

COMMIT;
