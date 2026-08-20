"""Contracts for R2 Forecast subsystem targeting observable network/weather states."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator

from services.zonepilot.release import current_release_sha


class ForecastTarget(str, Enum):
    WEATHER_TRAVEL_INFLATION_PERCENT = "WEATHER_TRAVEL_INFLATION_PERCENT"
    HOURLY_PRECIPITATION_MM = "HOURLY_PRECIPITATION_MM"
    HOURLY_WIND_SPEED_KMH = "HOURLY_WIND_SPEED_KMH"
    HOURLY_SURFACE_PRESSURE_HPA = "HOURLY_SURFACE_PRESSURE_HPA"


class BaselineModelType(str, Enum):
    LAST_OBSERVATION = "LAST_OBSERVATION"
    ROLLING_MEDIAN = "ROLLING_MEDIAN"
    PRIOR_DAY_SAME_HOUR = "PRIOR_DAY_SAME_HOUR"
    PRIOR_WEEK_SAME_HOUR = "PRIOR_WEEK_SAME_HOUR"


class PredictionRecord(BaseModel):
    prediction_id: str
    workspace_id: str
    zone_id: str
    prediction_time: datetime
    target_time: datetime
    horizon_hours: int
    target: ForecastTarget
    predicted_value: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    baseline_model: BaselineModelType

    # Provenance. None means "not established", which is the truthful value while
    # no forecast is actually produced. These previously defaulted to literals
    # ("1.0.0", "1.1", a model version for an unwired model), so a record with
    # predicted_value=None still asserted a dataset, a graph and a model it never
    # used (F-018).
    model_version: str | None = None
    feature_snapshot_hash: str | None = None
    dataset_version: str | None = None
    graph_version: str | None = None
    code_sha: str = Field(default_factory=current_release_sha)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _provenance_required_when_predicting(self) -> "PredictionRecord":
        """A real prediction must carry real lineage; an empty one must claim none."""
        if self.predicted_value is None:
            return self
        missing = [
            name
            for name in ("model_version", "feature_snapshot_hash", "dataset_version", "graph_version")
            if not getattr(self, name)
        ]
        if missing:
            raise ValueError(f"a prediction with a value requires provenance; missing: {', '.join(missing)}")
        return self


class ForecastEvaluationResult(BaseModel):
    target: ForecastTarget
    model: BaselineModelType
    sample_count: int
    mae: float
    rmse: float
    # None means not measured. Prediction intervals are not produced yet, so
    # interval coverage cannot be computed; asserting 1.0 claimed perfect
    # calibration that was never evaluated (F-018).
    coverage_rate: float | None = None
    chronological_split_cutoff: datetime
    evaluation_status: str = "ENGINEERING_COMPLETE_EVIDENCE_ACCUMULATING"
