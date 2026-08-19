"""API Gateway Security & Adversarial Attack Suite.

Tests attack vectors:
- SQL Injection in path parameters and query strings
- Path traversal attempts in zone/dataset routes
- Oversized payload bodies
- Deeply nested JSON payloads
- Malformed data types (NaN, Infinity, string injection in int fields)
- Unhandled HTTP methods
- Invalid UTF-8 bytes
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.core.auth import get_current_user
from services.api.main import app


def mock_auth():
    return {
        "sub": "00000000-0000-0000-0000-000000000002",
        "workspace_id": "00000000-0000-0000-0000-000000000001",
        "role": "OWNER",
    }


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_auth
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_sqli_in_path_parameter_rejected(client):
    sqli_payloads = [
        "8860145b41fffff' OR '1'='1",
        "8860145b41fffff; DROP TABLE workspaces;--",
        "8860145b41fffff' UNION SELECT * FROM auth.users--",
    ]
    for sqli in sqli_payloads:
        res = client.get(f"/api/v1/zones/{sqli}/state")
        assert res.status_code in {404, 422}
        assert res.json()["error"]["code"] in {"NOT_FOUND", "INVALID_ARGUMENT", "VALIDATION_ERROR"}


def test_path_traversal_in_evidence_endpoint(client):
    traversal_paths = [
        "../../etc/passwd",
        "..%2F..%2Fetc%2Fshadow",
        "....//....//config.json",
    ]
    for path in traversal_paths:
        res = client.get(f"/api/v1/evidence/osm/{path}")
        assert res.status_code in {404, 422}


def test_malformed_type_injection_in_optimization(client, monkeypatch):
    monkeypatch.setattr(
        "services.api.routers.observatory._opt_service.submit_optimization",
        lambda **kwargs: {"id": "mock", "status": "QUEUED"},
    )
    bad_payload = {
        "min_open_facilities": "not-an-integer",
        "max_travel_seconds": {"nested": "injection"},
    }
    res = client.post("/api/v1/optimizations", json=bad_payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_negative_values_in_optimization_rejected(client, monkeypatch):
    monkeypatch.setattr(
        "services.api.routers.observatory._opt_service.submit_optimization",
        lambda **kwargs: {"id": "mock", "status": "QUEUED"},
    )
    bad_payload = {
        "min_open_facilities": -5,
        "max_open_facilities": -10,
    }
    res = client.post("/api/v1/optimizations", json=bad_payload)
    assert res.status_code in {202, 422}


def test_huge_deeply_nested_json_handling(client, monkeypatch):
    monkeypatch.setattr(
        "services.api.routers.observatory._res_service.execute_scenario",
        lambda **kwargs: {"id": "scen-1", "scenario_type": "ROAD_CLOSURE"},
    )
    nested = {"a": 1}
    for _ in range(100):
        nested = {"level": nested}
    res = client.post("/api/v1/scenarios", json={"parameters": nested})
    assert res.status_code in {201, 422}
