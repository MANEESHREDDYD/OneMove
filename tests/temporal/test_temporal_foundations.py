from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from services.temporal import (
    TEMPORAL_SCHEMA_REGISTRY,
    EvidenceClass,
    JoinStatus,
    OutcomeRecord,
    OutcomeStatus,
    PointInTimeQuery,
    PredictionRecord,
    TemporalFeatureRecord,
    TemporalSplitBoundaries,
    TemporalSplitTimeField,
    point_in_time_join,
    prediction_fingerprint,
    split_temporal_records,
)

UTC = timezone.utc


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 13, hour, minute, tzinfo=UTC)


def feature(
    record_id: str,
    *,
    valid_at: datetime,
    available_at: datetime,
    retrieved_at: datetime | None = None,
    value: float = 1.0,
) -> TemporalFeatureRecord:
    return TemporalFeatureRecord(
        record_id=record_id,
        dataset_id="traffic-speed",
        dataset_version="2026-08-13.1",
        entity_id="segment-1",
        zone_id="8861892583fffff",
        event_time=valid_at,
        issued_at=available_at - timedelta(minutes=1),
        information_available_at=available_at,
        valid_at=valid_at,
        retrieved_at=retrieved_at or available_at,
        source="provider-adapter",
        source_version="v3",
        evidence_class=EvidenceClass.PROVIDER_ESTIMATED,
        features={"speed_kph": value},
        feature_units={"speed_kph": "km/h"},
    )


def test_temporal_contract_rejects_naive_time_and_implicit_identifier_coercion():
    payload = feature("valid", valid_at=at(9), available_at=at(8, 50)).model_dump()
    payload["event_time"] = datetime(2026, 8, 13, 9)
    with pytest.raises(ValidationError, match="UTC offset"):
        TemporalFeatureRecord.model_validate(payload)

    payload = feature("valid", valid_at=at(9), available_at=at(8, 50)).model_dump()
    payload["record_id"] = 123
    with pytest.raises(ValidationError):
        TemporalFeatureRecord.model_validate(payload)


def test_temporal_contract_rejects_impossible_availability_and_nonfinite_features():
    with pytest.raises(ValidationError, match="information_available_at must not be after"):
        feature(
            "bad-timeline",
            valid_at=at(10),
            available_at=at(8),
            retrieved_at=at(7, 59),
        )

    payload = feature("bad-value", valid_at=at(10), available_at=at(8)).model_dump()
    payload["features"] = {"speed_kph": float("nan")}
    with pytest.raises(ValidationError, match="must be finite"):
        TemporalFeatureRecord.model_validate(payload)

    payload = feature("bad-units", valid_at=at(10), available_at=at(8)).model_dump()
    payload["feature_units"] = {"travel_time": "seconds"}
    with pytest.raises(ValidationError, match="exactly one unit"):
        TemporalFeatureRecord.model_validate(payload)


def test_point_in_time_join_excludes_late_arrivals_and_selects_latest_eligible_version():
    older = feature("older", valid_at=at(9), available_at=at(9, 5), value=21.0)
    selected = feature("selected", valid_at=at(9, 15), available_at=at(9, 20), value=19.0)
    leaked = feature("late-arrival", valid_at=at(9, 30), available_at=at(10, 1), value=4.0)
    query = PointInTimeQuery(
        query_id="decision-1",
        entity_id="segment-1",
        zone_id="8861892583fffff",
        decision_time=at(10),
    )

    result = point_in_time_join([query], [leaked, older, selected])[0]

    assert result.status is JoinStatus.MATCHED
    assert result.feature_record is not None
    assert result.feature_record.record_id == "selected"
    assert result.feature_record.information_available_at <= query.decision_time


def test_point_in_time_join_supports_future_validity_without_future_information():
    forecast = feature("forecast", valid_at=at(11), available_at=at(9, 55), value=18.0)
    now_query = PointInTimeQuery(
        query_id="now",
        entity_id="segment-1",
        zone_id="8861892583fffff",
        decision_time=at(10),
    )
    target_query = PointInTimeQuery(
        query_id="future-target",
        entity_id="segment-1",
        zone_id="8861892583fffff",
        decision_time=at(10),
        as_of_valid_at=at(11),
    )

    now_result, target_result = point_in_time_join([now_query, target_query], [forecast])

    assert now_result.status is JoinStatus.NO_MATCH
    assert target_result.status is JoinStatus.MATCHED


