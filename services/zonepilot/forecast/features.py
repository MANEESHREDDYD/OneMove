"""Feature extraction for R2 forecasting with strict Point-In-Time causality."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Sequence


def extract_point_in_time_features(
    observations: Sequence[dict[str, Any]],
    prediction_time: datetime,
) -> list[dict[str, Any]]:
    """Filter and sort observations strictly satisfying information_available_at <= prediction_time."""
    valid = []
    for obs in observations:
        avail_at = obs.get("information_available_at")
        if isinstance(avail_at, str):
            avail_at = datetime.fromisoformat(avail_at)
        if avail_at and avail_at <= prediction_time:
            valid.append(obs)

    return sorted(valid, key=lambda x: x["observation_time"])


def compute_feature_snapshot_hash(features: Sequence[dict[str, Any]]) -> str:
    """Compute deterministic hash of valid features."""
    serialized = "".join(f"{f.get('zone_id')}:{f.get('observation_time')}:{f.get('value')}" for f in features)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
