-- F-011: persist the execution lineage a result claims.
--
-- OptimizationRepository.save_result required code_sha and then discarded it: the
-- column did not exist on optimization_results and was absent from the INSERT.
-- A stored result could therefore not be tied to the build that produced it, which
-- is the whole point of the field. Replay compared against whatever the current
-- code happened to be.
--
-- optimization_results.job_id already references optimization_jobs(id), and the job
-- row freezes the submission-time lineage. These columns denormalise the values that
-- were true AT EXECUTION TIME, which is not necessarily what the job row says today:
-- the job row is mutable, the result is immutable evidence.

ALTER TABLE public.optimization_results
    ADD COLUMN IF NOT EXISTS code_sha TEXT;

ALTER TABLE public.optimization_results
    ADD COLUMN IF NOT EXISTS dataset_version TEXT;

ALTER TABLE public.optimization_results
    ADD COLUMN IF NOT EXISTS matrix_id TEXT;

ALTER TABLE public.optimization_results
    ADD COLUMN IF NOT EXISTS matrix_sha256 TEXT;

ALTER TABLE public.optimization_results
    ADD COLUMN IF NOT EXISTS problem_snapshot_id TEXT;

ALTER TABLE public.optimization_results
    ADD COLUMN IF NOT EXISTS problem_snapshot_sha256 TEXT;

ALTER TABLE public.optimization_results
    ADD COLUMN IF NOT EXISTS solver_config_hash TEXT;

-- Locate a result by the exact build that produced it, which is the query an
-- incident review actually runs ("what did release X emit?").
CREATE INDEX IF NOT EXISTS idx_optimization_results_code_sha
    ON public.optimization_results (code_sha);

-- Locate every result derived from one frozen problem snapshot.
CREATE INDEX IF NOT EXISTS idx_optimization_results_snapshot
    ON public.optimization_results (problem_snapshot_sha256);
