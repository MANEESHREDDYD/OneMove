"""Machine-readable registry metadata for persisted temporal contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from services.temporal.contracts import OutcomeRecord, PredictionRecord, TemporalFeatureRecord


@dataclass(frozen=True)
class SchemaRegistration:
    schema_name: str
    schema_version: str
    compatibility_policy: str
    model: type[BaseModel]
    units: dict[str, str]
    evidence_semantics: str
    timestamp_semantics: dict[str, str]

    @property
    def required_fields(self) -> tuple[str, ...]:
        return tuple(name for name, field in self.model.model_fields.items() if field.is_required())

    @property
    def nullable_fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, field in self.model.model_fields.items()
            if field.annotation is not None and type(None) in getattr(field.annotation, "__args__", ())
        )


TEMPORAL_SCHEMA_REGISTRY = {
    "zonepilot.temporal_feature@1.0.0": SchemaRegistration(
        schema_name="zonepilot.temporal_feature",
        schema_version="1.0.0",
        compatibility_policy="BACKWARD_COMPATIBLE_WITHIN_MAJOR",
        model=TemporalFeatureRecord,
        units={"features": "declared per key in feature_units"},
        evidence_semantics="evidence_class is required on every feature record",
        timestamp_semantics={
            "event_time": "UTC instant when the source event occurred",
            "issued_at": "UTC instant when the source issued the value",
            "information_available_at": "UTC leakage cutoff; must be <= decision_time",
            "valid_at": "UTC instant when the value applies",
            "retrieved_at": "UTC instant when ZonePilot retrieved the value",
        },
    ),
    "zonepilot.prediction@1.0.0": SchemaRegistration(
        schema_name="zonepilot.prediction",
        schema_version="1.0.0",
        compatibility_policy="BACKWARD_COMPATIBLE_WITHIN_MAJOR",
        model=PredictionRecord,
        units={"predicted_value": "target_unit", "horizon": "ISO 8601 duration"},
        evidence_semantics="evidence_ids link the immutable prediction to source evidence",
        timestamp_semantics={
            "prediction_time": "UTC decision instant",
            "frozen_at": "UTC instant the immutable record was frozen",
            "target_time": "UTC prediction target instant",
        },
    ),
    "zonepilot.outcome@1.0.0": SchemaRegistration(
        schema_name="zonepilot.outcome",
        schema_version="1.0.0",
        compatibility_policy="BACKWARD_COMPATIBLE_WITHIN_MAJOR",
        model=OutcomeRecord,
        units={"actual_target": "target_unit"},
        evidence_semantics="status distinguishes pending, joined, evaluated, and rejected outcomes",
        timestamp_semantics={
            "target_time": "UTC target instant copied from the prediction",
            "observation_time": "UTC instant represented by the actual",
            "availability_time": "UTC instant the actual became usable for evaluation",
        },
    ),
}
