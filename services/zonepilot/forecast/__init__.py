"""R2 Forecast subsystem."""

from services.zonepilot.forecast.contracts import (
    BaselineModelType,
    ForecastEvaluationResult,
    ForecastTarget,
    PredictionRecord,
)
from services.zonepilot.forecast.baselines import BaselineForecaster
from services.zonepilot.forecast.evaluator import evaluate_chronological
from services.zonepilot.forecast.features import extract_point_in_time_features, compute_feature_snapshot_hash
from services.zonepilot.forecast.repository import ForecastRepository

__all__ = [
    "BaselineModelType",
    "ForecastEvaluationResult",
    "ForecastTarget",
    "PredictionRecord",
    "BaselineForecaster",
    "evaluate_chronological",
    "extract_point_in_time_features",
    "compute_feature_snapshot_hash",
    "ForecastRepository",
]
