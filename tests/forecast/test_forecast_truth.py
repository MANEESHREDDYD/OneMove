"""F-018: no fabricated forecast provenance, no fabricated measurements.

The forecast endpoint persisted predicted_value=None -- honest -- while also
asserting a model_version, a dataset_version, a graph_version, an evidence id and
a feature_snapshot_hash computed as sha256(zone_id): a hash of the request, not of
any feature snapshot. Separately the baseline returned 0.0 on empty history, and
the evaluator hardcoded coverage_rate=1.0 while never producing intervals.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services.zonepilot.forecast.baselines import BaselineForecaster
from services.zonepilot.forecast.contracts import (
    BaselineModelType,
    ForecastTarget,
    PredictionRecord,
)

NOW = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)


def _record(**over):
    base = dict(
        prediction_id="pred-test",
        workspace_id="ws-test",
        zone_id="8860145b59fffff",
        prediction_time=NOW,
        target_time=NOW,
        horizon_hours=1,
        target=ForecastTarget.WEATHER_TRAVEL_INFLATION_PERCENT,
        baseline_model=BaselineModelType.LAST_OBSERVATION,
    )
    base.update(over)
    return PredictionRecord(**base)


def test_empty_history_yields_no_prediction_not_zero() -> None:
    """0.0 is a measurement; absence of data is not."""
    assert BaselineForecaster.predict([], NOW, BaselineModelType.LAST_OBSERVATION) is None


def test_record_without_a_prediction_claims_no_provenance() -> None:
    rec = _record()
    assert rec.predicted_value is None
    assert rec.model_version is None
    assert rec.feature_snapshot_hash is None
    assert rec.dataset_version is None
    assert rec.graph_version is None
    assert rec.evidence_ids == ()


def test_record_with_a_prediction_requires_provenance() -> None:
    """A real number must carry real lineage."""
    with pytest.raises(ValueError) as exc:
        _record(predicted_value=12.5)
    message = str(exc.value)
    for field in ("model_version", "feature_snapshot_hash", "dataset_version", "graph_version"):
        assert field in message


def test_fully_provenanced_prediction_is_accepted() -> None:
    """Control: the validator must not reject legitimate records."""
    rec = _record(
        predicted_value=12.5,
        model_version="baseline-last-observation-1.0.0",
        feature_snapshot_hash="a" * 64,
        dataset_version="1.0.0",
        graph_version="1.1",
    )
    assert rec.predicted_value == 12.5


def test_snapshot_hash_is_not_derived_from_the_request() -> None:
    """sha256(zone_id) is a hash of the request, not of a feature snapshot."""
    import hashlib
    import inspect

    from services.api.routers import observatory

    src = inspect.getsource(observatory.predict_forecast)
    forged = hashlib.sha256(b"8860145b59fffff").hexdigest()[:8]
    assert forged not in src
    assert "sha256(payload.zone_id" not in src.replace(" ", "")
