"""F-018 (reopened): "no samples" must never be reported as "perfect model".

The evaluator set mae=rmse=0.0 whenever nothing was scored, while sample_count
was ``len(test)`` -- every CANDIDATE row, including the ones the walk-forward
skipped. A reader saw a non-zero sample count with zero error: a perfect-accuracy
claim over measurements that were never taken.

The invariant asserted here is:
    sample_count == samples ACTUALLY SCORED, and
    sample_count == 0  =>  mae is rmse is coverage_rate is None.

The subtle case each test below is built around: a genuine OBSERVED 0.0 is a
measurement and must stay distinguishable from UNAVAILABLE.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone

import pytest

from services.zonepilot.forecast import baselines as baselines_module
from services.zonepilot.forecast.baselines import BaselineForecaster
from services.zonepilot.forecast.contracts import (
    NOT_EVALUATED_STATUS,
    BaselineModelType,
    ForecastEvaluationResult,
    ForecastTarget,
)
from services.zonepilot.forecast.evaluator import evaluate_chronological

CUTOFF = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
TARGET = ForecastTarget.WEATHER_TRAVEL_INFLATION_PERCENT
MODEL = BaselineModelType.LAST_OBSERVATION


def _obs(offset_hours: float, value: float | None, *, available_offset_hours: float | None = None) -> dict:
    """One observation, with event time and availability time stated separately."""
    event_time = CUTOFF + timedelta(hours=offset_hours)
    available_at = CUTOFF + timedelta(hours=offset_hours if available_offset_hours is None else available_offset_hours)
    return {
        "zone_id": "8860145b59fffff",
        "observation_time": event_time,
        "information_available_at": available_at,
        "value": value,
    }


def _evaluate(observations, model: BaselineModelType = MODEL) -> ForecastEvaluationResult:
    return evaluate_chronological(observations, CUTOFF, TARGET, model)


def _assert_reports_nothing_measured(result: ForecastEvaluationResult) -> None:
    assert result.sample_count == 0
    assert result.mae is None, "zero error over zero measurements is a perfect-accuracy claim"
    assert result.rmse is None
    assert result.coverage_rate is None
    assert result.evaluation_status == NOT_EVALUATED_STATUS


# --- zero history ----------------------------------------------------------


def test_zero_historical_rows_measures_nothing() -> None:
    """Test rows with no history to predict from cannot be scored at all."""
    result = _evaluate([_obs(1, 10.0), _obs(2, 11.0)])

    _assert_reports_nothing_measured(result)
    # The candidates are still reported -- they are just not counted as hits.
    assert result.candidate_sample_count == 2
    assert result.unscored_sample_count == 2


def test_completely_empty_input_measures_nothing() -> None:
    result = _evaluate([])

    _assert_reports_nothing_measured(result)
    assert result.candidate_sample_count == 0
    assert result.unscored_sample_count == 0


# --- exactly one historical row -------------------------------------------


def test_exactly_one_historical_row_scores_exactly_one_sample() -> None:
    """The smallest history that can produce a prediction produces exactly one."""
    result = _evaluate([_obs(-1, 10.0), _obs(1, 13.0)])

    assert result.sample_count == 1
    assert result.candidate_sample_count == 1
    assert result.unscored_sample_count == 0
    assert result.mae == 3.0
    assert result.rmse == 3.0


def test_one_historical_row_and_no_test_rows_measures_nothing() -> None:
    result = _evaluate([_obs(-1, 10.0)])

    _assert_reports_nothing_measured(result)
    assert result.candidate_sample_count == 0


# --- candidates present, none scoreable -----------------------------------


def test_candidates_present_but_none_scoreable_reports_zero_samples() -> None:
    """sample_count counted len(test); three unscoreable rows read as three hits."""
    observations = [_obs(-1, 10.0)] + [_obs(i, None) for i in (1, 2, 3)]

    result = _evaluate(observations)

    _assert_reports_nothing_measured(result)
    assert result.candidate_sample_count == 3
    assert result.unscored_sample_count == 3


def test_history_without_usable_values_scores_nothing() -> None:
    """History exists but holds no measurement, so no prediction can be made."""
    result = _evaluate([_obs(-2, None), _obs(-1, None), _obs(1, 10.0)])

    _assert_reports_nothing_measured(result)
    assert result.candidate_sample_count == 1


# --- mixed scoreable / unscoreable ----------------------------------------


def test_mixed_candidates_score_only_the_scoreable_ones() -> None:
    observations = [
        _obs(-1, 10.0),
        _obs(1, None),  # unscoreable: no usable observation to compare against
        _obs(2, 14.0),  # scoreable: |14 - 10| = 4
        _obs(3, None),  # unscoreable
    ]

    result = _evaluate(observations)

    assert result.candidate_sample_count == 3
    assert result.sample_count == 1, "skipped candidates must not inflate the sample count"
    assert result.unscored_sample_count == 2
    # The error is the mean over SCORED samples only; averaging over candidates
    # would report 4/3 and flatter the model.
    assert result.mae == 4.0
    assert result.rmse == 4.0


def test_non_finite_and_non_numeric_observations_are_not_scored() -> None:
    observations = [
        _obs(-1, 10.0),
        _obs(1, float("nan")),
        _obs(2, float("inf")),
        {**_obs(3, 0.0), "value": "not-a-number"},
        _obs(4, 12.0),
    ]

    result = _evaluate(observations)

    assert result.candidate_sample_count == 4
    assert result.sample_count == 1
    assert result.mae == 2.0


# --- a real zero is a measurement -----------------------------------------


def test_observed_zero_is_scored_normally() -> None:
    """The subtle case: an OBSERVED 0.0 must not be mistaken for missing data."""
    result = _evaluate([_obs(-1, 0.0), _obs(1, 0.0)])

    assert result.sample_count == 1, "a genuine zero observation must be scored"
    assert result.mae == 0.0
    assert result.rmse == 0.0
    assert result.candidate_sample_count == 1
    assert result.unscored_sample_count == 0


def test_observed_zero_and_no_samples_are_distinguishable() -> None:
    """Both report 0/None-shaped numbers; only one of them measured anything."""
    measured_zero = _evaluate([_obs(-1, 0.0), _obs(1, 0.0)])
    measured_nothing = _evaluate([_obs(1, 0.0)])

    assert (measured_zero.sample_count, measured_zero.mae) == (1, 0.0)
    assert (measured_nothing.sample_count, measured_nothing.mae) == (0, None)
    assert measured_zero.evaluation_status != measured_nothing.evaluation_status


def test_zero_error_against_a_zero_prediction_is_a_real_score() -> None:
    """A zero-valued history predicts zero; that is a prediction, not an absence."""
    assert BaselineForecaster.predict([_obs(-1, 0.0)], CUTOFF, MODEL) == 0.0
    assert BaselineForecaster.predict([], CUTOFF, MODEL) is None


# --- baselines: no fabricated zero on any unavailable path ------------------


def test_rolling_median_without_usable_values_returns_none() -> None:
    """baselines.py kept an `else 0.0` branch for the unavailable state."""
    history = [_obs(-3, None), _obs(-2, None)]

    assert BaselineForecaster.predict(history, CUTOFF, BaselineModelType.ROLLING_MEDIAN) is None


def test_rolling_median_of_genuine_zeroes_is_zero() -> None:
    history = [_obs(-3, 0.0), _obs(-2, 0.0)]

    assert BaselineForecaster.predict(history, CUTOFF, BaselineModelType.ROLLING_MEDIAN) == 0.0


@pytest.mark.parametrize("model", list(BaselineModelType))
def test_no_baseline_model_fabricates_a_value_without_history(model: BaselineModelType) -> None:
    assert BaselineForecaster.predict([], CUTOFF, model) is None
    assert BaselineForecaster.predict([_obs(-1, None)], CUTOFF, model) is None


def test_no_zero_fallback_remains_in_the_baseline_source() -> None:
    """Regression guard: `else 0.0` is how the unavailable state got a value."""
    source = inspect.getsource(baselines_module)

    assert "else 0.0" not in source
    assert "or 0.0" not in source


# --- the contract itself forbids the claim ---------------------------------


def test_contract_rejects_zero_samples_with_a_reported_error() -> None:
    """Make the false claim unrepresentable, not merely un-emitted."""
    with pytest.raises(ValueError) as exc:
        ForecastEvaluationResult(
            target=TARGET,
            model=MODEL,
            sample_count=0,
            mae=0.0,
            rmse=0.0,
            chronological_split_cutoff=CUTOFF,
        )

    assert "no samples were scored" in str(exc.value)


def test_contract_rejects_scored_samples_without_metrics() -> None:
    with pytest.raises(ValueError):
        ForecastEvaluationResult(
            target=TARGET,
            model=MODEL,
            sample_count=2,
            candidate_sample_count=2,
            mae=None,
            rmse=None,
            chronological_split_cutoff=CUTOFF,
        )


def test_contract_rejects_a_sample_count_above_the_candidates() -> None:
    """sample_count was len(test); it can never exceed the candidates considered."""
    with pytest.raises(ValueError):
        ForecastEvaluationResult(
            target=TARGET,
            model=MODEL,
            sample_count=5,
            candidate_sample_count=3,
            unscored_sample_count=0,
            mae=1.0,
            rmse=1.0,
            chronological_split_cutoff=CUTOFF,
        )
