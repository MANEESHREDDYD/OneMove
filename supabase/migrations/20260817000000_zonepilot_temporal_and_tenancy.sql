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
-- 2. workspace_id appeared in no migration, so the API's workspace check was
--    unreachable: it is skipped whenever the token carries no workspace claim,
--    and no token could carry one. Authorization was inert.

BEGIN;

-- ---------------------------------------------------------------------------
-- Evidence taxonomy as a database type
-- ---------------------------------------------------------------------------
--
-- This is not a second vocabulary. It is the same nine values as the canonical
-- EvidenceClass enum in services/temporal/contracts.py, projected into the
-- database so the constraint can be enforced where the row actually lands.
--
-- Availability is a *state*, not an evidence class, and deliberately does not
-- appear here.

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
  'Mirrors services.temporal.contracts.EvidenceClass exactly (9 values). '
  'Authoritative observation tables reject STAGING_DO_NOT_USE and TEST_ONLY '
  'via CHECK constraint; the values remain in the type so staging surfaces can '
  'still carry them.';

CREATE TYPE zonepilot_workspace_role AS ENUM (
  'OWNER',
  'ADMIN',
  'RESEARCHER',
  'VIEWER',
  'INTEGRATION_USER',
  'COLLECTOR'
);

COMMENT ON TYPE zonepilot_workspace_role IS
  'OWNER/ADMIN administer membership. RESEARCHER/VIEWER/INTEGRATION_USER read '
  'workspace evidence but never administer. COLLECTOR is a write-only '
  'acquisition identity: it may append evidence to its own workspace but may '
  'not read the evidence corpus and may not read other members.';

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
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role         zonepilot_workspace_role NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX workspace_members_user_idx ON workspace_members (user_id);

-- ---------------------------------------------------------------------------
-- Membership resolution
-- ---------------------------------------------------------------------------
--
-- SECURITY DEFINER so the membership lookup does not re-enter the RLS policy
-- that calls it. Migration 00003_fix_rls_recursion.sql already had to repair
-- exactly that class of recursion for the legacy profile policies.
--
-- These functions take no user argument on purpose. A SECURITY DEFINER
-- function that accepts an arbitrary user id and is executable by
-- `authenticated` is a membership-enumeration oracle for every other user in
-- the deployment. The caller identity is resolved from the verified session
-- instead, so a caller can only ever learn about itself.

CREATE OR REPLACE FUNCTION public.zonepilot_current_member_workspaces()
RETURNS SETOF UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
  SELECT workspace_id
  FROM public.workspace_members
  WHERE user_id = auth.uid();
$fn$;

CREATE OR REPLACE FUNCTION public.zonepilot_current_workspace_role(target_workspace UUID)
RETURNS zonepilot_workspace_role
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
  SELECT role
  FROM public.workspace_members
  WHERE user_id = auth.uid()
    AND workspace_id = target_workspace;
$fn$;

COMMENT ON FUNCTION public.zonepilot_current_workspace_role(UUID) IS
  'Returns the calling session''s role in one workspace, or NULL when the '
  'caller is not a member. NULL propagates through the IN () tests used by the '
  'policies below, so a non-member fails closed.';

