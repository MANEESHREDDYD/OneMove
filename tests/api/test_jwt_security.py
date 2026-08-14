import os
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.testclient import TestClient

from services.api.core import auth
from services.api.core.auth import get_current_user, verify_token
from services.api.main import app

client = TestClient(app)

SECRET = os.environ["SUPABASE_JWT_SECRET"]

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", "zonepilot_issuer")

def create_token(payload: dict, secret: str = SECRET) -> str:
    default_payload = {
        "sub": "user-123",
        "aud": "authenticated",
        "iss": "zonepilot_issuer",
        "exp": int(time.time()) + 3600
    }
    default_payload.update(payload)
    return jwt.encode(default_payload, secret, algorithm="HS256")


def test_unauthenticated_rejection():
    # Attempting to hit an authenticated endpoint without token
    response = client.get("/api/v1/zones")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

def test_malformed_bearer():
    response = client.get("/api/v1/zones", headers={"Authorization": "Bearer malformed.token.here"})
    assert response.status_code == 401

def test_invalid_signature():
    token = create_token({}, secret=f"wrong-{SECRET}")
    response = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_es256_token_uses_supabase_jwks(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(
        {
            "sub": "user-es256",
            "aud": "authenticated",
            "iss": "https://project.supabase.co/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        private_key,
        algorithm="ES256",
        headers={"kid": "active-signing-key"},
    )

    class StaticJwksClient:
        def get_signing_key_from_jwt(self, candidate):
            assert candidate == token
            return type("SigningKey", (), {"key": private_key.public_key()})()

    monkeypatch.delenv("SUPABASE_JWT_ALGORITHM", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", "https://project.supabase.co/auth/v1")
    monkeypatch.setattr(auth, "_jwks_client", lambda _url: StaticJwksClient())

    assert verify_token(token)["sub"] == "user-es256"


def test_unapproved_jwt_algorithm_is_rejected(monkeypatch):
    monkeypatch.delenv("SUPABASE_JWT_ALGORITHM", raising=False)
    token = jwt.encode(
        {
            "sub": "user-384",
            "aud": "authenticated",
            "iss": "zonepilot_issuer",
            "exp": int(time.time()) + 3600,
        },
        SECRET,
        algorithm="HS384",
    )

    with pytest.raises(HTTPException) as exc_info:
        verify_token(token)

    assert exc_info.value.status_code == 401

def test_expired_token():
    token = create_token({"exp": int(time.time()) - 3600})
    response = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

def test_wrong_issuer():
    token = create_token({"iss": "wrong_issuer"})
    response = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

def test_wrong_audience():
    token = create_token({"aud": "public"})
    response = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

def test_wrong_workspace():
    # Setup token for workspace A, but request workspace B
    token = create_token({"workspace_id": "workspace-A"})
    response = client.get(
        "/api/v1/zones",
        headers={
            "Authorization": f"Bearer {token}",
            "x-workspace-id": "workspace-B"
        }
    )
    assert response.status_code == 403

def test_wrong_role():
    from fastapi import Depends, FastAPI, Request
    from fastapi.testclient import TestClient
    
    app_test = FastAPI()
    
    @app_test.middleware("http")
    async def set_role(request: Request, call_next):
        request.state.required_role = "admin"
        return await call_next(request)
        
    @app_test.get("/test_admin_only")
    def admin_only(user=Depends(get_current_user)):
        return {"ok": True}
        
    client_test = TestClient(app_test)
    token = create_token({"role": "viewer"})
    response = client_test.get("/test_admin_only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

def test_oversized_payload():
    large_payload = "A" * 1024 * 1024 * 5 # 5MB payload
    response = client.post("/api/v1/scenarios", json={"data": large_payload})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
