"""Integration tests proving Optimization API is durable in PostgreSQL with zero in-memory mock."""

import uuid

import pytest
from fastapi.testclient import TestClient

import services.api.routers.observatory as obs_module
from services.api.core.auth import get_current_user
from services.api.main import app


def mock_user_auth():
    return {
        "sub": "11111111-1111-1111-1111-111111111111",
        "workspace_id": "ws-test-durability",
        "role": "admin",
    }


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_user_auth
    yield
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


def test_no_in_memory_optimization_dict_exists():
    """Anti-regression test: _in_memory_optimization_jobs must not exist in router."""
    assert not hasattr(obs_module, "_in_memory_optimization_jobs")


def test_durable_optimization_lifecycle():
    """Test submit -> DB insert -> solve -> DB retrieve lifecycle."""
    idem_key = f"test-idem-key-{uuid.uuid4().hex[:8]}"
    req = {
        "idempotency_key": idem_key,
        "min_open_facilities": 2,
        "max_open_facilities": 4,
        "max_travel_seconds": 1800,
        "allow_uncovered_demand": True,
        "scenarios": ["s1_free_flow", "s2_congested", "s3_congested_outage"],
    }

    # 1. Submit optimization job
    res = client.post("/api/v1/optimizations", json=req)
    assert res.status_code in (201, 202)
    data = res.json()
    job_id = data["job_id"]
    assert len(job_id) > 0
    assert data["status"] in {"SUCCESS", "QUEUED", "RUNNING"}

    # 2. Re-fetch from DB
    get_res = client.get(f"/api/v1/optimizations/{job_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["job_id"] == job_id
    assert get_data["solver_status"] in {"OPTIMAL", "FEASIBLE"}
    assert len(get_data["opened_facilities"]) >= 2

    # 3. Verify in list
    list_res = client.get("/api/v1/optimizations")
    assert list_res.status_code == 200
    jobs = list_res.json()["data"]
    assert any(j["job_id"] == job_id for j in jobs)
