-- Record which mathematical policy produced each decision.
--
-- Optimization policy 2.0.0 changed capacity semantics, normalised the
-- objective components, and made assignments canonically reconstructed. A
-- decision frozen under the previous policy cannot be meaningfully recomputed
-- under the current one: replaying it would compare answers from two different
-- models and report the difference as drift, which reads as "same model,
-- different answer" and is false.
--
-- Existing rows stay NULL on purpose. NULL means "frozen before policy
-- versioning existed", which the replay path treats as legacy and refuses to
-- restate under current mathematics. Backfilling a version onto historical
-- rows would assert something we cannot know.

ALTER TABLE public.decision_records
    ADD COLUMN IF NOT EXISTS optimization_policy_version TEXT;

-- The legacy column keeps its name so frozen history stays readable, but the
-- value is a probability-weighted P95 across SCENARIO TOTAL demand-weighted
-- travel: the unit is demand_units*seconds, not seconds. New rows populate the
-- explicitly named column alongside it.
ALTER TABLE public.decision_records
    ADD COLUMN IF NOT EXISTS p95_scenario_total_travel_demand_seconds BIGINT;

COMMENT ON COLUMN public.decision_records.optimization_policy_version IS
    'Mathematical policy version that produced this decision. NULL = pre-versioning legacy record.';
COMMENT ON COLUMN public.decision_records.p95_travel_seconds IS
    'LEGACY NAME. Unit is demand_units*seconds, not seconds. See p95_scenario_total_travel_demand_seconds.';
