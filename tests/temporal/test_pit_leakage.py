"""F-020: a record observed after the cutoff must not enter training.

split_temporal_records defaulted its boundary to event_time. Point-in-time
correctness depends on when a fact became KNOWABLE, not when it occurred, so a
record describing something before the cutoff but only observed afterwards leaked
future information into the training partition.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.temporal.contracts import EvidenceClass, TemporalFeatureRecord
from services.temporal.splits import (
    TemporalSplitBoundaries,
    TemporalSplitTimeField,
    split_temporal_records,
)

CUTOFF = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
BOUNDARIES = TemporalSplitBoundaries(
    train_end=CUTOFF,
    validation_end=CUTOFF + timedelta(hours=1),
    test_end=CUTOFF + timedelta(hours=2),
)


def _record(record_id: str, event_time: datetime, available_at: datetime) -> TemporalFeatureRecord:
    return TemporalFeatureRecord(
        record_id=record_id,
        dataset_id="ds-test",
        dataset_version="1.0.0",
        entity_id="zone:test",
        zone_id="8860145b59fffff",
        event_time=event_time,
        issued_at=available_at,
        information_available_at=available_at,
        valid_at=event_time,
        retrieved_at=available_at,
        source="unit-test",
        source_version="1.0.0",
        evidence_class=EvidenceClass.DERIVED,
        features={"test_metric": 1.0},
        feature_units={"test_metric": "count"},
    )


def test_default_boundary_is_information_availability() -> None:
    """The default must be the safe one; leakage should require opting in."""
    import inspect

    default = inspect.signature(split_temporal_records).parameters["time_field"].default
    assert default is TemporalSplitTimeField.INFORMATION_AVAILABLE_AT


def test_late_observed_record_is_excluded_from_training() -> None:
    """The exact adversarial case: happened before the cutoff, known after it."""
    leaky = _record(
        "leaky",
        event_time=CUTOFF - timedelta(hours=1),
        available_at=CUTOFF + timedelta(minutes=5),
    )
    legitimate = _record(
        "legitimate",
        event_time=CUTOFF - timedelta(hours=2),
        available_at=CUTOFF - timedelta(hours=2),
    )

    result = split_temporal_records([leaky, legitimate], BOUNDARIES)
    train_ids = {r.record_id for r in result.train}

    assert "legitimate" in train_ids, "a genuinely-available record must still train"
    assert "leaky" not in train_ids, "a record observed after the cutoff leaked into training"


def test_event_time_split_still_leaks_and_must_be_explicit() -> None:
    """Documents why the default changed: the old behaviour is still reachable."""
    leaky = _record(
        "leaky",
        event_time=CUTOFF - timedelta(hours=1),
        available_at=CUTOFF + timedelta(minutes=5),
    )
    result = split_temporal_records([leaky], BOUNDARIES, time_field=TemporalSplitTimeField.EVENT_TIME)
    assert {r.record_id for r in result.train} == {"leaky"}


def test_no_record_is_silently_dropped() -> None:
    records = [
        _record("a", CUTOFF - timedelta(hours=3), CUTOFF - timedelta(hours=3)),
        _record("b", CUTOFF + timedelta(minutes=30), CUTOFF + timedelta(minutes=30)),
        _record("c", CUTOFF + timedelta(hours=5), CUTOFF + timedelta(hours=5)),
    ]
    result = split_temporal_records(records, BOUNDARIES)
    total = len(result.train) + len(result.validation) + len(result.test) + len(result.prospective_holdout)
    assert total == len(records)
