"""Chronological evaluation of forecasting models without temporal data leakage."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Sequence

from services.zonepilot.forecast.baselines import BaselineForecaster, usable_observation_value
from services.zonepilot.forecast.contracts import (
    EVIDENCE_ACCUMULATING_STATUS,
    NOT_EVALUATED_STATUS,
    BaselineModelType,
    ForecastEvaluationResult,
    ForecastTarget,
)
from services.zonepilot.forecast.timeline import coerce_utc

AVAILABILITY_KEY = "information_available_at"
EVENT_TIME_KEY = "observation_time"


def _availability_time(observation: Any) -> datetime | None:
    """When this record BECAME KNOWABLE. There is no fallback to event time.

    Falling back to ``observation_time`` would reinstate exactly the leak this
    guards against: a fact that occurred before the cutoff but only became
    available after it would be treated as training data (F-020).
    """
    if not isinstance(observation, dict):
        return None
    return coerce_utc(observation.get(AVAILABILITY_KEY))


def _event_time(observation: Any) -> datetime | None:
    if not isinstance(observation, dict):
        return None
    return coerce_utc(observation.get(EVENT_TIME_KEY))


def evaluate_chronological(
    observations: Sequence[dict[str, Any]],
    split_cutoff: datetime,
    target: ForecastTarget,
    model_type: BaselineModelType,
    *,
    horizon: timedelta | None = None,
) -> ForecastEvaluationResult:
    """Score a baseline chronologically, using only information available at issue time.

    F-020: the split and the per-sample history were both taken on
    ``observation_time`` -- EVENT time. A prediction issued at time T may only be
    trained on records satisfying ``information_available_at <= T``, so both the
    partitioning and the per-prediction history are now derived from availability
    time. Records with no usable availability timestamp cannot be placed on the
    timeline and are excluded from both partitions, and reported as excluded
    rather than silently dropped.

    ``horizon`` selects the evaluation origin. When it is None every prediction is
    issued at ``split_cutoff`` (single-origin). When it is given, the prediction
    for a target at time t is issued at ``t - horizon`` and its history is
    re-derived at that issue time (expanding-window walk-forward).

    F-018: ``sample_count`` is the number of samples ACTUALLY SCORED. When that is
    zero, mae/rmse/coverage_rate are None -- never 0.0, which claimed a perfect
    model over measurements that were never taken.
    """
    if horizon is not None and horizon <= timedelta(0):
        raise ValueError("horizon must be positive when supplied")

    cutoff = coerce_utc(split_cutoff)
    if cutoff is None:
        raise ValueError("split_cutoff must be a datetime")

    placeable: list[tuple[datetime, datetime, dict[str, Any]]] = []
    excluded_record_count = 0
    for observation in observations:
        available_at = _availability_time(observation)
        event_time = _event_time(observation)
        if available_at is None or event_time is None:
            # Not placeable on the availability timeline; it can be proven
            # neither safe for training nor eligible for scoring.
            excluded_record_count += 1
            continue
        placeable.append((available_at, event_time, observation))

    placeable.sort(key=lambda entry: (entry[1], entry[0]))
    candidates = [entry for entry in placeable if entry[0] > cutoff]

    errors: list[float] = []
    squared_errors: list[float] = []
    for _issued_available_at, event_time, observation in candidates:
        issue_time = event_time - horizon if horizon is not None else cutoff
        history = [
            entry[2]
            for entry in placeable
            # Available at issue time, and strictly before the target it predicts,
            # so a sample can never be part of its own history.
            if entry[0] <= issue_time and entry[1] < event_time
        ]
        predicted = BaselineForecaster.predict(history, event_time, model_type)
        actual = usable_observation_value(observation)
        if predicted is None or actual is None:
            # Unscoreable: no history to predict from, or no usable observation to
            # compare against. Skipped, and counted as skipped -- not as a hit.
            continue
        error = abs(actual - predicted)
        if not math.isfinite(error):
            continue
        errors.append(error)
        squared_errors.append(error**2)

    scored = len(errors)
    candidate_count = len(candidates)
    if scored == 0:
        return ForecastEvaluationResult(
            target=target,
            model=model_type,
            sample_count=0,
            candidate_sample_count=candidate_count,
            unscored_sample_count=candidate_count,
            excluded_record_count=excluded_record_count,
            # Nothing was measured. Reporting 0.0 here asserted a perfect model.
            mae=None,
            rmse=None,
            # Not measured: prediction intervals are not produced, so interval
            # coverage cannot be computed. 1.0 asserted perfect calibration (F-018).
            coverage_rate=None,
            chronological_split_cutoff=cutoff,
            evaluation_status=NOT_EVALUATED_STATUS,
        )

    return ForecastEvaluationResult(
        target=target,
        model=model_type,
        sample_count=scored,
        candidate_sample_count=candidate_count,
        unscored_sample_count=candidate_count - scored,
        excluded_record_count=excluded_record_count,
        mae=round(sum(errors) / scored, 4),
        rmse=round(math.sqrt(sum(squared_errors) / scored), 4),
        # Not measured; see above.
        coverage_rate=None,
        chronological_split_cutoff=cutoff,
        evaluation_status=EVIDENCE_ACCUMULATING_STATUS,
    )
