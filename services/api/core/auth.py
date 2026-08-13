import os
from functools import lru_cache
from urllib.parse import urljoin

import jwt
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from supabase import Client, create_client

security = HTTPBearer(auto_error=False)

_ASYMMETRIC_ALGORITHMS = frozenset({"ES256", "RS256"})


def _allowed_algorithms() -> set[str]:
    configured = os.environ.get("SUPABASE_JWT_ALGORITHMS")
    if configured:
        return {item.strip() for item in configured.split(",") if item.strip()}

    legacy_algorithm = os.environ.get("SUPABASE_JWT_ALGORITHM")
    if legacy_algorithm:
        return {legacy_algorithm}

    # Supabase projects can issue new asymmetric tokens while legacy sessions
    # remain HS256 during a signing-key migration. The key source is selected
    # independently below, so allowing both cannot create an algorithm-confusion
    # path between a public key and the legacy shared secret.
    return {"ES256", "RS256", "HS256"}


def _expected_issuer() -> str | None:
    configured = os.environ.get("SUPABASE_JWT_ISSUER")
    if configured:
        return configured.rstrip("/")

    supabase_url = os.environ.get("SUPABASE_URL")
    if not supabase_url:
        return None
    return urljoin(f"{supabase_url.rstrip('/')}/", "auth/v1")


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        jwks_url,
        cache_keys=True,
        cache_jwk_set=True,
        lifespan=600,
        timeout=5,
    )


def _verification_key(token: str, algorithm: str):
    if algorithm == "HS256":
        secret = os.environ.get("SUPABASE_JWT_SECRET")
        if not secret:
            raise HTTPException(status_code=500, detail="Supabase JWT verifier is not configured")
        return secret

    public_key = os.environ.get("SUPABASE_JWT_PUBLIC_KEY")
    if public_key:
        return public_key

    supabase_url = os.environ.get("SUPABASE_URL")
    jwks_url = os.environ.get("SUPABASE_JWKS_URL")
    if not jwks_url and supabase_url:
        jwks_url = urljoin(f"{supabase_url.rstrip('/')}/", "auth/v1/.well-known/jwks.json")
    if not jwks_url:
        raise HTTPException(status_code=500, detail="Supabase JWKS verifier is not configured")

    try:
        return _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Token verification temporarily unavailable",
        ) from exc
    except jwt.PyJWKClientError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

def verify_token(token: str) -> dict:
    expected_issuer = _expected_issuer()
    expected_audience = os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")

    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
        if algorithm not in _allowed_algorithms() or algorithm not in _ASYMMETRIC_ALGORITHMS | {"HS256"}:
            raise jwt.InvalidAlgorithmError("JWT signing algorithm is not allowed")

        verification_key = _verification_key(token, algorithm)
        decode_kwargs = {
            "algorithms": [algorithm],
            "audience": expected_audience,
        }
        if expected_issuer:
            decode_kwargs["issuer"] = expected_issuer

        payload = jwt.decode(
            token,
            verification_key,
            **decode_kwargs
        )
        
        if "sub" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid token: wrong issuer")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token: wrong audience")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    """Extracts payload and asserts Workspace and Role access if required by headers."""
    payload = verify_token(credentials.credentials)
    
    # Assert Workspace boundaries if passed
    req_workspace = request.headers.get("x-workspace-id")
    token_workspace = payload.get("workspace_id")
    if req_workspace and token_workspace and req_workspace != token_workspace:
        raise HTTPException(status_code=403, detail="Invalid token: wrong workspace")

    # Assert Role boundaries
    token_role = payload.get("role", "anon")
    req_role = getattr(request.state, "required_role", None)
    if req_role and token_role != req_role:
        raise HTTPException(status_code=403, detail="Invalid token: wrong role")

    return payload


def get_participant_id(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    payload = verify_token(token)
    return payload["sub"]


def get_supabase(credentials: HTTPAuthorizationCredentials = Security(security)) -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase environment variables missing")
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    verify_token(token)
    
    try:
        client = create_client(url, key)
        client.postgrest.auth(token)
        return client
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
