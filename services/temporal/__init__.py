"""Leakage-safe temporal contracts and deterministic dataset operations."""

from services.temporal.contracts import (
    EvidenceClass,
    OutcomeRecord,
    OutcomeStatus,
    PointInTimeQuery,
    PredictionRecord,
    TemporalFeatureRecord,
    prediction_fingerprint,
)
from services.temporal.joins import JoinStatus, PointInTimeJoinResult, point_in_time_join
from services.temporal.registry import TEMPORAL_SCHEMA_REGISTRY, SchemaRegistration
from services.temporal.splits import (
    TemporalSplitBoundaries,
    TemporalSplitResult,
    TemporalSplitTimeField,
    split_temporal_records,
)

__all__ = [
    "EvidenceClass",
    "JoinStatus",
    "OutcomeRecord",
    "OutcomeStatus",
    "PointInTimeJoinResult",
    "PointInTimeQuery",
    "PredictionRecord",
    "SchemaRegistration",
    "TEMPORAL_SCHEMA_REGISTRY",
    "TemporalFeatureRecord",
    "TemporalSplitBoundaries",
    "TemporalSplitResult",
    "TemporalSplitTimeField",
    "point_in_time_join",
    "prediction_fingerprint",
    "split_temporal_records",
]
