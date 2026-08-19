-- Immutable Optimization Problem Snapshots for Deterministic PIT Replay
CREATE TABLE IF NOT EXISTS public.optimization_problem_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    snapshot_sha256 TEXT NOT NULL UNIQUE,
    workspace_id TEXT,
    problem_json JSONB NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_opt_problem_snapshots_sha ON public.optimization_problem_snapshots (snapshot_sha256);
CREATE INDEX IF NOT EXISTS idx_opt_problem_snapshots_ws ON public.optimization_problem_snapshots (workspace_id);

ALTER TABLE public.optimization_problem_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "problem_snapshots_workspace_isolation"
    ON public.optimization_problem_snapshots
    FOR ALL
    USING (
        workspace_id IS NULL OR workspace_id IN (
            SELECT workspace_id::text
            FROM public.workspace_members
            WHERE user_id = auth.uid()
        )
    );
