"""Versioned temporal records used before any forecasting model is trained."""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FeatureValue = bool | int | float | str | None


class EvidenceClass(str, Enum):
    OBSERVED = "OBSERVED"
    PUBLIC_OFFICIAL = "PUBLIC_OFFICIAL"
    PUBLIC_GEOGRAPHIC = "PUBLIC_GEOGRAPHIC"
    PROVIDER_ESTIMATED = "PROVIDER_ESTIMATED"
    DERIVED = "DERIVED"
    SIMULATED = "SIMULATED"
    ASSUMPTION = "ASSUMPTION"
    STAGING_DO_NOT_USE = "STAGING_DO_NOT_USE"
    TEST_ONLY = "TEST_ONLY"


class OutcomeStatus(str, Enum):
    PENDING = "PENDING"
    JOINED = "JOINED"
    EVALUATED = "EVALUATED"
    REJECTED = "REJECTED"


class StrictContract(BaseModel):
    """Reject implicit Python coercion and unknown contract fields."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return value.astimezone(timezone.utc)


def _validate_text(value: str) -> str:
    if not value.strip():
        raise ValueError("identifier must not be blank")
    return value


class TemporalFeatureRecord(StrictContract):
    """Canonical, availability-aware feature record.

    ``event_time`` says when the source event occurred, ``valid_at`` says when
    the value applies, and ``information_available_at`` is the hard leakage
    boundary. Provider payloads must be adapted into this contract rather than
    becoming permanent internal schemas.
    """

    record_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    schema_name: str = Field(default="zonepilot.temporal_feature", min_length=1)
    schema_version: str = Field(default="1.0.0", min_length=1)
    entity_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    event_time: datetime
    issued_at: datetime
    information_available_at: datetime
    valid_at: datetime
    retrieved_at: datetime
    source: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    evidence_class: EvidenceClass
    features: dict[str, FeatureValue]
    feature_units: dict[str, str]

    @field_validator(
        "event_time",
        "issued_at",
        "information_available_at",
        "valid_at",
        "retrieved_at",
    )
    @classmethod
    def timestamps_are_utc_aware(cls, value: datetime) -> datetime:
        return _utc_aware(value)

    @field_validator(
        "record_id",
        "dataset_id",
        "dataset_version",
        "schema_name",
        "schema_version",
        "entity_id",
        "zone_id",
        "source",
        "source_version",
    )
    @classmethod
    def identifiers_are_not_blank(cls, value: str) -> str:
        return _validate_text(value)

    @field_validator("features")
    @classmethod
    def features_are_named_and_finite(cls, features: dict[str, FeatureValue]) -> dict[str, FeatureValue]:
        for name, value in features.items():
            if not name.strip():
                raise ValueError("feature names must not be blank")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"feature {name!r} must be finite")
        return features

    @field_validator("feature_units")
    @classmethod
    def units_are_not_blank(cls, units: dict[str, str]) -> dict[str, str]:
        if any(not name.strip() or not unit.strip() for name, unit in units.items()):
            raise ValueError("feature unit names and values must not be blank")
        return units

    @model_validator(mode="after")
    def validate_availability_timeline(self) -> Self:
        if self.issued_at > self.information_available_at:
            raise ValueError("issued_at must not be after information_available_at")
        if self.information_available_at > self.retrieved_at:
            raise ValueError("information_available_at must not be after retrieved_at")
        if self.features.keys() != self.feature_units.keys():
            raise ValueError("feature_units must define exactly one unit for every feature")
        return self


class PointInTimeQuery(StrictContract):
    query_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    decision_time: datetime
    as_of_valid_at: datetime | None = None
    dataset_id: str | None = Field(default=None, min_length=1)
    dataset_version: str | None = Field(default=None, min_length=1)

    @field_validator("decision_time", "as_of_valid_at")
    @classmethod
    def timestamps_are_utc_aware(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc_aware(value)

    @field_validator("query_id", "entity_id", "zone_id", "dataset_id", "dataset_version")
    @classmethod
    def identifiers_are_not_blank(cls, value: str | None) -> str | None:
        return None if value is None else _validate_text(value)

    @property
    def validity_cutoff(self) -> datetime:
        return self.as_of_valid_at or self.decision_time


class PredictionRecord(StrictContract):
    """Immutable prediction snapshot suitable for prospective evaluation."""

    schema_name: str = Field(default="zonepilot.prediction", min_length=1)
    schema_version: str = Field(default="1.0.0", min_length=1)
    prediction_id: str = Field(min_length=1)
    prediction_time: datetime
    frozen_at: datetime
    horizon: timedelta
    target_time: datetime
    predicted_value: float
    target_unit: str = Field(min_length=1)
    lower_bound: float | None = None
    upper_bound: float | None = None
    model_version: str = Field(min_length=1)
    feature_dataset_version: str = Field(min_length=1)
    graph_version: str = Field(min_length=1)
    code_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    evidence_ids: tuple[str, ...] = ()

    @field_validator("prediction_time", "frozen_at", "target_time")
    @classmethod
    def timestamps_are_utc_aware(cls, value: datetime) -> datetime:
        return _utc_aware(value)

    @field_validator(
        "schema_name",
        "schema_version",
        "prediction_id",
        "target_unit",
        "model_version",
        "feature_dataset_version",
        "graph_version",
    )
    @classmethod
    def identifiers_are_not_blank(cls, value: str) -> str:
        return _validate_text(value)

    @field_validator("predicted_value", "lower_bound", "upper_bound")
    @classmethod
    def numeric_values_are_finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("prediction values must be finite")
        return value

    @model_validator(mode="after")
    def validate_prediction_timeline(self) -> Self:
        if self.horizon <= timedelta(0):
            raise ValueError("horizon must be positive")
        if self.target_time != self.prediction_time + self.horizon:
            raise ValueError("target_time must equal prediction_time plus horizon")
        if not self.prediction_time <= self.frozen_at < self.target_time:
            raise ValueError("frozen_at must be on or after prediction_time and before target_time")
        if self.lower_bound is not None and self.predicted_value < self.lower_bound:
            raise ValueError("predicted_value must not be below lower_bound")
        if self.upper_bound is not None and self.predicted_value > self.upper_bound:
            raise ValueError("predicted_value must not exceed upper_bound")
        if self.lower_bound is not None and self.upper_bound is not None and self.lower_bound > self.upper_bound:
            raise ValueError("lower_bound must not exceed upper_bound")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence_ids must be unique")
        if any(not evidence_id.strip() for evidence_id in self.evidence_ids):
            raise ValueError("evidence_ids must not contain blank identifiers")
        return self


def prediction_fingerprint(prediction: PredictionRecord) -> str:
    """Return a stable content hash for detecting rewritten predictions."""

    payload = prediction.model_dump_json(exclude_none=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class OutcomeRecord(StrictContract):
    schema_name: str = Field(default="zonepilot.outcome", min_length=1)
    schema_version: str = Field(default="1.0.0", min_length=1)
    outcome_id: str = Field(min_length=1)
    prediction_id: str = Field(min_length=1)
    target_time: datetime
    observation_time: datetime
    availability_time: datetime
    actual_target: float | None = None
    target_unit: str = Field(min_length=1)
    status: OutcomeStatus
    evaluation_reason: str | None = None

    @field_validator("target_time", "observation_time", "availability_time")
    @classmethod
    def timestamps_are_utc_aware(cls, value: datetime) -> datetime:
        return _utc_aware(value)

    @field_validator("schema_name", "schema_version", "outcome_id", "prediction_id", "target_unit")
    @classmethod
    def identifiers_are_not_blank(cls, value: str) -> str:
        return _validate_text(value)

    @field_validator("actual_target")
    @classmethod
    def actual_target_is_finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("actual_target must be finite")
        return value

    @model_validator(mode="after")
    def validate_outcome_timeline_and_status(self) -> Self:
        if self.target_time > self.observation_time:
            raise ValueError("observation_time must not precede target_time")
        if self.observation_time > self.availability_time:
            raise ValueError("availability_time must not precede observation_time")
        if self.status in {OutcomeStatus.JOINED, OutcomeStatus.EVALUATED} and self.actual_target is None:
            raise ValueError("joined and evaluated outcomes require actual_target")
        if self.status is OutcomeStatus.PENDING and self.actual_target is not None:
            raise ValueError("pending outcomes must not contain actual_target")
        if self.status is OutcomeStatus.REJECTED and not self.evaluation_reason:
            raise ValueError("rejected outcomes require evaluation_reason")
        return self