def test_point_in_time_join_requires_unique_query_ids():
    query = PointInTimeQuery(
        query_id="duplicate",
        entity_id="segment-1",
        zone_id="8861892583fffff",
        decision_time=at(10),
    )
    with pytest.raises(ValueError, match="query_id values must be unique"):
        point_in_time_join([query, query], [])


def test_temporal_split_is_chronological_deterministic_and_complete():
    records = [
        feature("holdout", valid_at=at(13), available_at=at(13)),
        feature("validation", valid_at=at(10), available_at=at(10)),
        feature("train", valid_at=at(9), available_at=at(9)),
        feature("test", valid_at=at(11), available_at=at(11)),
    ]
    boundaries = TemporalSplitBoundaries(train_end=at(9), validation_end=at(10), test_end=at(11))

    result = split_temporal_records(records, boundaries, time_field=TemporalSplitTimeField.VALID_AT)

    assert [row.record_id for row in result.train] == ["train"]
    assert [row.record_id for row in result.validation] == ["validation"]
    assert [row.record_id for row in result.test] == ["test"]
    assert [row.record_id for row in result.prospective_holdout] == ["holdout"]
    assert sum(map(len, (result.train, result.validation, result.test, result.prospective_holdout))) == len(records)


def test_temporal_split_rejects_overlapping_or_naive_boundaries():
    with pytest.raises(ValidationError, match="strictly increasing"):
        TemporalSplitBoundaries(train_end=at(10), validation_end=at(10), test_end=at(11))
    with pytest.raises(ValidationError, match="UTC offset"):
        TemporalSplitBoundaries(
            train_end=datetime(2026, 8, 13, 9),
            validation_end=at(10),
            test_end=at(11),
        )


def test_prediction_record_is_frozen_hashable_and_tied_to_target_horizon():
    prediction = PredictionRecord(
        prediction_id="pred-1",
        prediction_time=at(10),
        frozen_at=at(10, 1),
        horizon=timedelta(hours=1),
        target_time=at(11),
        predicted_value=18.2,
        target_unit="km/h",
        lower_bound=16.0,
        upper_bound=21.0,
        model_version="persistence-v1",
        feature_dataset_version="2026-08-13.1",
        graph_version="graph-1.1",
        code_sha="a" * 40,
        evidence_ids=("ev-1",),
    )

    assert prediction_fingerprint(prediction) == prediction_fingerprint(prediction)
    with pytest.raises(ValidationError, match="frozen"):
        prediction.predicted_value = 99.0

    invalid = prediction.model_dump()
    invalid["target_time"] = at(12)
    with pytest.raises(ValidationError, match="target_time must equal"):
        PredictionRecord.model_validate(invalid)


def test_outcome_contract_enforces_observation_availability_and_status():
    outcome = OutcomeRecord(
        outcome_id="outcome-1",
        prediction_id="pred-1",
        target_time=at(11),
        observation_time=at(11, 2),
        availability_time=at(11, 5),
        actual_target=17.5,
        target_unit="km/h",
        status=OutcomeStatus.EVALUATED,
    )
    assert outcome.actual_target == 17.5

    with pytest.raises(ValidationError, match="require actual_target"):
        OutcomeRecord(
            outcome_id="outcome-2",
            prediction_id="pred-2",
            target_time=at(11),
            observation_time=at(11, 2),
            availability_time=at(11, 5),
            target_unit="km/h",
            status=OutcomeStatus.JOINED,
        )

    with pytest.raises(ValidationError, match="must not precede observation_time"):
        OutcomeRecord(
            outcome_id="outcome-3",
            prediction_id="pred-3",
            target_time=at(11),
            observation_time=at(11, 5),
            availability_time=at(11, 2),
            actual_target=17.5,
            target_unit="km/h",
            status=OutcomeStatus.EVALUATED,
        )


def test_temporal_schema_registry_exposes_contract_governance_metadata():
    assert set(TEMPORAL_SCHEMA_REGISTRY) == {
        "zonepilot.temporal_feature@1.0.0",
        "zonepilot.prediction@1.0.0",
        "zonepilot.outcome@1.0.0",
    }
    for registration in TEMPORAL_SCHEMA_REGISTRY.values():
        assert registration.compatibility_policy == "BACKWARD_COMPATIBLE_WITHIN_MAJOR"
        assert registration.required_fields
        assert registration.units
        assert registration.evidence_semantics
        assert registration.timestamp_semantics
