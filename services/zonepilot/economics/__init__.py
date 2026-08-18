"""R5 Proxy Economics and Experiment Registry Package."""

from services.zonepilot.economics.contracts import (
    ExperimentDefinition,
    ExperimentEvaluation,
    ExperimentStatus,
    FrontierPoint,
    ProxyEconomicsMetric,
)
from services.zonepilot.economics.registry import (
    CANONICAL_EXPERIMENTS,
    compute_proxy_economics,
    evaluate_experiment,
)

__all__ = [
    "CANONICAL_EXPERIMENTS",
    "ExperimentDefinition",
    "ExperimentEvaluation",
    "ExperimentStatus",
    "FrontierPoint",
    "ProxyEconomicsMetric",
    "compute_proxy_economics",
    "evaluate_experiment",
]
