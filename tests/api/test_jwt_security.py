import os
import time
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.testclient import TestClient

from services.api.core import auth
from services.api.core.auth import verify_token
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
        "exp": int(time.time()) + 3600,
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
        "/api/v1/zones", headers={"Authorization": f"Bearer {token}", "x-workspace-id": "workspace-B"}
    )
    assert response.status_code == 403


WORKSPACE_A = "11111111-1111-4111-8111-111111111111"
WORKSPACE_B = "22222222-2222-4222-8222-222222222222"


def _admin_only_app():
    """A route guarded the way production routes are: by stored workspace role.

    The old test here set ``request.state.required_role`` and asserted a 403.
    Nothing outside that test ever set the attribute, so it proved only that the
    test could reach its own middleware. The dependency below is the real
    enforcement path, so this asserts against something that actually ships.
    """

    from fastapi import Depends, FastAPI

    app_test = FastAPI()

    @app_test.get("/admin_only")
    def admin_only(
        principal=Depends(auth.require_workspace_role(auth.WorkspaceRole.OWNER, auth.WorkspaceRole.ADMIN)),
    ):
        return {"workspace_id": principal.workspace_id, "role": principal.role.value}

    return TestClient(app_test)


def _stub_memberships(monkeypatch, *pairs):
    """Pin the *stored* membership state the server will trust."""

    def fake(user_id: str):
        return tuple(auth.WorkspacePrincipal(user_id=user_id, workspace_id=ws, role=role) for ws, role in pairs)

    monkeypatch.setattr(auth, "workspace_memberships", fake)


def test_researcher_cannot_administer(monkeypatch):
    _stub_memberships(monkeypatch, (WORKSPACE_A, auth.WorkspaceRole.RESEARCHER))
    token = create_token({})
    response = _admin_only_app().get(
        "/admin_only",
        headers={"Authorization": f"Bearer {token}", "x-workspace-id": WORKSPACE_A},
    )
    assert response.status_code == 403
    assert "RESEARCHER" in response.json()["detail"]


def test_viewer_cannot_administer(monkeypatch):
    _stub_memberships(monkeypatch, (WORKSPACE_A, auth.WorkspaceRole.VIEWER))
    token = create_token({})
    response = _admin_only_app().get(
        "/admin_only",
        headers={"Authorization": f"Bearer {token}", "x-workspace-id": WORKSPACE_A},
    )
    assert response.status_code == 403


def test_owner_may_administer_own_workspace(monkeypatch):
    _stub_memberships(monkeypatch, (WORKSPACE_A, auth.WorkspaceRole.OWNER))
    token = create_token({})
    response = _admin_only_app().get(
        "/admin_only",
        headers={"Authorization": f"Bearer {token}", "x-workspace-id": WORKSPACE_A},
    )
    assert response.status_code == 200
    assert response.json() == {"workspace_id": WORKSPACE_A, "role": "OWNER"}


def test_role_forgery_in_token_is_ignored(monkeypatch):
    """A token may claim any role it likes; only stored membership decides."""

    _stub_memberships(monkeypatch, (WORKSPACE_A, auth.WorkspaceRole.VIEWER))
    token = create_token({"role": "OWNER", "workspace_role": "OWNER", "user_role": "ADMIN"})
    response = _admin_only_app().get(
        "/admin_only",
        headers={"Authorization": f"Bearer {token}", "x-workspace-id": WORKSPACE_A},
    )
    assert response.status_code == 403
    assert "VIEWER" in response.json()["detail"]


def test_workspace_forgery_is_denied(monkeypatch):
    """A header may select only among workspaces the subject provably joined."""

    _stub_memberships(monkeypatch, (WORKSPACE_A, auth.WorkspaceRole.OWNER))
    token = create_token({"workspace_id": WORKSPACE_B})
    response = _admin_only_app().get(
        "/admin_only",
        headers={"Authorization": f"Bearer {token}", "x-workspace-id": WORKSPACE_B},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not a member of the requested workspace"


def test_no_membership_is_denied(monkeypatch):
    _stub_memberships(monkeypatch)
    token = create_token({})
    response = _admin_only_app().get(
        "/admin_only",
        headers={"Authorization": f"Bearer {token}", "x-workspace-id": WORKSPACE_A},
    )
    assert response.status_code == 403


def test_ambiguous_workspace_selection_fails_closed(monkeypatch):
    """Two memberships and no selector is ambiguous, so it must not guess."""

    _stub_memberships(
        monkeypatch,
        (WORKSPACE_A, auth.WorkspaceRole.OWNER),
        (WORKSPACE_B, auth.WorkspaceRole.VIEWER),
    )
    token = create_token({})
    response = _admin_only_app().get("/admin_only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Workspace selection required"


def test_required_role_attribute_is_gone():
    """Regression guard: the inert authorization path must not come back."""

    source = Path(auth.__file__).read_text(encoding="utf-8")
    assert "required_role" not in source


def test_oversized_payload():
    large_payload = "A" * 1024 * 1024 * 5  # 5MB payload
    response = client.post("/api/v1/scenarios", json={"data": large_payload})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
