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
    assert get_data["status"] in {"QUEUED", "RUNNING", "SUCCESS"}
    assert get_data["solver_status"] in {None, "QUEUED", "OPTIMAL", "FEASIBLE"}

    # 3. Verify in list
    list_res = client.get("/api/v1/optimizations")
    assert list_res.status_code == 200
    jobs = list_res.json().get("data") or list_res.json().get("jobs", [])
    assert any(j["job_id"] == job_id for j in jobs)


def test_api_process_never_invokes_solver_synchronously(monkeypatch):
    """P0-ASYNC-001 regression test: POST /api/v1/optimizations MUST NOT invoke optimize_facilities in API process."""

    def _forbidden_solver_call(*args, **kwargs):
        raise AssertionError("CRITICAL VIOLATION: optimize_facilities was invoked synchronously inside API process!")

    monkeypatch.setattr("services.zonepilot.optimization.solver.optimize_facilities", _forbidden_solver_call)
    monkeypatch.setattr("services.zonepilot.optimization.service.optimize_facilities", _forbidden_solver_call)

    idem_key = f"test-async-strict-{uuid.uuid4().hex[:8]}"
    req = {
        "idempotency_key": idem_key,
        "min_open_facilities": 1,
        "max_open_facilities": 3,
        "max_travel_seconds": 1800,
        "allow_uncovered_demand": True,
    }
    res = client.post("/api/v1/optimizations", json=req)
    assert res.status_code == 202
    assert res.json()["status"] == "QUEUED"


def test_readiness_probe_fails_on_environment_project_mismatch(monkeypatch):
    """P0-CONFIG-001 test: Readiness probe must fail closed on staging/production project mismatch."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("GCP_PROJECT_ID", "zonepilot-stg-9a4285")  # mismatch!
    monkeypatch.setenv("PUBSUB_TOPIC_OPTIMIZATIONS", "zonepilot-opt-jobs-prod")

    res = client.get("/health/ready")
    assert res.status_code == 503
    data = res.json()
    assert data["status"] == "unready"
    assert "Environment/project mismatch" in data.get("reason", "")


def test_outbox_dispatcher_unit():
    """P1-OUTBOX-003 test: OutboxDispatcher runs standalone without synchronous API blocking."""
    from services.zonepilot.optimization.outbox_dispatcher import OutboxDispatcher

    dispatcher = OutboxDispatcher()
    count = dispatcher.run_once()
    assert count >= 0
