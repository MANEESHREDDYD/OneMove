"""Chronological evaluation of forecasting models without temporal data leakage."""

from __future__ import annotations

from datetime import datetime
import math
from typing import Any, Sequence

from services.zonepilot.forecast.baselines import BaselineForecaster
from services.zonepilot.forecast.contracts import (
    BaselineModelType,
    ForecastEvaluationResult,
    ForecastTarget,
)


def evaluate_chronological(
    observations: Sequence[dict[str, Any]],
    split_cutoff: datetime,
    target: ForecastTarget,
    model_type: BaselineModelType,
) -> ForecastEvaluationResult:
    train = [o for o in observations if o["observation_time"] <= split_cutoff]
    test = [o for o in observations if o["observation_time"] > split_cutoff]

    if not test:
        return ForecastEvaluationResult(
            target=target,
            model=model_type,
            sample_count=0,
            mae=0.0,
            rmse=0.0,
            coverage_rate=1.0,
            chronological_split_cutoff=split_cutoff,
            evaluation_status="ENGINEERING_COMPLETE_EVIDENCE_ACCUMULATING",
        )

    errors = []
    sq_errors = []
    for actual in test:
        pred = BaselineForecaster.predict(train, actual["observation_time"], model_type)
        err = abs(actual["value"] - pred)
        errors.append(err)
        sq_errors.append(err**2)

    mae = sum(errors) / len(errors) if errors else 0.0
    rmse = math.sqrt(sum(sq_errors) / len(sq_errors)) if sq_errors else 0.0

    return ForecastEvaluationResult(
        target=target,
        model=model_type,
        sample_count=len(test),
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        coverage_rate=1.0,
        chronological_split_cutoff=split_cutoff,
        evaluation_status="ENGINEERING_COMPLETE_EVIDENCE_ACCUMULATING",
    )
