import os
import time

import jwt
from fastapi.testclient import TestClient

from services.api.core.auth import get_current_user
from services.api.main import app

client = TestClient(app)

SECRET = "REDACTED_SYNTHETIC_TEST_SECRET"
os.environ["SUPABASE_JWT_SECRET"] = SECRET
os.environ["SUPABASE_JWT_AUDIENCE"] = "authenticated"
os.environ["SUPABASE_JWT_ISSUER"] = "zonepilot_issuer"

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
    token = create_token({}, secret="wrong_secret")
    response = client.get("/api/v1/zones", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

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
    from fastapi import FastAPI, Depends, Request
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
