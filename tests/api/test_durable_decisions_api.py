"""Integration tests for durable Decision Ledger, Replay, and Shadows."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from services.api.core.auth import get_current_user
from services.api.main import app


def mock_user_auth():
    return {
        "sub": "33333333-3333-3333-3333-333333333333",
        "workspace_id": "ws-test-decisions",
        "role": "admin",
    }


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_user_auth
    yield
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


def test_durable_decision_record_replay_shadow():
    now = datetime.now(timezone.utc)
    rec_payload = {
        "decision_time": now.isoformat(),
        "network_version": "1.1",
        "dataset_version": "1.0.0",
        "feature_snapshot_hash": "snap-test-1234",
        "selected_action": "OPEN_FACILITIES",
        "opened_facilities": ["fac:88618925a5fffff", "fac:88618925a7fffff", "fac:8861892ec3fffff", "fac:8861892ecbfffff"],
        "objective_value": 1756300000000,
        "expected_travel_seconds": 620,
        "p95_travel_seconds": 780,
        "coverage_basis_points": 9910,
        "code_sha": "git-sha-test-456",
    }

    # 1. POST /api/v1/decisions
    res = client.post("/api/v1/decisions", json=rec_payload)
    assert res.status_code == 201
    dec = res.json()
    dec_id = dec["decision_id"]
    assert dec_id.startswith("dec-")

    # 2. GET /api/v1/decisions/{id}
    get_res = client.get(f"/api/v1/decisions/{dec_id}")
    assert get_res.status_code == 200
    assert get_res.json()["decision_id"] == dec_id

    # 3. POST /api/v1/decisions/{id}/replay
    replay_payload = {
        "feature_cutoff": now.isoformat(),
    }
    rep_res = client.post(f"/api/v1/decisions/{dec_id}/replay", json=replay_payload)
    assert rep_res.status_code == 200
    replay_data = rep_res.json()
    assert replay_data["pit_valid"] is True
    assert replay_data["reproduced_exact_action"] is True
    assert replay_data["reproduced_exact_facilities"] is True
    assert replay_data["objective_match"] is True
    assert replay_data["match_status"] == "EXACT_MATCH"

    # 4. POST /api/v1/decisions/{id}/shadows
    future_time = datetime.fromtimestamp(now.timestamp() + 7200, tz=timezone.utc)
    shadow_payload = {
        "future_observation_time": future_time.isoformat(),
        "frozen_decision_time": now.isoformat(),
        "predicted_p95_seconds": 780,
    }
    shad_res = client.post(f"/api/v1/decisions/{dec_id}/shadows", json=shadow_payload)
    assert shad_res.status_code == 201
    shad_data = shad_res.json()
    assert shad_data["shadow_state"] == "FROZEN_AWAITING_FUTURE"
