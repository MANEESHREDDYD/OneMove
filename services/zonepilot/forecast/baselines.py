"""Deterministic baseline models for observable network/weather targets."""

from __future__ import annotations

import math
import statistics
from datetime import datetime
from typing import Any, Sequence

from services.zonepilot.forecast.contracts import BaselineModelType


def usable_observation_value(observation: Any) -> float | None:
    """Return the observation's value, or None when there is no usable measurement.

    A genuine 0.0 is a measurement and must survive this function unchanged; only
    absent, non-numeric or non-finite values collapse to None. Truthiness checks
    are deliberately avoided here -- ``if value:`` would erase a real zero.
    """
    if not isinstance(observation, dict):
        return None
    value = observation.get("value")
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _usable_values(history: Sequence[dict[str, Any]]) -> list[float]:
    values = [usable_observation_value(item) for item in history]
    return [value for value in values if value is not None]


def _last_usable_value(history: Sequence[dict[str, Any]]) -> float | None:
    for item in reversed(history):
        value = usable_observation_value(item)
        if value is not None:
            return value
    return None


def _last_matching_value(
    history: Sequence[dict[str, Any]],
    predicate: Any,
) -> float | None:
    for item in reversed(history):
        observation_time = item.get("observation_time") if isinstance(item, dict) else None
        if observation_time is None or not hasattr(observation_time, "hour"):
            continue
        if not predicate(observation_time):
            continue
        value = usable_observation_value(item)
        if value is not None:
            return value
    return None


class BaselineForecaster:
    @staticmethod
    def predict(
        history: Sequence[dict[str, Any]],
        target_time: datetime,
        model_type: BaselineModelType = BaselineModelType.LAST_OBSERVATION,
    ) -> float | None:
        """Return a baseline prediction, or None when there is no usable history.

        This returned 0.0 on empty history, and ROLLING_MEDIAN still returned 0.0
        when it had no values to take a median of (F-018). Zero is a measurement,
        and an operator cannot distinguish "we predict zero" from "we have no
        data". Every unavailable path now returns None, which forces the caller to
        surface UNAVAILABLE.
        """
        if not history:
            return None

        if model_type == BaselineModelType.ROLLING_MEDIAN:
            values = _usable_values(history[-24:])
            return float(statistics.median(values)) if values else None

        if model_type == BaselineModelType.PRIOR_DAY_SAME_HOUR:
            target_hour = target_time.hour
            match = _last_matching_value(history, lambda ts: ts.hour == target_hour)
            return match if match is not None else _last_usable_value(history)

        if model_type == BaselineModelType.PRIOR_WEEK_SAME_HOUR:
            target_weekday = target_time.weekday()
            target_hour = target_time.hour
            match = _last_matching_value(
                history,
                lambda ts: hasattr(ts, "weekday") and ts.weekday() == target_weekday and ts.hour == target_hour,
            )
            return match if match is not None else _last_usable_value(history)

        # LAST_OBSERVATION, and the default for any future model type that has no
        # implementation yet: never invent a number for an unhandled model.
        return _last_usable_value(history)
