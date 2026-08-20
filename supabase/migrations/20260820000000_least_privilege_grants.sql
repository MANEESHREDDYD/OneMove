-- F-007: replace blanket GRANT ALL with least privilege.
--
-- 20260809000000_explicit_grants.sql granted ALL PRIVILEGES on every table in
-- schema public to anon and authenticated. Row Level Security is the only thing
-- that constrained those grants, and six OneMove tables never enabled it:
--
--     decision_records, decision_replays, forecast_records,
--     resilience_results, resilience_scenarios, shadow_evaluations
--
-- Anyone holding the public anon key could therefore read, insert, update and
-- delete decision and evidence records directly through PostgREST, with no
-- application code involved. The decision ledger was forgeable from a browser.
--
-- Model applied here:
--   anon           -> no rights on any OneMove table. Nothing here is public.
--   authenticated  -> SELECT only, and only on tenant tables that have RLS
--                     enforcing workspace membership. All mutation goes through
--                     the API, which applies workspace predicates explicitly
--                     because the backend's owner-role DSN bypasses RLS.
--   service_role   -> unchanged; it is the backend identity.
--
-- Internal machinery (outbox, snapshots, jobs, results) is not reachable by any
-- browser role at all, in any mode.

-- ---------------------------------------------------------------------------
-- 1. Revoke privileges on the OneMove tables this finding is about.
-- ---------------------------------------------------------------------------
-- A blanket `REVOKE ALL ... ON ALL TABLES` was the first attempt here and it was
-- wrong. Re-granting only the ten tables enumerated below stripped every OTHER
-- table in the schema -- workspaces, workspace_members, profiles, weather -- and
-- broke legitimate tenant access. The live-database run surfaced 30
-- InsufficientPrivilege failures across the RLS suite, including on `profiles`,
-- which the admin authorization check reads. A static review had passed this
-- migration; only executing it against a real database found the defect.
--
-- The finding is about internal OneMove machinery being reachable from a browser
-- role. The revoke is therefore scoped to exactly those tables. Pre-existing
-- consumer tables keep the grants they had; narrowing those is a separate piece
-- of work with its own blast radius, and doing it silently here is how the
-- regression happened.

REVOKE ALL PRIVILEGES ON
    public.decision_records,
    public.decision_replays,
    public.forecast_records,
    public.resilience_results,
    public.resilience_scenarios,
    public.shadow_evaluations,
    public.optimization_jobs,
    public.optimization_results,
    public.optimization_outbox,
    public.optimization_problem_snapshots
FROM anon, authenticated;

-- Schema usage is still required for PostgREST to resolve anything at all.
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 2. Enable RLS on the six OneMove tables that never had it.
--    Without this, a SELECT grant below would expose every tenant's rows.
-- ---------------------------------------------------------------------------
ALTER TABLE public.decision_records      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.decision_replays      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forecast_records      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resilience_results    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resilience_scenarios  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shadow_evaluations    ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- 3. Workspace-membership read policies. Read-only by construction: no
--    WITH CHECK clause is defined, and no INSERT/UPDATE/DELETE is granted.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'decision_records',
        'decision_replays',
        'forecast_records',
        'resilience_results',
        'resilience_scenarios',
        'shadow_evaluations'
    ]
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', tbl || '_workspace_read', tbl);
        EXECUTE format(
            'CREATE POLICY %I ON public.%I FOR SELECT USING ('
            '  workspace_id IN ('
            '    SELECT workspace_id::text FROM public.workspace_members WHERE user_id = auth.uid()'
            '  )'
            ')',
            tbl || '_workspace_read', tbl
        );
    END LOOP;
END
$$;

-- ---------------------------------------------------------------------------
-- 4. Least-privilege grants. SELECT only, tenant tables only.
-- ---------------------------------------------------------------------------
GRANT SELECT ON public.decision_records     TO authenticated;
GRANT SELECT ON public.decision_replays     TO authenticated;
GRANT SELECT ON public.forecast_records     TO authenticated;
GRANT SELECT ON public.resilience_results   TO authenticated;
GRANT SELECT ON public.resilience_scenarios TO authenticated;
GRANT SELECT ON public.shadow_evaluations   TO authenticated;
GRANT SELECT ON public.optimization_jobs    TO authenticated;
GRANT SELECT ON public.optimization_results TO authenticated;

-- Deliberately NOT granted to any browser role:
--   optimization_outbox              - internal delivery machinery
--   optimization_problem_snapshots   - immutable replay lineage
-- Both remain service_role only.

-- ---------------------------------------------------------------------------
-- 5. anon holds nothing. Stated explicitly so the intent survives review.
-- ---------------------------------------------------------------------------
REVOKE ALL PRIVILEGES ON public.decision_records,
                         public.decision_replays,
                         public.forecast_records,
                         public.resilience_results,
                         public.resilience_scenarios,
                         public.shadow_evaluations,
                         public.optimization_jobs,
                         public.optimization_results,
                         public.optimization_outbox,
                         public.optimization_problem_snapshots
    FROM anon;
