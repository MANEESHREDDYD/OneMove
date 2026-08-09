from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from supabase import create_client, Client

import jwt

security = HTTPBearer()

def verify_token(token: str) -> dict:
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET environment variable missing")
    try:
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        if "sub" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

def get_supabase(credentials: HTTPAuthorizationCredentials = Security(security)) -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase environment variables missing")
    
    token = credentials.credentials
    # Validate token before trusting identity
    verify_token(token)
    
    try:
        # Client initialized with user's JWT for RLS
        client = create_client(url, key)
        client.postgrest.auth(token)
        return client
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Authentication Token: {str(e)}")

def get_participant_id(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    token = credentials.credentials
    payload = verify_token(token)
    return payload["sub"]
