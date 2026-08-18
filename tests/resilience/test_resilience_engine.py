"""Tests for R4 Network Resilience engine."""

from __future__ import annotations

import pytest
from services.temporal.contracts import EvidenceClass
from services.zonepilot.resilience.contracts import (
    ResilienceEvaluationResult,
    ResilienceMetrics,
    ResilienceScenario,
    ScenarioComparison,
    ScenarioType,
)
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
            parameters={},
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
    durations = [400, 500, 650, 800, 1100]
    result = engine.evaluate_scenario(scenario, durations)

    assert result.evaluation_id.startswith("eval-")
    assert result.metrics.coverage_basis_points == 10_000
    assert result.metrics.p95_duration_seconds == 1100
    assert result.fail_closed is False
