"""Contracts for R2 Forecast subsystem targeting observable network/weather states."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

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
    predicted_value: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    baseline_model: BaselineModelType
    model_version: str = "zonepilot-forecast-baseline-1.0.0"
    feature_snapshot_hash: str
    dataset_version: str = "1.0.0"
    graph_version: str = "1.1"
    code_sha: str = Field(default_factory=current_release_sha)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class ForecastEvaluationResult(BaseModel):
    target: ForecastTarget
    model: BaselineModelType
    sample_count: int
    mae: float
    rmse: float
    coverage_rate: float
    chronological_split_cutoff: datetime
    evaluation_status: str = "ENGINEERING_COMPLETE_EVIDENCE_ACCUMULATING"
