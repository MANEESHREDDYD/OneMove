from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from supabase import create_client, Client
import jwt

security = HTTPBearer()

def verify_token(token: str) -> dict:
    """
    Centralized cryptographic JWT verifier for ZonePilot.
    Supports symmetric (HS256) and asymmetric (RS256/JWKS) signing modes.
    Validates signature, allowed algorithm, expiration, audience, subject, and issuer (when configured).
    """
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    jwt_public_key = os.environ.get("SUPABASE_JWT_PUBLIC_KEY")
    expected_issuer = os.environ.get("SUPABASE_JWT_ISSUER")
    algorithm = os.environ.get("SUPABASE_JWT_ALGORITHM", "HS256")

    # Use public key for asymmetric RS256 mode, or secret for symmetric HS256 mode
    verification_key = jwt_public_key if algorithm == "RS256" and jwt_public_key else jwt_secret

    if not verification_key:
        raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET environment variable missing")

    try:
        decode_kwargs = {
            "algorithms": [algorithm],
            "audience": "authenticated"
        }
        if expected_issuer:
            decode_kwargs["issuer"] = expected_issuer

        payload = jwt.decode(
            token,
            verification_key,
            **decode_kwargs
        )
        
        # Check issuer explicitly if present in payload and expected
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

def get_supabase(credentials: HTTPAuthorizationCredentials = Security(security)) -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase environment variables missing")
    
    token = credentials.credentials
    # Validate token before trusting identity
    verify_token(token)
    
    try:
        client = create_client(url, key)
        client.postgrest.auth(token)
        return client
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Authentication Token: {str(e)}")

def get_participant_id(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    token = credentials.credentials
    payload = verify_token(token)
    return payload["sub"]
