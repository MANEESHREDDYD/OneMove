"""Deterministic baseline models for observable network/weather targets."""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any, Sequence

from services.zonepilot.forecast.contracts import BaselineModelType


class BaselineForecaster:
    @staticmethod
    def predict(
        history: Sequence[dict[str, Any]],
        target_time: datetime,
        model_type: BaselineModelType = BaselineModelType.LAST_OBSERVATION,
    ) -> float | None:
        """Return a baseline prediction, or None when there is no history.

        This returned 0.0 on empty history (F-018). Zero is a measurement, and an
        operator cannot distinguish "we predict zero" from "we have no data".
        None forces the caller to surface UNAVAILABLE.
        """
        if not history:
            return None

        if model_type == BaselineModelType.LAST_OBSERVATION:
            return float(history[-1]["value"])

        if model_type == BaselineModelType.ROLLING_MEDIAN:
            vals = [float(h["value"]) for h in history[-24:]]
            return float(statistics.median(vals)) if vals else 0.0

        if model_type == BaselineModelType.PRIOR_DAY_SAME_HOUR:
            target_hour = target_time.hour
            prior_day_matches = [
                float(h["value"])
                for h in history
                if hasattr(h["observation_time"], "hour") and h["observation_time"].hour == target_hour
            ]
            return float(prior_day_matches[-1]) if prior_day_matches else float(history[-1]["value"])

        if model_type == BaselineModelType.PRIOR_WEEK_SAME_HOUR:
            target_weekday = target_time.weekday()
            target_hour = target_time.hour
            prior_week_matches = [
                float(h["value"])
                for h in history
                if hasattr(h["observation_time"], "weekday")
                and h["observation_time"].weekday() == target_weekday
                and h["observation_time"].hour == target_hour
            ]
            return float(prior_week_matches[-1]) if prior_week_matches else float(history[-1]["value"])

        return float(history[-1]["value"])
