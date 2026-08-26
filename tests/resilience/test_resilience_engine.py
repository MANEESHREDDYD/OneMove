"""Tests for R4 Network Resilience engine."""

from __future__ import annotations

import pytest

from services.temporal.contracts import EvidenceClass
from services.zonepilot.optimization.contracts import MatrixEvidenceClass, TravelMatrix
from services.zonepilot.resilience.contracts import (
    ResilienceScenario,
    ScenarioType,
)
from services.zonepilot.resilience.derivation import build_frozen_inputs
from services.zonepilot.resilience.engine import (
    ResilienceEngine,
    compare_scenarios,
    compute_metrics,
)


def test_resilience_scenario_requires_simulated_or_derived() -> None:
    scenario = ResilienceScenario(
        scenario_id="scen-01",
        scenario_type=ScenarioType.ROAD_CLOSURE,
        description="Road closure on Outer Ring Road",
        parameters={"closed_roads": ["way:101", "way:102"]},
        graph_version="1.1",
        evidence_class=EvidenceClass.SIMULATED,
    )
    assert scenario.evidence_class == EvidenceClass.SIMULATED

    with pytest.raises(ValueError, match="Counterfactual scenarios cannot have"):
        ResilienceScenario(
            scenario_id="scen-bad",
            scenario_type=ScenarioType.ROAD_CLOSURE,
            description="Fake observed counterfactual",
            parameters={"travel_time_inflation_basis_points": 2500},
            graph_version="1.1",
            evidence_class=EvidenceClass.OBSERVED,
        )


def test_resilience_metrics_quantile_monotonicity() -> None:
    durations = [300, 450, 600, 750, 900, 1200, 1500, 1800, 2400, 3600]
    metrics = compute_metrics(
        durations,
        total_demands=10,
        covered_demands=10,
        total_capacity=1000,
        lost_capacity=0,
        zone_count=10,
        disconnected_count=0,
        redundant_facility_count=2,
        total_open_facilities=4,
    )

    assert metrics.coverage_basis_points == 10_000
    assert metrics.p50_duration_seconds <= metrics.p90_duration_seconds
    assert metrics.p90_duration_seconds <= metrics.p95_duration_seconds
    assert metrics.failure_exposure_score == 0
    assert metrics.capacity_loss_basis_points == 0


def test_resilience_scenario_comparison_and_grading() -> None:
    baseline = compute_metrics(
        [300, 400, 500, 600, 700],
        total_demands=5,
        covered_demands=5,
        total_capacity=500,
        lost_capacity=0,
        zone_count=5,
        disconnected_count=0,
        redundant_facility_count=2,
        total_open_facilities=3,
    )
    stressed = compute_metrics(
        [600, 800, 1000, 1200, 1400],
        total_demands=5,
        covered_demands=4,
        total_capacity=500,
        lost_capacity=100,
        zone_count=5,
        disconnected_count=1,
        redundant_facility_count=1,
        total_open_facilities=2,
    )

    comparison = compare_scenarios(baseline, stressed, "s1_free_flow", "s2_congested")
    assert comparison.coverage_delta_basis_points == -2000
    assert comparison.p95_inflation_seconds == 700
    assert comparison.additional_disconnected_zones == 1
    assert comparison.capacity_loss_basis_points == 2000
    assert comparison.resilience_grade in {"SEVERE_DEGRADATION", "CRITICAL_FAILURE"}


def test_resilience_engine_evaluation() -> None:
    engine = ResilienceEngine()
    scenario = ResilienceScenario(
        scenario_id="scen-heavy-rain",
        scenario_type=ScenarioType.HEAVY_RAIN,
        description="Heavy monsoon rain",
        parameters={"rain_intensity_mm": 45.0},
        graph_version="1.1",
    )
    # F-010: the engine now requires FrozenScenarioInputs built from the authentic
    # travel matrix. A bare duration sequence carries no provenance, so metrics
    # derived from it could not be classified -- which is how invented coverage and
    # capacity figures used to reach the ledger.
    matrix = TravelMatrix(
        matrix_id="matrix-test",
        graph_version="1.1",
        router="osrm-routed-table",
        router_version="1.0.0",
        evidence_class=MatrixEvidenceClass.PUBLIC_GEOGRAPHIC,
        facility_ids=("fac:01",),
        demand_ids=tuple(f"zone:{i:02d}" for i in range(1, 6)),
        durations_seconds=((400, 500, 650, 800, 1100),),
    )
    inputs = build_frozen_inputs(
        matrix,
        scenario_type=ScenarioType.HEAVY_RAIN,
        parameters={"travel_time_inflation_basis_points": 2500},
    )
    result = engine.evaluate_scenario(scenario, inputs)

    assert result.evaluation_id.startswith("eval-")
    assert result.metrics.coverage_basis_points == 10_000
    # 1100 * 1.25 under a 2500bp inflation. The previous expectation of 1100 was
    # the UNDISTURBED baseline: the old engine ignored the scenario entirely and
    # reported the baseline as the failure result (F-010).
    assert result.metrics.p95_duration_seconds == 1375
    assert result.fail_closed is False
