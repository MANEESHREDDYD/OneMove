"""Integration tests for R4 Resilience Scenario API and PostgreSQL durability."""

import pytest
from fastapi.testclient import TestClient
from services.api.main import app
from services.api.core.auth import get_current_user


def mock_user_auth():
    return {
        "sub": "22222222-2222-2222-2222-222222222222",
        "workspace_id": "ws-test-resilience",
        "role": "admin",
    }


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_user_auth
    yield
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


def test_create_and_query_resilience_scenario():
    req = {
        "scenario_type": "CONGESTION_SPIKE",
        "description": "Peak evening rush hour spike",
        "parameters": {"congestion_multiplier": 1.5},
        "seed": 42,
    }

    # 1. POST /api/v1/scenarios -> creates and evaluates
    res = client.post("/api/v1/scenarios", json=req)
    assert res.status_code == 201
    data = res.json()
    scenario_id = data["scenario_id"]
    assert scenario_id.startswith("scen-")
    assert data["scenario_type"] == "CONGESTION_SPIKE"
    assert data["coverage_basis_points"] > 0
    assert data["p95_duration_seconds"] > 0
    assert data["degradation_grade"] in {"ROBUST", "MODERATE_DEGRADATION", "SEVERE_DEGRADATION", "CRITICAL_FAILURE"}

    # 2. GET /api/v1/scenarios/{id}
    get_res = client.get(f"/api/v1/scenarios/{scenario_id}")
    assert get_res.status_code == 200
    assert get_res.json()["scenario_id"] == scenario_id

    # 3. GET /api/v1/scenarios -> list
    list_res = client.get("/api/v1/scenarios")
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1
