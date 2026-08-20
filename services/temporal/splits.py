"""Chronological dataset splitting; random split APIs intentionally do not exist."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Self, Sequence

from pydantic import field_validator, model_validator

from services.temporal.contracts import StrictContract, TemporalFeatureRecord, _utc_aware


class TemporalSplitTimeField(str, Enum):
    EVENT_TIME = "event_time"
    VALID_AT = "valid_at"
    INFORMATION_AVAILABLE_AT = "information_available_at"


class TemporalSplitBoundaries(StrictContract):
    train_end: datetime
    validation_end: datetime
    test_end: datetime

    @field_validator("train_end", "validation_end", "test_end")
    @classmethod
    def timestamps_are_utc_aware(cls, value: datetime) -> datetime:
        return _utc_aware(value)

    @model_validator(mode="after")
    def boundaries_are_strictly_increasing(self) -> Self:
        if not self.train_end < self.validation_end < self.test_end:
            raise ValueError("split boundaries must be strictly increasing")
        return self


class TemporalSplitResult(StrictContract):
    time_field: TemporalSplitTimeField
    boundaries: TemporalSplitBoundaries
    train: tuple[TemporalFeatureRecord, ...]
    validation: tuple[TemporalFeatureRecord, ...]
    test: tuple[TemporalFeatureRecord, ...]
    prospective_holdout: tuple[TemporalFeatureRecord, ...]


def split_temporal_records(
    records: Sequence[TemporalFeatureRecord],
    boundaries: TemporalSplitBoundaries,
    *,
    time_field: TemporalSplitTimeField = TemporalSplitTimeField.INFORMATION_AVAILABLE_AT,
) -> TemporalSplitResult:
    """Assign every record to a deterministic chronological partition.

    Boundary timestamps are inclusive for the partition they terminate. Records
    after ``test_end`` are preserved as the prospective holdout; none are silently
    discarded.

    The split boundary defaults to ``information_available_at``, not ``event_time``
    (F-020). What matters for point-in-time correctness is when a fact BECAME
    KNOWABLE, not when it occurred. A record describing something that happened
    before the cutoff but was only observed afterwards is future information: with
    an event_time split it lands in train and leaks. Callers may still pass
    ``EVENT_TIME`` explicitly for descriptive, non-predictive partitioning, but it
    must be a deliberate choice rather than the default.
    """

    ordered = sorted(records, key=lambda record: (getattr(record, time_field.value), record.record_id))
    train: list[TemporalFeatureRecord] = []
    validation: list[TemporalFeatureRecord] = []
    test: list[TemporalFeatureRecord] = []
    prospective_holdout: list[TemporalFeatureRecord] = []

    for record in ordered:
        split_time = getattr(record, time_field.value)
        if split_time <= boundaries.train_end:
            train.append(record)
        elif split_time <= boundaries.validation_end:
            validation.append(record)
        elif split_time <= boundaries.test_end:
            test.append(record)
        else:
            prospective_holdout.append(record)

    return TemporalSplitResult(
        time_field=time_field,
        boundaries=boundaries,
        train=tuple(train),
        validation=tuple(validation),
        test=tuple(test),
        prospective_holdout=tuple(prospective_holdout),
    )
