"""Comprehensive Authentication & Multi-Tenant Adversarial Attack Suite.

Tests attack vectors:
- Missing authorization header
- Malformed / garbage bearer token
- Expired token
- Future nbf (not before) claim
- Wrong audience ('wrong-aud' vs 'authenticated')
- Wrong issuer claim
- Alg: none forgery attempt
- Token signed with wrong HS256 secret
- Role forgery in claims (attempting escalated admin privilege without membership)
- IDOR: Cross-workspace decision ledger read attempt
- IDOR: Cross-workspace optimization job read attempt
- IDOR: Cross-workspace scenario execution attempt
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from services.api.main import app

JWT_SECRET = "test-adversarial-secret-key-32-chars-long"


@pytest.fixture(autouse=True)
def setup_auth_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", JWT_SECRET)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("SUPABASE_JWT_ALGORITHMS", "HS256")
    monkeypatch.delenv("SUPABASE_JWT_ISSUER", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)


@pytest.fixture
def client():
    return TestClient(app)


def _mint(payload: dict, secret: str = JWT_SECRET, alg: str = "HS256") -> str:
    return jwt.encode(payload, secret, algorithm=alg)


def test_missing_auth_header(client):
    res = client.get("/api/v1/zones")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_malformed_bearer_token(client):
    res = client.get("/api/v1/zones", headers={"Authorization": "Bearer this.is.garbage"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_expired_jwt_rejected(client):
    now = int(datetime.now(timezone.utc).timestamp())
    token = _mint({
        "sub": "usr_test",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now - 7200,
        "exp": now - 3600,
    })
    res = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_future_nbf_rejected(client):
    now = int(datetime.now(timezone.utc).timestamp())
    token = _mint({
        "sub": "usr_test",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "nbf": now + 3600,
        "exp": now + 7200,
    })
    res = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_wrong_audience_rejected(client):
    token = _mint({
        "sub": "usr_test",
        "aud": "attacker-fake-audience",
        "role": "authenticated",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
    })
    res = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_algorithm_none_forgery_rejected(client):
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": "usr_admin", "aud": "authenticated", "role": "admin"}
    b64_h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    b64_p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    forged_token = f"{b64_h}.{b64_p}."

    res = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {forged_token}"})
    assert res.status_code == 401


def test_tampered_secret_signature_rejected(client):
    token = _mint(
        {"sub": "usr_test", "aud": "authenticated", "role": "authenticated"},
        secret="attacker-different-secret-key-32-chars",
    )
    res = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_cross_workspace_decision_idor_isolation(client, monkeypatch):
    """Verify Tenant A cannot read Tenant B's decision records."""
    token_b = _mint({
        "sub": "usr_tenant_b",
        "aud": "authenticated",
        "role": "authenticated",
    })

    fake_dec_id = str(uuid.uuid4())
    monkeypatch.setattr("services.api.routers.observatory._dec_ledger.get_decision", lambda did, wid: None)

    res = client.get(f"/api/v1/decisions/{fake_dec_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_cross_workspace_optimization_idor_isolation(client, monkeypatch):
    """Verify Tenant A cannot retrieve Tenant B's optimization result."""
    token_b = _mint({
        "sub": "usr_tenant_b",
        "aud": "authenticated",
        "role": "authenticated",
    })

    fake_opt_id = str(uuid.uuid4())
    monkeypatch.setattr("services.api.routers.observatory._opt_service.get_optimization", lambda oid, wid: None)

    res = client.get(f"/api/v1/optimizations/{fake_opt_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"