REVOKE ALL ON FUNCTION public.zonepilot_current_member_workspaces() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.zonepilot_current_workspace_role(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.zonepilot_current_member_workspaces() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.zonepilot_current_workspace_role(UUID) TO authenticated, service_role;

-- ---------------------------------------------------------------------------
-- Tenancy row level security
-- ---------------------------------------------------------------------------

ALTER TABLE workspaces        ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY workspaces_member_read ON workspaces
  FOR SELECT TO authenticated
  USING (id IN (SELECT public.zonepilot_current_member_workspaces()));

-- Only OWNER/ADMIN may rename or otherwise administer a workspace. A VIEWER or
-- RESEARCHER holding a valid workspace session still cannot mutate.
CREATE POLICY workspaces_admin_update ON workspaces
  FOR UPDATE TO authenticated
  USING (public.zonepilot_current_workspace_role(id) IN ('OWNER', 'ADMIN'))
  WITH CHECK (public.zonepilot_current_workspace_role(id) IN ('OWNER', 'ADMIN'));

-- Workspace creation is a server-side provisioning action performed with the
-- service role. No INSERT or DELETE policy is granted to authenticated.

-- A member always sees its own membership row. Seeing *other* members is an
-- administrative capability: it is the workspace's user directory. This is the
-- rule that keeps a COLLECTOR identity from reading unrelated user data.
CREATE POLICY workspace_members_read ON workspace_members
  FOR SELECT TO authenticated
  USING (
    user_id = auth.uid()
    OR public.zonepilot_current_workspace_role(workspace_id) IN ('OWNER', 'ADMIN')
  );

CREATE POLICY workspace_members_admin_insert ON workspace_members
  FOR INSERT TO authenticated
  WITH CHECK (public.zonepilot_current_workspace_role(workspace_id) IN ('OWNER', 'ADMIN'));

CREATE POLICY workspace_members_admin_update ON workspace_members
  FOR UPDATE TO authenticated
  USING (public.zonepilot_current_workspace_role(workspace_id) IN ('OWNER', 'ADMIN'))
  WITH CHECK (public.zonepilot_current_workspace_role(workspace_id) IN ('OWNER', 'ADMIN'));

CREATE POLICY workspace_members_admin_delete ON workspace_members
  FOR DELETE TO authenticated
  USING (public.zonepilot_current_workspace_role(workspace_id) IN ('OWNER', 'ADMIN'));

-- ---------------------------------------------------------------------------
-- PostgREST grants
-- ---------------------------------------------------------------------------
--
-- 20260809000000_explicit_grants.sql granted the Data API roles privileges on
-- the tables that existed *at that moment*. It cannot reach tables created
-- afterwards, and supabase/config.toml documents that auto-exposure of new
-- public tables is being withdrawn. Without these grants the policies above
-- would be unreachable and every workspace read would fail with "permission
-- denied for table" rather than a clean row-level decision.
--
-- anon is deliberately granted nothing: tenancy has no unauthenticated surface.

GRANT SELECT, UPDATE                 ON TABLE workspaces        TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE workspace_members TO authenticated;
GRANT ALL PRIVILEGES                 ON TABLE workspaces        TO service_role;
GRANT ALL PRIVILEGES                 ON TABLE workspace_members TO service_role;

-- ---------------------------------------------------------------------------
-- Refuse to fabricate provenance for pre-tenancy rows
-- ---------------------------------------------------------------------------
--
-- The temporal columns below are NOT NULL and carry no default, because there
-- is no honest default for them. A row already sitting in an observation table
-- has no recorded event_time, issued_at or information_available_at, and
-- inventing one would place an unfalsifiable timestamp into the evidence
-- corpus -- exactly the failure this migration exists to prevent.
--
-- So the migration refuses, loudly, rather than backfilling a lie. Both tables
-- are empty today (no acquisition run has ever completed). If that changes,
-- the operator must quarantine those rows deliberately before re-running.

DO $guard$
DECLARE
  weather_rows BIGINT;
  traffic_rows BIGINT;
BEGIN
  SELECT count(*) INTO weather_rows FROM weather_observations;
  SELECT count(*) INTO traffic_rows FROM traffic_observations;
  IF weather_rows > 0 OR traffic_rows > 0 THEN
    RAISE EXCEPTION
      'Refusing to add NOT NULL temporal provenance over % pre-tenancy weather row(s) and % pre-tenancy traffic row(s). These rows have no recorded provenance and none may be invented. Quarantine or delete them, then re-run this migration.',
      weather_rows, traffic_rows;
  END IF;
END
$guard$;

-- ---------------------------------------------------------------------------
-- Temporal columns on the authoritative observation tables
-- ---------------------------------------------------------------------------
--
-- run_id already exists on both tables as a nullable FK to collector_runs and
-- is restated here only so the full temporal column contract is legible in one
-- place. It is left nullable: the execution plane owns run lifecycle.
--
-- This column set is a published contract that the acquisition plane writes
-- against. Do not reorder, rename or retype these columns without coordinating.

ALTER TABLE collector_runs
  ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;

ALTER TABLE weather_observations
  ADD COLUMN IF NOT EXISTS run_id                   UUID REFERENCES collector_runs(id),
  ADD COLUMN                workspace_id             UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  ADD COLUMN                zone_id                  TEXT NOT NULL,
  ADD COLUMN                provider                 TEXT NOT NULL,
  ADD COLUMN                provider_version         TEXT NOT NULL,
  ADD COLUMN                event_time               TIMESTAMPTZ NOT NULL,
  ADD COLUMN                issued_at                TIMESTAMPTZ NOT NULL,
  ADD COLUMN                valid_at                 TIMESTAMPTZ NOT NULL,
  ADD COLUMN                retrieved_at             TIMESTAMPTZ NOT NULL,
  ADD COLUMN                information_available_at TIMESTAMPTZ NOT NULL,
  ADD COLUMN                evidence_class           zonepilot_evidence_class NOT NULL,
  ADD COLUMN                dataset_version          TEXT NOT NULL;

ALTER TABLE traffic_observations
  ADD COLUMN IF NOT EXISTS run_id                   UUID REFERENCES collector_runs(id),
  ADD COLUMN                workspace_id             UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  ADD COLUMN                zone_id                  TEXT NOT NULL,
  ADD COLUMN                provider                 TEXT NOT NULL,
  ADD COLUMN                provider_version         TEXT NOT NULL,
  ADD COLUMN                event_time               TIMESTAMPTZ NOT NULL,
  ADD COLUMN                issued_at                TIMESTAMPTZ NOT NULL,
  ADD COLUMN                valid_at                 TIMESTAMPTZ NOT NULL,
  ADD COLUMN                retrieved_at             TIMESTAMPTZ NOT NULL,
  ADD COLUMN                information_available_at TIMESTAMPTZ NOT NULL,
  ADD COLUMN                evidence_class           zonepilot_evidence_class NOT NULL,
  ADD COLUMN                dataset_version          TEXT NOT NULL;

-- ---------------------------------------------------------------------------
-- Temporal invariants
-- ---------------------------------------------------------------------------
--
-- These mirror TemporalFeatureRecord.validate_availability_timeline so a row
-- that Postgres accepts is a row the Python contract can also accept:
--
--   information_available_at >= event_time    an event is not knowable before it happens
--   information_available_at >= issued_at     a payload is not knowable before its provider issued it
--   information_available_at <= retrieved_at  we did not know it before we fetched it
--   retrieved_at             >= issued_at     nothing is retrieved before it exists
--
-- Deliberately ABSENT: any relation between valid_at and
-- information_available_at. A weather forecast issued at T for a valid_at
-- hours in the future is the normal, legitimate case, and the whole point of
-- separating the two columns. The leakage rule is about *decision_time*, not
-- about valid_at:
--
--   safe to use at decision time D          <=>  information_available_at <= D
--   it is a forecast rather than a nowcast  <=>  valid_at > D
--
-- A constraint of the form `valid_at <= information_available_at` would reject
-- every forecast ZonePilot exists to produce. It is not here, and must not be
-- added.

ALTER TABLE weather_observations
  ADD CONSTRAINT weather_information_not_before_event
    CHECK (information_available_at >= event_time),
  ADD CONSTRAINT weather_information_not_before_issue
    CHECK (information_available_at >= issued_at),
  ADD CONSTRAINT weather_information_not_after_retrieval
    CHECK (information_available_at <= retrieved_at),
  ADD CONSTRAINT weather_retrieved_not_before_issue
    CHECK (retrieved_at >= issued_at),
  ADD CONSTRAINT weather_evidence_is_authoritative
    CHECK (evidence_class NOT IN ('STAGING_DO_NOT_USE', 'TEST_ONLY'));

ALTER TABLE traffic_observations
  ADD CONSTRAINT traffic_information_not_before_event
    CHECK (information_available_at >= event_time),
  ADD CONSTRAINT traffic_information_not_before_issue
    CHECK (information_available_at >= issued_at),
  ADD CONSTRAINT traffic_information_not_after_retrieval
    CHECK (information_available_at <= retrieved_at),
  ADD CONSTRAINT traffic_retrieved_not_before_issue
    CHECK (retrieved_at >= issued_at),
  ADD CONSTRAINT traffic_evidence_is_authoritative
    CHECK (evidence_class NOT IN ('STAGING_DO_NOT_USE', 'TEST_ONLY'));

-- ---------------------------------------------------------------------------
-- Idempotency: a provider re-run must not duplicate an observation
-- ---------------------------------------------------------------------------
--
-- Identity is (workspace, provider, zone, event_time, valid_at, issued_at).
-- retrieved_at and information_available_at are deliberately NOT part of the
-- identity: re-fetching the same provider payload later yields the same
-- observation, only re-retrieved. That is what makes an acquisition re-run
-- safely repeatable through ON CONFLICT DO NOTHING.

CREATE UNIQUE INDEX weather_observation_identity
  ON weather_observations (workspace_id, provider, zone_id, event_time, valid_at, issued_at);

CREATE UNIQUE INDEX traffic_observation_identity
  ON traffic_observations (workspace_id, provider, zone_id, event_time, valid_at, issued_at);

-- Point-in-time access path: "the rows visible as of a decision time, newest
-- validity first".
CREATE INDEX weather_point_in_time
  ON weather_observations (workspace_id, zone_id, information_available_at DESC, valid_at DESC);

CREATE INDEX traffic_point_in_time
  ON traffic_observations (workspace_id, zone_id, information_available_at DESC, valid_at DESC);

-- ---------------------------------------------------------------------------
-- Observation row level security
-- ---------------------------------------------------------------------------
--
-- RLS was already enabled on these three tables by 00002_zonepilot_v151.sql
-- with no policy attached, which denied everything. These policies are the
-- first read path, and they agree with the API layer in
-- services/api/core/auth.py: membership is resolved from the session, never
-- from a client-supplied header.
--
-- COLLECTOR is absent from every read policy on purpose. It is an acquisition
-- identity, so it appends evidence and can never read the corpus back.

CREATE POLICY weather_workspace_read ON weather_observations
  FOR SELECT TO authenticated
  USING (
    public.zonepilot_current_workspace_role(workspace_id)
      IN ('OWNER', 'ADMIN', 'RESEARCHER', 'VIEWER', 'INTEGRATION_USER')
  );

CREATE POLICY traffic_workspace_read ON traffic_observations
  FOR SELECT TO authenticated
  USING (
    public.zonepilot_current_workspace_role(workspace_id)
      IN ('OWNER', 'ADMIN', 'RESEARCHER', 'VIEWER', 'INTEGRATION_USER')
  );

CREATE POLICY collector_runs_workspace_read ON collector_runs
  FOR SELECT TO authenticated
  USING (
    public.zonepilot_current_workspace_role(workspace_id)
      IN ('OWNER', 'ADMIN', 'RESEARCHER', 'VIEWER', 'INTEGRATION_USER')
  );

-- The only end-user write path into the evidence corpus: a COLLECTOR appending
-- to the one workspace it belongs to. There is no UPDATE and no DELETE policy
-- for any role, so evidence is append-only for every authenticated session
-- including OWNER; corrections are a service-role operation.

CREATE POLICY weather_collector_append ON weather_observations
  FOR INSERT TO authenticated
  WITH CHECK (public.zonepilot_current_workspace_role(workspace_id) = 'COLLECTOR');

CREATE POLICY traffic_collector_append ON traffic_observations
  FOR INSERT TO authenticated
  WITH CHECK (public.zonepilot_current_workspace_role(workspace_id) = 'COLLECTOR');

CREATE POLICY collector_runs_collector_append ON collector_runs
  FOR INSERT TO authenticated
  WITH CHECK (public.zonepilot_current_workspace_role(workspace_id) = 'COLLECTOR');

COMMENT ON COLUMN weather_observations.information_available_at IS
  'Hard leakage boundary. A feature build for decision time D may only read '
  'rows where information_available_at <= D. A forecast for a future valid_at '
  'is readable from information_available_at onward, never before.';
COMMENT ON COLUMN traffic_observations.information_available_at IS
  'Hard leakage boundary. A feature build for decision time D may only read '
  'rows where information_available_at <= D.';
COMMENT ON COLUMN weather_observations.valid_at IS
  'When the value applies. Intentionally unconstrained relative to '
  'information_available_at: valid_at > information_available_at is a forecast.';
COMMENT ON COLUMN traffic_observations.valid_at IS
  'When the value applies. Intentionally unconstrained relative to '
  'information_available_at: valid_at > information_available_at is a forecast.';

COMMIT;

NOTIFY pgrst, 'reload schema';
