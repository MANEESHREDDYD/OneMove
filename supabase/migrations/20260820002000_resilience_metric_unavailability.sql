-- F-010: give UNAVAILABLE a representation in resilience_results.
--
-- Every metric column was declared NOT NULL, so a resilience evaluation that
-- legitimately could not compute one -- capacity loss with no capacity ledger,
-- quantiles when a total outage leaves no routable zone -- had nowhere to record
-- that fact. The old code filled the gap with invented constants (coverage always
-- 10000, capacity loss always 0). Removing the invention left the repository
-- correctly REFUSING to persist a partial evaluation, which is honest but throws
-- away the metrics it did derive.
--
-- NULL now means "not computed", and metric_unavailable records WHY, per metric.
-- A NULL with no matching reason is a bug, not an absence, so the two are written
-- together and the application enforces the pairing.
--
-- Widening only: dropping NOT NULL cannot fail on existing rows, and existing rows
-- keep their values with an empty reason map.

ALTER TABLE public.resilience_results ALTER COLUMN coverage_basis_points          DROP NOT NULL;
ALTER TABLE public.resilience_results ALTER COLUMN p50_duration_seconds           DROP NOT NULL;
ALTER TABLE public.resilience_results ALTER COLUMN p90_duration_seconds           DROP NOT NULL;
ALTER TABLE public.resilience_results ALTER COLUMN p95_duration_seconds           DROP NOT NULL;
ALTER TABLE public.resilience_results ALTER COLUMN disconnected_zones_count       DROP NOT NULL;
ALTER TABLE public.resilience_results ALTER COLUMN redundancy_index_basis_points  DROP NOT NULL;
ALTER TABLE public.resilience_results ALTER COLUMN failure_exposure_score         DROP NOT NULL;
ALTER TABLE public.resilience_results ALTER COLUMN capacity_loss_basis_points     DROP NOT NULL;

-- Reason per unavailable metric: {"capacity_loss_basis_points": "no capacity ledger frozen", ...}
ALTER TABLE public.resilience_results
    ADD COLUMN IF NOT EXISTS metric_unavailable JSONB NOT NULL DEFAULT '{}'::jsonb;

-- The grade is derived from the metrics, so it becomes UNAVAILABLE with them.
-- It stays NOT NULL because the string "UNAVAILABLE" is a truthful value here,
-- where a NULL numeric would be ambiguous.
ALTER TABLE public.resilience_results
    DROP CONSTRAINT IF EXISTS chk_resilience_degradation_grade;

ALTER TABLE public.resilience_results
    ADD CONSTRAINT chk_resilience_degradation_grade
    CHECK (degradation_grade IN ('ROBUST', 'DEGRADED', 'FRAGILE', 'CRITICAL', 'UNAVAILABLE'));

-- Surface partially-evaluated rows to operators without a full scan.
CREATE INDEX IF NOT EXISTS idx_resilience_results_partial
    ON public.resilience_results (workspace_id, evaluated_at)
    WHERE metric_unavailable <> '{}'::jsonb;
