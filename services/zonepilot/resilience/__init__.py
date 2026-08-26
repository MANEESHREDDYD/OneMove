"""R4 Network Resilience and Stress Testing Package."""

from services.zonepilot.resilience.contracts import (
    METRIC_FIELDS,
    CapacityAssumption,
    CoverageAssumption,
    FrozenScenarioInputs,
    MetricUnavailable,
    ResilienceEvaluationResult,
    ResilienceMetrics,
    ResilienceScenario,
    ScenarioComparison,
    ScenarioDisruption,
    ScenarioType,
)
from services.zonepilot.resilience.derivation import (
    DEFAULT_COVERAGE_ASSUMPTION,
    DerivedCounts,
    ScenarioNotRepresentable,
    build_frozen_inputs,
    derive_counts,
    resolve_disruption,
    scenario_durations,
)
from services.zonepilot.resilience.engine import (
    ResilienceEngine,
    compare_scenarios,
    compute_metrics,
    metrics_from_counts,
)

__all__ = [
    "DEFAULT_COVERAGE_ASSUMPTION",
    "METRIC_FIELDS",
    "CapacityAssumption",
    "CoverageAssumption",
    "DerivedCounts",
    "FrozenScenarioInputs",
    "MetricUnavailable",
    "ResilienceEngine",
    "ResilienceEvaluationResult",
    "ResilienceMetrics",
    "ResilienceScenario",
    "ScenarioComparison",
    "ScenarioDisruption",
    "ScenarioNotRepresentable",
    "ScenarioType",
    "build_frozen_inputs",
    "compare_scenarios",
    "compute_metrics",
    "derive_counts",
    "metrics_from_counts",
    "resolve_disruption",
    "scenario_durations",
]
