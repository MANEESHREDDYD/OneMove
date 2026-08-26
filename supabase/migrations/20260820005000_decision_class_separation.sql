-- F-005: separate solver-derived metrics from operator claims.
--
-- decision_records has ONE set of metric columns, so a hand-authored decision and
-- a solver-derived one wrote to the same slots. An independent certifier posted
-- invented facilities, an invented OSRM hash and 100% coverage and received 201
-- with a persisted decision_id. Labelling the record MANUAL_OPERATOR_DECISION
-- improved honesty but did not stop caller numbers occupying authoritative
-- columns, so every downstream reader -- replay, evidence, analytics -- still
-- treated them as computed.
--
-- The authoritative columns now hold ONLY values derived from a real solver run.
-- Operator-supplied figures live in operator_claims, which no reader may treat as
-- DERIVED. That is why the metric columns become nullable: for a manual decision
-- there IS no derived value, and a zero or a copied claim would both be lies.

ALTER TABLE public.decision_records
    ADD COLUMN IF NOT EXISTS decision_class TEXT NOT NULL DEFAULT 'OPTIMIZER_DECISION';

ALTER TABLE public.decision_records
    DROP CONSTRAINT IF EXISTS chk_decision_class;

ALTER TABLE public.decision_records
    ADD CONSTRAINT chk_decision_class
    CHECK (decision_class IN ('OPTIMIZER_DECISION', 'MANUAL_OPERATOR_DECISION'));

-- Operator-supplied figures, never authoritative. Shape:
--   {"coverage_basis_points": {"value": 9910, "evidence_class": "UNVERIFIED"}, ...}
ALTER TABLE public.decision_records
    ADD COLUMN IF NOT EXISTS operator_claims JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE public.decision_records
    ADD COLUMN IF NOT EXISTS operator_rationale TEXT;

-- Which lineage fields were checked against a canonical source, and the outcome.
-- A field absent from this map was never verified and must not be presented as if
-- it were.
ALTER TABLE public.decision_records
    ADD COLUMN IF NOT EXISTS lineage_verified JSONB NOT NULL DEFAULT '{}'::jsonb;

-- A manual decision has no solver-derived metrics. NULL is the truthful value.
ALTER TABLE public.decision_records ALTER COLUMN objective_value          DROP NOT NULL;
ALTER TABLE public.decision_records ALTER COLUMN expected_travel_seconds  DROP NOT NULL;
ALTER TABLE public.decision_records ALTER COLUMN p95_travel_seconds       DROP NOT NULL;
ALTER TABLE public.decision_records ALTER COLUMN coverage_basis_points    DROP NOT NULL;

-- An OPTIMIZER_DECISION must still carry every derived metric: nullability exists
-- for the manual class only, and must not become a loophole for the optimizer path.
ALTER TABLE public.decision_records
    DROP CONSTRAINT IF EXISTS chk_optimizer_decision_metrics_complete;

ALTER TABLE public.decision_records
    ADD CONSTRAINT chk_optimizer_decision_metrics_complete
    CHECK (
        decision_class <> 'OPTIMIZER_DECISION'
        OR (
            objective_value IS NOT NULL
            AND expected_travel_seconds IS NOT NULL
            AND p95_travel_seconds IS NOT NULL
            AND coverage_basis_points IS NOT NULL
        )
    );

-- A manual decision must carry a rationale; an unexplained one is indistinguishable
-- from an accident.
ALTER TABLE public.decision_records
    DROP CONSTRAINT IF EXISTS chk_manual_decision_has_rationale;

ALTER TABLE public.decision_records
    ADD CONSTRAINT chk_manual_decision_has_rationale
    CHECK (
        decision_class <> 'MANUAL_OPERATOR_DECISION'
        OR (operator_rationale IS NOT NULL AND length(trim(operator_rationale)) >= 20)
    );

CREATE INDEX IF NOT EXISTS idx_decision_records_class
    ON public.decision_records (workspace_id, decision_class, decision_time DESC);
