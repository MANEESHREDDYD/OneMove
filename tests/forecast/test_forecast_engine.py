"""Unit and Integration tests for R2 Forecast subsystem."""

from datetime import datetime, timedelta, timezone

from services.zonepilot.forecast.baselines import BaselineForecaster
from services.zonepilot.forecast.contracts import BaselineModelType, ForecastTarget
from services.zonepilot.forecast.evaluator import evaluate_chronological
from services.zonepilot.forecast.features import compute_feature_snapshot_hash, extract_point_in_time_features


def test_point_in_time_feature_filtering():
    base_time = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    observations = [
        {
            "observation_time": base_time - timedelta(hours=2),
            "information_available_at": base_time - timedelta(hours=2),
            "value": 10.0,
            "zone_id": "z1",
        },
        {
            "observation_time": base_time - timedelta(hours=1),
            "information_available_at": base_time - timedelta(hours=1),
            "value": 15.0,
            "zone_id": "z1",
        },
        # Future observation that leaked
        {
            "observation_time": base_time + timedelta(hours=1),
            "information_available_at": base_time + timedelta(hours=1),
            "value": 25.0,
            "zone_id": "z1",
        },
    ]

    valid = extract_point_in_time_features(observations, base_time)
    assert len(valid) == 2
    assert all(o["observation_time"] <= base_time for o in valid)

    snap_hash = compute_feature_snapshot_hash(valid)
    assert len(snap_hash) == 16


def test_baseline_models():
    base_time = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    history = [
        {"observation_time": base_time - timedelta(hours=i), "value": float(10 + i), "zone_id": "z1"}
        for i in reversed(range(1, 25))
    ]

    # Last observation
    pred_last = BaselineForecaster.predict(history, base_time, BaselineModelType.LAST_OBSERVATION)
    assert pred_last == 11.0

    # Rolling median
    pred_median = BaselineForecaster.predict(history, base_time, BaselineModelType.ROLLING_MEDIAN)
    assert pred_median > 0.0


def test_chronological_evaluation_no_leakage():
    split_time = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    # Every row states when it became knowable. The evaluator partitions on
    # information_available_at, not on event time (F-020), so a row without one
    # cannot be placed on the timeline and is excluded rather than assumed safe.
    observations = [
        {
            "observation_time": split_time - timedelta(hours=i),
            "information_available_at": split_time - timedelta(hours=i),
            "value": float(10 + (i % 5)),
        }
        for i in reversed(range(1, 48))
    ] + [
        {
            "observation_time": split_time + timedelta(hours=i),
            "information_available_at": split_time + timedelta(hours=i),
            "value": float(12 + (i % 3)),
        }
        for i in range(1, 24)
    ]

    res = evaluate_chronological(
        observations,
        split_time,
        ForecastTarget.WEATHER_TRAVEL_INFLATION_PERCENT,
        BaselineModelType.LAST_OBSERVATION,
    )
    assert res.sample_count == 23
    assert res.candidate_sample_count == 23
    assert res.excluded_record_count == 0
    assert res.mae >= 0.0
    assert res.rmse >= 0.0
    assert res.evaluation_status == "ENGINEERING_COMPLETE_EVIDENCE_ACCUMULATING"
