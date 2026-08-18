-- 20260817003000_durable_decisions_and_scenarios.sql
-- Durable, PostgreSQL-backed storage for R4 Scenarios, R7 Decision Ledger, Replay, Shadow Loop, and R2 Forecasting.

-- 1. Resilience Scenarios and Evaluation Results
CREATE TABLE IF NOT EXISTS public.resilience_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id TEXT NOT NULL UNIQUE,
    workspace_id TEXT NOT NULL,
    scenario_type TEXT NOT NULL,
    description TEXT,
    evidence_class TEXT NOT NULL DEFAULT 'SIMULATED',
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    seed INTEGER NOT NULL DEFAULT 42,
    graph_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID,

    CONSTRAINT chk_scenario_type CHECK (
        scenario_type IN ('ROAD_CLOSURE', 'FACILITY_OUTAGE', 'CONGESTION_SPIKE', 'HEAVY_RAIN', 'CAPACITY_REDUCTION', 'COMPOUND_FAILURE', 'BASELINE')
    ),
    CONSTRAINT chk_scenario_evidence CHECK (
        evidence_class IN ('SIMULATED', 'DERIVED')
    )
);

CREATE INDEX IF NOT EXISTS idx_resilience_scenarios_ws ON public.resilience_scenarios(workspace_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.resilience_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id TEXT NOT NULL UNIQUE,
    scenario_id TEXT NOT NULL REFERENCES public.resilience_scenarios(scenario_id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    coverage_basis_points INTEGER NOT NULL,
    p50_duration_seconds INTEGER NOT NULL,
    p90_duration_seconds INTEGER NOT NULL,
    p95_duration_seconds INTEGER NOT NULL,
    disconnected_zones_count INTEGER NOT NULL,
    redundancy_index_basis_points INTEGER NOT NULL,
    failure_exposure_score INTEGER NOT NULL,
    capacity_loss_basis_points INTEGER NOT NULL,
    degradation_grade TEXT NOT NULL,
    baseline_comparison JSONB,
    code_sha TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_resilience_results_scenario ON public.resilience_results(scenario_id);
CREATE INDEX IF NOT EXISTS idx_resilience_results_ws ON public.resilience_results(workspace_id, evaluated_at DESC);

-- 2. Decision Records (Immutable Ledger)
CREATE TABLE IF NOT EXISTS public.decision_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id TEXT NOT NULL UNIQUE,
    workspace_id TEXT NOT NULL,
    decision_time TIMESTAMPTZ NOT NULL,
    network_version TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    feature_snapshot_hash TEXT NOT NULL,
    selected_action TEXT NOT NULL,
    opened_facilities TEXT[] NOT NULL,
    objective_value BIGINT NOT NULL,
    expected_travel_seconds INTEGER NOT NULL,
    p95_travel_seconds INTEGER NOT NULL,
    coverage_basis_points INTEGER NOT NULL,
    graph_version TEXT NOT NULL,
    osrm_bundle_hash TEXT NOT NULL,
    solver_version TEXT NOT NULL,
    code_sha TEXT NOT NULL,
    evidence_ids TEXT[] NOT NULL DEFAULT '{}',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    recorded_by UUID,

    CONSTRAINT chk_decision_pit_causality CHECK (decision_time <= recorded_at + interval '1 second')
);

CREATE INDEX IF NOT EXISTS idx_decision_records_ws ON public.decision_records(workspace_id, decision_time DESC);
CREATE INDEX IF NOT EXISTS idx_decision_records_hash ON public.decision_records(feature_snapshot_hash);

-- 3. Decision Replays (Deterministic Verification)
CREATE TABLE IF NOT EXISTS public.decision_replays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    replay_id TEXT NOT NULL UNIQUE,
    original_decision_id TEXT NOT NULL REFERENCES public.decision_records(decision_id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    pit_valid BOOLEAN NOT NULL,
    pit_cutoff TIMESTAMPTZ NOT NULL,
    reproduced_exact_action BOOLEAN NOT NULL,
    reproduced_exact_facilities BOOLEAN NOT NULL,
    objective_match BOOLEAN NOT NULL,
    recomputed_objective BIGINT NOT NULL,
    recomputed_facilities TEXT[] NOT NULL,
    replayed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    code_sha TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decision_replays_orig ON public.decision_replays(original_decision_id);

-- 4. Shadow Evaluations (Prospective Evaluation Loop)
CREATE TABLE IF NOT EXISTS public.shadow_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shadow_id TEXT NOT NULL UNIQUE,
    decision_id TEXT NOT NULL REFERENCES public.decision_records(decision_id) ON DELETE CASCADE,
    workspace_id TEXT NOT NULL,
    frozen_decision_time TIMESTAMPTZ NOT NULL,
    future_observation_time TIMESTAMPTZ NOT NULL,
    shadow_state TEXT NOT NULL DEFAULT 'FROZEN_AWAITING_FUTURE',
    predicted_p95_seconds INTEGER NOT NULL,
    actual_observed_p95_seconds INTEGER,
    regret_seconds INTEGER,
    outcome_status TEXT NOT NULL DEFAULT 'PENDING',
    evaluated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_shadow_state CHECK (
        shadow_state IN ('FROZEN_AWAITING_FUTURE', 'JOINED_FUTURE_OBSERVED', 'EVALUATED')
    ),
    CONSTRAINT chk_outcome_status CHECK (
        outcome_status IN ('PENDING', 'JOINED', 'EVALUATED', 'REJECTED')
    )
);

CREATE INDEX IF NOT EXISTS idx_shadow_evaluations_decision ON public.shadow_evaluations(decision_id);
CREATE INDEX IF NOT EXISTS idx_shadow_evaluations_ws ON public.shadow_evaluations(workspace_id, created_at DESC);

-- 5. Forecast Records (R2 Observable Target Predictions)
CREATE TABLE IF NOT EXISTS public.forecast_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forecast_id TEXT NOT NULL UNIQUE,
    workspace_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    target_metric TEXT NOT NULL,
    forecast_issue_time TIMESTAMPTZ NOT NULL,
    horizon_hours INTEGER NOT NULL,
    target_time TIMESTAMPTZ NOT NULL,
    predicted_value DOUBLE PRECISION NOT NULL,
    baseline_model TEXT NOT NULL,
    model_version TEXT NOT NULL,
    feature_dataset_version TEXT NOT NULL,
    graph_version TEXT NOT NULL,
    code_sha TEXT NOT NULL,
    lower_bound DOUBLE PRECISION,
    upper_bound DOUBLE PRECISION,
    evidence_ids TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_forecast_records_zone ON public.forecast_records(zone_id, target_time DESC);
CREATE INDEX IF NOT EXISTS idx_forecast_records_ws ON public.forecast_records(workspace_id, forecast_issue_time DESC);
