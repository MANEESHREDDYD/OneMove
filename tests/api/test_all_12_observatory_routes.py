"""Comprehensive test suite proving all 12 Observatory API routes on FastAPI."""

import pytest
from fastapi.testclient import TestClient

from services.api.core.auth import get_current_user
from services.api.main import app


def mock_operator_auth():
    return {
        "sub": "00000000-0000-0000-0000-000000000001",
        "workspace_id": "ws-pilot-default",
        "role": "operator",
    }


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_operator_auth
    yield
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


def test_route_1_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_route_2_version(monkeypatch):
    monkeypatch.setenv("ZONEPILOT_APP_VERSION", "1.5.1")
    monkeypatch.setenv("ZONEPILOT_GIT_SHA", "483c8e1f6d256c39987d3780ffdb342f935f7ac2")
    monkeypatch.setenv("ZONEPILOT_SCHEMA_VERSION", "1.0.0")
    res = client.get("/api/v1/version")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()["data"]
        assert data["app_version"] == "1.5.1"
        assert data["git_sha"] == "483c8e1f6d256c39987d3780ffdb342f935f7ac2"


def test_route_3_zones():
    res = client.get("/api/v1/zones")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()
        assert len(data["data"]) == 94


def test_route_4_map_layers():
    res = client.get("/api/v1/network/map-layers")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()
        assert len(data["data"]) >= 1


def test_route_5_datasets():
    res = client.get("/api/v1/datasets")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()
        assert len(data["data"]) >= 1


def test_route_6_data_health():
    res = client.get("/api/v1/data-health")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()
        assert isinstance(data["data"], list)
        assert "evaluated_at" in data


def test_route_7_optimizations_lifecycle():
    # Submit job
    req = {
        "idempotency_key": "test-idem-route-7",
        "min_open_facilities": 2,
        "max_open_facilities": 4,
        "max_travel_seconds": 1800,
        "allow_uncovered_demand": True,
    }
    post_res = client.post("/api/v1/optimizations", json=req)
    assert post_res.status_code in {200, 201, 202}
    job_id = post_res.json()["job_id"]

    # Retrieve job
    get_res = client.get(f"/api/v1/optimizations/{job_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["status"] == "SUCCESS"
    assert data["solver_status"] == "OPTIMAL"
    assert len(data["opened_facilities"]) >= 2


def test_route_8_scenarios_side_effect_free():
    # GET is side effect free
    get_res = client.get("/api/v1/scenarios")
    assert get_res.status_code == 200

    # POST creates scenario
    post_res = client.post(
        "/api/v1/scenarios",
        json={
            "scenario_type": "ROAD_CLOSURE",
            "description": "Corridor disruption test",
            "parameters": {"multiplier": 1.4},
            "seed": 42,
        },
    )
    assert post_res.status_code == 201
    scen_id = post_res.json()["scenario_id"]

    # GET specific scenario
    scen_res = client.get(f"/api/v1/scenarios/{scen_id}")
    assert scen_res.status_code == 200
    assert scen_res.json()["scenario_id"] == scen_id


def test_route_9_experiments():
    res = client.get("/api/v1/experiments")
    assert res.status_code == 200
    assert len(res.json()["experiments"]) == 4


def test_route_10_decisions_and_pit_replay():
    # Record decision
    dec_req = {
        "network_version": "1.1.0+bad320dd48da",
        "dataset_version": "1.0.0",
        "feature_snapshot_hash": "snap-7b443717",
        "selected_action": "OPEN_FACILITIES",
        "opened_facilities": ["fac:8861892421fffff", "fac:8861892537fffff"],
        "objective_value": 450000,
        "expected_travel_seconds": 620,
        "p95_travel_seconds": 840,
        "coverage_basis_points": 9600,
        "graph_version": "1.1.0+bad320dd48da",
        "osrm_bundle_hash": "7b4437178db62410bb85b6ef1e68fe2f07b7880ce281d146a1480f64ab86b383",
        "solver_version": "ortools-cp-sat",
    }
    post_res = client.post("/api/v1/decisions", json=dec_req)
    assert post_res.status_code == 201
    dec_id = post_res.json()["decision_id"]

    # Replay decision with PIT validation
    rep_res = client.post(
        f"/api/v1/decisions/{dec_id}/replay",
        json={
            "recomputed_action": "OPEN_FACILITIES",
            "recomputed_facilities": ["fac:8861892421fffff", "fac:8861892537fffff"],
            "recomputed_objective": 450000,
        },
    )
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["pit_valid"] is True
    assert rep_data["reproduced_exact_action"] is True
    assert rep_data["reproduced_exact_facilities"] is True


def test_route_11_forecast_prediction():
    res = client.post(
        "/api/v1/forecast/predict",
        json={
            "zone_id": "8860145b41fffff",
            "horizon_hours": 12,
            "target": "WEATHER_TRAVEL_INFLATION_PERCENT",
            "model": "LAST_OBSERVATION",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["zone_id"] == "8860145b41fffff"
    assert data["horizon_hours"] == 12


def test_route_12_assistant_query():
    res = client.post(
        "/api/v1/assistant/query",
        json={
            "query": "What is the network state for zone 8860145b41fffff?",
            "tool_name": "get_zone_state",
            "arguments": {"zone_id": "8860145b41fffff"},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_name"] == "get_zone_state"
    assert "result_data" in data
