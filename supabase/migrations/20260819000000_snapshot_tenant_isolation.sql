-- P0-AUTH-SNAPSHOT-001: close cross-tenant exposure of optimization problem snapshots.
--
-- The prior policy contained a `workspace_id IS NULL OR ...` escape hatch, which made
-- every unscoped snapshot readable by every tenant. Combined with an application-layer
-- lookup that ignored workspace_id entirely, any tenant could read, replay, or freeze
-- another tenant's snapshot. This migration removes the escape hatch and forbids new
-- unscoped rows.

-- 1. Refuse to proceed if legacy unscoped snapshots exist. These are ambiguous: we
--    cannot infer their owner, and silently deleting tenant data is not acceptable.
--    An operator must triage them explicitly before this migration can apply.
DO $$
DECLARE
    orphan_count BIGINT;
BEGIN
    SELECT count(*) INTO orphan_count
    FROM public.optimization_problem_snapshots
    WHERE workspace_id IS NULL;

    IF orphan_count > 0 THEN
        RAISE EXCEPTION
            'P0-AUTH-SNAPSHOT-001: % snapshot row(s) have a NULL workspace_id. Assign an owning workspace or archive them, then re-run this migration.',
            orphan_count;
    END IF;
END
$$;

-- 2. Forbid unscoped snapshots at the schema level.
ALTER TABLE public.optimization_problem_snapshots
    ALTER COLUMN workspace_id SET NOT NULL;

-- 3. Replace the permissive policy with strict membership-only isolation.
DROP POLICY IF EXISTS "problem_snapshots_workspace_isolation"
    ON public.optimization_problem_snapshots;

CREATE POLICY "problem_snapshots_workspace_isolation"
    ON public.optimization_problem_snapshots
    FOR ALL
    USING (
        workspace_id IN (
            SELECT workspace_id::text
            FROM public.workspace_members
            WHERE user_id = auth.uid()
        )
    )
    WITH CHECK (
        workspace_id IN (
            SELECT workspace_id::text
            FROM public.workspace_members
            WHERE user_id = auth.uid()
        )
    );

-- 4. Snapshots are immutable evidence. Members may read them; they must not rewrite
--    or delete frozen lineage. Writes happen through the backend owner role only.
REVOKE UPDATE, DELETE ON public.optimization_problem_snapshots FROM authenticated;

-- 5. Support the now-mandatory (identifier, workspace) lookup shape.
CREATE INDEX IF NOT EXISTS idx_opt_problem_snapshots_ws_sha
    ON public.optimization_problem_snapshots (workspace_id, snapshot_sha256);
CREATE INDEX IF NOT EXISTS idx_opt_problem_snapshots_ws_id
    ON public.optimization_problem_snapshots (workspace_id, snapshot_id);
