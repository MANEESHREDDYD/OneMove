"""F-020 (reopened), path (a): the evaluator split and predicted on EVENT time.

``evaluate_chronological`` partitioned on ``observation_time`` and rebuilt each
prediction's history from the same field. A record describing something that
happened before the cutoff but only became available afterwards therefore landed
in training: future information, scoring the model against knowledge it could not
have had.

A prediction issued at time T may only be trained on records satisfying
``information_available_at <= T``. The arithmetic in these tests is chosen so the
leaking and non-leaking behaviours produce DIFFERENT numbers.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.zonepilot.forecast.contracts import BaselineModelType, ForecastTarget
from services.zonepilot.forecast.evaluator import evaluate_chronological

TODAY = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
TARGET = ForecastTarget.WEATHER_TRAVEL_INFLATION_PERCENT
MODEL = BaselineModelType.LAST_OBSERVATION


def _record(event_time: datetime, available_at: datetime, value: float | None) -> dict:
    return {
        "zone_id": "8860145b59fffff",
        "observation_time": event_time,
        "information_available_at": available_at,
        "value": value,
    }


def _evaluate(observations, **kwargs):
    return evaluate_chronological(observations, TODAY, TARGET, MODEL, **kwargs)


def test_late_arriving_record_does_not_train_the_model() -> None:
    """Occurred yesterday, available tomorrow, decision today -> EXCLUDED from history.

    On an event-time split the late record is the most recent training row, so
    LAST_OBSERVATION predicts 999.0 for the scored candidate and its error is 989.
    On an availability split the history ends at 10.0 and the error is 0.
    """
    scored_candidate = _record(TODAY + timedelta(hours=1), TODAY + timedelta(hours=1), 10.0)
    observations = [
        _record(YESTERDAY, YESTERDAY, 10.0),
        # Event time is before the cutoff; availability is after it.
        _record(TODAY - timedelta(hours=1), TOMORROW, 999.0),
        scored_candidate,
    ]

    result = _evaluate(observations)

    # Both post-cutoff-availability rows are candidates; neither is training data.
    assert result.candidate_sample_count == 2
    assert result.sample_count == 2
    # 989 for the late record itself, 0 for the clean candidate. An event-time
    # split leaks 999.0 into history and yields mae == 989.0 instead.
    assert result.mae == pytest.approx(494.5)


def test_a_record_available_after_the_cutoff_is_a_candidate_not_training_data() -> None:
    late = _record(TODAY - timedelta(hours=2), TODAY + timedelta(hours=2), 42.0)

    result = _evaluate([late])

    # No history is available at the cutoff, so it cannot be scored -- and it is
    # certainly not training data for itself.
    assert result.candidate_sample_count == 1
    assert result.sample_count == 0
    assert result.mae is None


def test_a_sample_is_never_part_of_its_own_history() -> None:
    """One post-cutoff row alone must score nothing, not zero error against itself."""
    result = _evaluate([_record(TOMORROW, TOMORROW, 7.0)])

    assert result.sample_count == 0
    assert result.mae is None


def test_records_without_an_availability_time_are_excluded_and_reported() -> None:
    """No availability time means the record cannot be placed on the timeline.

    Falling back to event time is exactly the leak; dropping it silently is what
    let unscoreable rows disappear. It is excluded AND counted.
    """
    observations = [
        {"zone_id": "z", "observation_time": YESTERDAY, "value": 10.0},
        _record(YESTERDAY, YESTERDAY, 11.0),
        _record(TODAY + timedelta(hours=1), TODAY + timedelta(hours=1), 11.0),
    ]

    result = _evaluate(observations)

    assert result.excluded_record_count == 1
    assert result.sample_count == 1
    # The undated row never reached history: the prediction is 11.0, not 10.0.
    assert result.mae == 0.0


def test_unparseable_availability_time_is_excluded_not_guessed() -> None:
    observations = [
        {
            "zone_id": "z",
            "observation_time": YESTERDAY,
            "information_available_at": "not-a-timestamp",
            "value": 10.0,
        },
        _record(TODAY + timedelta(hours=1), TODAY + timedelta(hours=1), 10.0),
    ]

    result = _evaluate(observations)

    assert result.excluded_record_count == 1
    assert result.sample_count == 0


def test_iso_string_timestamps_are_honoured() -> None:
    """Rows arriving from JSON must not be silently dropped as unplaceable."""
    observations = [
        {
            "zone_id": "z",
            "observation_time": YESTERDAY.isoformat(),
            "information_available_at": YESTERDAY.isoformat(),
            "value": 10.0,
        },
        {
            "zone_id": "z",
            "observation_time": (TODAY + timedelta(hours=1)).isoformat(),
            "information_available_at": (TODAY + timedelta(hours=1)).isoformat(),
            "value": 12.0,
        },
    ]

    result = _evaluate(observations)

    assert result.excluded_record_count == 0
    assert result.sample_count == 1
    assert result.mae == 2.0


def test_walk_forward_history_is_bounded_by_each_prediction_issue_time() -> None:
    """With a horizon, history is re-derived at target_time - horizon.

    The 500.0 record becomes available one minute AFTER the second prediction is
    issued, so it may inform the third prediction and no earlier one.
    """
    horizon = timedelta(hours=1)
    observations = [
        _record(TODAY - timedelta(hours=1), TODAY - timedelta(hours=1), 10.0),
        _record(TODAY + timedelta(hours=1), TODAY + timedelta(hours=1), 10.0),
        _record(
            TODAY + timedelta(hours=2),
            # Issued for the second candidate at TODAY+1h; this arrives after that.
            TODAY + timedelta(hours=1, minutes=1),
            500.0,
        ),
        _record(TODAY + timedelta(hours=3), TODAY + timedelta(hours=3), 500.0),
    ]

    result = _evaluate(observations, horizon=horizon)

    assert result.candidate_sample_count == 3
    assert result.sample_count == 3
    # |10-10| = 0, |500-10| = 490, |500-500| = 0  ->  mean 163.3333
    assert result.mae == pytest.approx(163.3333, abs=1e-4)


def test_a_non_positive_horizon_is_rejected() -> None:
    with pytest.raises(ValueError):
        _evaluate([], horizon=timedelta(0))
    with pytest.raises(ValueError):
        _evaluate([], horizon=timedelta(hours=-1))


def test_naive_timestamps_are_read_as_utc_rather_than_crashing() -> None:
    """A mixed-awareness dataset must not raise mid-comparison."""
    naive_history = {
        "zone_id": "z",
        "observation_time": YESTERDAY.replace(tzinfo=None),
        "information_available_at": YESTERDAY.replace(tzinfo=None),
        "value": 10.0,
    }
    aware_candidate = _record(TODAY + timedelta(hours=1), TODAY + timedelta(hours=1), 14.0)

    result = _evaluate([naive_history, aware_candidate])

    assert result.sample_count == 1
    assert result.mae == 4.0
