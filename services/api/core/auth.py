import os

import jwt
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from supabase import Client, create_client

security = HTTPBearer(auto_error=False)

def verify_token(token: str) -> dict:
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    jwt_public_key = os.environ.get("SUPABASE_JWT_PUBLIC_KEY")
    expected_issuer = os.environ.get("SUPABASE_JWT_ISSUER")
    expected_audience = os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")
    algorithm = os.environ.get("SUPABASE_JWT_ALGORITHM", "HS256")

    verification_key = jwt_public_key if algorithm in ("RS256", "ES256") and jwt_public_key else jwt_secret

    if not verification_key:
        raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET environment variable missing")

    try:
        decode_kwargs = {
            "algorithms": [algorithm],
            "audience": expected_audience
        }
        if expected_issuer:
            decode_kwargs["issuer"] = expected_issuer

        payload = jwt.decode(
            token,
            verification_key,
            **decode_kwargs
        )
        
        if expected_issuer and payload.get("iss") != expected_issuer:
            raise HTTPException(status_code=401, detail="Invalid token: wrong issuer")

        if "sub" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid token: wrong issuer")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token: wrong audience")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


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
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Authentication Token: {str(e)}")
