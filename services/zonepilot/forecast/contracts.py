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


NOT_EVALUATED_STATUS = "NOT_EVALUATED_NO_SCORED_SAMPLES"
EVIDENCE_ACCUMULATING_STATUS = "ENGINEERING_COMPLETE_EVIDENCE_ACCUMULATING"


class ForecastEvaluationResult(BaseModel):
    """An accuracy report that can only describe measurements it actually made.

    ``sample_count`` used to be the number of CANDIDATE test rows while mae/rmse
    fell back to 0.0 whenever nothing was scored, so an evaluation that measured
    nothing reported flawless accuracy over a non-zero sample (F-018). Now
    ``sample_count`` counts scored samples only, the error metrics are optional,
    and the validator below makes "zero samples, zero error" unrepresentable.
    """

    target: ForecastTarget
    model: BaselineModelType
    # Samples ACTUALLY SCORED: a prediction was produced and compared against a
    # usable observation. Candidates that were skipped are NOT counted here.
    sample_count: int = Field(ge=0)
    # Test-partition rows considered, scored or not.
    candidate_sample_count: int = Field(default=0, ge=0)
    # Candidates that could not be scored (no history to predict from, or no
    # usable observed value to compare against).
    unscored_sample_count: int = Field(default=0, ge=0)
    # Rows excluded from BOTH partitions because their availability time is
    # missing or unparseable, so they cannot be placed on the timeline at all.
    excluded_record_count: int = Field(default=0, ge=0)
    # None means NOT MEASURED. Zero error over zero measurements is not accuracy.
    mae: float | None = None
    rmse: float | None = None
    # None means not measured. Prediction intervals are not produced yet, so
    # interval coverage cannot be computed; asserting 1.0 claimed perfect
    # calibration that was never evaluated (F-018).
    coverage_rate: float | None = None
    chronological_split_cutoff: datetime
    evaluation_status: str = EVIDENCE_ACCUMULATING_STATUS

    @model_validator(mode="after")
    def _metrics_require_measurements(self) -> "ForecastEvaluationResult":
        if self.candidate_sample_count < self.sample_count:
            raise ValueError("candidate_sample_count cannot be smaller than the number of scored samples")
        if self.unscored_sample_count != self.candidate_sample_count - self.sample_count:
            raise ValueError("unscored_sample_count must equal candidate_sample_count minus sample_count")
        if self.sample_count == 0:
            reported = [name for name in ("mae", "rmse", "coverage_rate") if getattr(self, name) is not None]
            if reported:
                raise ValueError(
                    f"no samples were scored, so no accuracy metric can be reported; remove: {', '.join(reported)}"
                )
            return self
        if self.mae is None or self.rmse is None:
            raise ValueError("scored samples require both mae and rmse")
        if self.mae < 0 or self.rmse < 0:
            raise ValueError("error metrics must not be negative")
        return self
