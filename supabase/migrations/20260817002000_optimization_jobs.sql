-- 20260817002000_optimization_jobs.sql
-- Durable, DB-backed job runner for the deterministic facility optimizer.
--
-- Design notes
--   * There is no broker. Claiming is a lease with an expiry, so a worker that
--     crashes mid-solve does not strand its job: once the lease lapses the row
--     becomes claimable again. This is deliberately the simplest thing that
--     survives a crash.
--   * Every input version reference is stored on the job row, not looked up at
--     read time. A result must remain explainable even after the artifacts it
--     was computed from have been superseded.
--   * Idempotency is enforced in the database, not in application code, so two
--     concurrent submissions cannot both create a job.

CREATE TABLE IF NOT EXISTS public.optimization_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by UUID NOT NULL,
    workspace_id TEXT,

    -- Idempotency. The fingerprint is a content hash of the canonicalised
    -- request; the key is caller-supplied. Same key + same fingerprint is a
    -- retry of one submission. Same key + different fingerprint is a caller
    -- bug and must be rejected, never silently served from cache.
    idempotency_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    request_payload JSONB NOT NULL,

    -- Input lineage, captured at submission time.
    graph_version TEXT,
    dataset_version TEXT,
    matrix_id TEXT,
    assumption_version TEXT,
    solver_version TEXT,
    code_sha TEXT,

    status TEXT NOT NULL DEFAULT 'QUEUED',
    solver_status TEXT,
    fail_closed BOOLEAN,
    failure_code TEXT,
    failure_message TEXT,

    -- Lease-based claiming.
    lease_owner TEXT,
    lease_expires_at TIMESTAMPTZ,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,

    -- Timings.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    queue_wait_ms BIGINT,
    run_duration_ms BIGINT,

    CONSTRAINT chk_optimization_job_status
        CHECK (status IN ('QUEUED', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELLED')),
    CONSTRAINT chk_optimization_job_solver_status
        CHECK (solver_status IS NULL OR solver_status IN
            ('OPTIMAL', 'INFEASIBLE', 'TIME_LIMIT', 'MODEL_INVALID', 'SOLVER_ERROR')),
    CONSTRAINT chk_optimization_job_fingerprint
        CHECK (request_fingerprint ~ '^[0-9a-f]{64}$'),
    CONSTRAINT chk_optimization_job_idempotency_key
        CHECK (char_length(idempotency_key) BETWEEN 1 AND 200),
    CONSTRAINT chk_optimization_job_attempts
        CHECK (attempt_count >= 0 AND max_attempts > 0),
    -- A terminal job must not still hold a lease.
    CONSTRAINT chk_optimization_job_lease_released
        CHECK (status IN ('QUEUED', 'RUNNING') OR lease_owner IS NULL),
    -- RUNNING is the only state that may hold a lease, and it must have one.
    CONSTRAINT chk_optimization_job_running_has_lease
        CHECK (status <> 'RUNNING' OR (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)),

    -- Idempotency is scoped per requester so one caller's key cannot collide
    -- with, or leak the existence of, another's.
    CONSTRAINT uq_optimization_job_idempotency UNIQUE (requested_by, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_optimization_jobs_claimable
    ON public.optimization_jobs (status, lease_expires_at, created_at);
CREATE INDEX IF NOT EXISTS idx_optimization_jobs_requested_by
    ON public.optimization_jobs (requested_by, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_optimization_jobs_fingerprint
    ON public.optimization_jobs (request_fingerprint);

CREATE TABLE IF NOT EXISTS public.optimization_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES public.optimization_jobs(id) ON DELETE CASCADE,

    -- The verbatim, contract-validated engine result. Stored whole so a stored
    -- decision can be re-validated against the same Pydantic contract later.
    result_document JSONB NOT NULL,
    pareto_document JSONB,

    problem_fingerprint TEXT NOT NULL,
    solver_status TEXT NOT NULL,
    action TEXT NOT NULL,
    fail_closed BOOLEAN NOT NULL,

    -- Evidence references, denormalised for auditability.
    graph_version TEXT NOT NULL,
    assumption_version TEXT NOT NULL,
    solver_version TEXT NOT NULL,
    scenario_evidence_classes TEXT[] NOT NULL DEFAULT '{}',

    -- Measured cost of the run.
    cp_sat_solve_count INTEGER,
    implied_solves_skipped INTEGER,
    solver_wall_time_seconds DOUBLE PRECISION,
    peak_memory_bytes BIGINT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_optimization_result_solver_status
        CHECK (solver_status IN ('OPTIMAL', 'INFEASIBLE', 'TIME_LIMIT', 'MODEL_INVALID', 'SOLVER_ERROR')),
    CONSTRAINT chk_optimization_result_action
        CHECK (action IN ('OPEN_FACILITIES', 'NO_ACTION', 'NONE')),
    CONSTRAINT chk_optimization_result_fingerprint
        CHECK (problem_fingerprint ~ '^[0-9a-f]{64}$'),
    -- The fail-closed rule, enforced by the database as well as the contract:
    -- only a proved optimum may carry an action.
    CONSTRAINT chk_optimization_result_fail_closed
        CHECK (
            (solver_status = 'OPTIMAL' AND fail_closed = FALSE AND action <> 'NONE')
            OR (solver_status <> 'OPTIMAL' AND fail_closed = TRUE AND action = 'NONE')
        ),
    -- One result per job.
    CONSTRAINT uq_optimization_result_job UNIQUE (job_id)
);

CREATE INDEX IF NOT EXISTS idx_optimization_results_job
    ON public.optimization_results (job_id);

-- Claim the oldest runnable job under a fresh lease.
--
-- Reclaims a RUNNING job whose lease has expired, which is what makes a worker
-- crash survivable. FOR UPDATE SKIP LOCKED lets several workers poll the same
-- table without blocking or double-claiming.
CREATE OR REPLACE FUNCTION public.claim_optimization_job(
    p_lease_owner TEXT,
    p_lease_seconds INTEGER DEFAULT 300
)
RETURNS SETOF public.optimization_jobs
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_job_id UUID;
BEGIN
    IF p_lease_owner IS NULL OR char_length(p_lease_owner) = 0 THEN
        RAISE EXCEPTION 'lease owner must be provided';
    END IF;
    IF p_lease_seconds IS NULL OR p_lease_seconds <= 0 THEN
        RAISE EXCEPTION 'lease seconds must be positive';
    END IF;

    SELECT id INTO v_job_id
    FROM public.optimization_jobs
    WHERE (
        status = 'QUEUED'
        OR (status = 'RUNNING' AND lease_expires_at IS NOT NULL AND lease_expires_at < now())
    )
      AND attempt_count < max_attempts
    ORDER BY created_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1;

    IF v_job_id IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    UPDATE public.optimization_jobs
    SET status = 'RUNNING',
        lease_owner = p_lease_owner,
        lease_expires_at = now() + make_interval(secs => p_lease_seconds),
        attempt_count = attempt_count + 1,
        started_at = COALESCE(started_at, now()),
        queue_wait_ms = COALESCE(queue_wait_ms,
            (EXTRACT(EPOCH FROM (now() - created_at)) * 1000)::BIGINT),
        updated_at = now()
    WHERE id = v_job_id
    RETURNING *;
END;
$$;

-- Extend an existing lease. Refuses to touch a job the caller does not hold,
-- so a stale worker cannot resurrect a job that was already reclaimed.
CREATE OR REPLACE FUNCTION public.renew_optimization_job_lease(
    p_job_id UUID,
    p_lease_owner TEXT,
    p_lease_seconds INTEGER DEFAULT 300
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE public.optimization_jobs
    SET lease_expires_at = now() + make_interval(secs => p_lease_seconds),
        updated_at = now()
    WHERE id = p_job_id
      AND status = 'RUNNING'
      AND lease_owner = p_lease_owner;
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated = 1;
END;
$$;

ALTER TABLE public.optimization_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.optimization_results ENABLE ROW LEVEL SECURITY;

-- Callers may read only their own jobs. There is no client-side insert policy:
-- submission goes through the API, which validates the request contract first.
DROP POLICY IF EXISTS "Requester can read own optimization jobs" ON public.optimization_jobs;
CREATE POLICY "Requester can read own optimization jobs"
    ON public.optimization_jobs
    FOR SELECT
    TO authenticated
    USING (requested_by = auth.uid());

DROP POLICY IF EXISTS "Requester can read own optimization results" ON public.optimization_results;
CREATE POLICY "Requester can read own optimization results"
    ON public.optimization_results
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.optimization_jobs job
            WHERE job.id = optimization_results.job_id
              AND job.requested_by = auth.uid()
        )
    );

REVOKE ALL ON FUNCTION public.claim_optimization_job(TEXT, INTEGER) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.renew_optimization_job_lease(UUID, TEXT, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.claim_optimization_job(TEXT, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.renew_optimization_job_lease(UUID, TEXT, INTEGER) TO service_role;

GRANT SELECT ON public.optimization_jobs TO authenticated;
GRANT SELECT ON public.optimization_results TO authenticated;
GRANT ALL ON public.optimization_jobs TO service_role;
GRANT ALL ON public.optimization_results TO service_role;
