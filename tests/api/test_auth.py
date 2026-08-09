import datetime
import os

import jwt
import pytest
from core.auth import verify_token
from fastapi import HTTPException

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "REDACTED_SYNTHETIC_TEST_SECRET")
os.environ["SUPABASE_JWT_SECRET"] = SUPABASE_JWT_SECRET

def test_verify_token_valid():
    payload = {
        "sub": "user-123",
        "aud": "authenticated",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    result = verify_token(token)
    assert result["sub"] == "user-123"

def test_verify_token_altered_payload():
    payload = {
        "sub": "user-123",
        "aud": "authenticated",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    # alter token
    parts = token.split(".")
    parts[1] = "altered"
    bad_token = ".".join(parts)
    with pytest.raises(HTTPException) as exc:
        verify_token(bad_token)
    assert exc.value.status_code == 401

def test_verify_token_altered_signature():
    payload = {
        "sub": "user-123",
        "aud": "authenticated",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    parts = token.split(".")
    parts[2] = "badsig"
    bad_token = ".".join(parts)
    with pytest.raises(HTTPException) as exc:
        verify_token(bad_token)
    assert exc.value.status_code == 401

def test_verify_token_expired():
    payload = {
        "sub": "user-123",
        "aud": "authenticated",
        "exp": datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()

def test_verify_token_malformed():
    with pytest.raises(HTTPException) as exc:
        verify_token("not-a-token")
    assert exc.value.status_code == 401

def test_verify_token_unsigned():
    payload = {
        "sub": "user-123",
        "aud": "authenticated",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, "", algorithm="none")
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401

def test_verify_token_wrong_audience():
    payload = {
        "sub": "user-123",
        "aud": "public",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401
    assert "audience" in exc.value.detail.lower()

def test_verify_token_without_subject():
    payload = {
        "aud": "authenticated",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        verify_token(token)
    assert exc.value.status_code == 401
    assert "missing sub" in exc.value.detail.lower()

def test_verify_token_wrong_issuer_rejected():
    os.environ["SUPABASE_JWT_ISSUER"] = "https://trusted-supabase.com/auth/v1"
    try:
        payload = {
            "sub": "user-123",
            "aud": "authenticated",
            "iss": "https://malicious-issuer.com",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
        with pytest.raises(HTTPException) as exc:
            verify_token(token)
        assert exc.value.status_code == 401
        assert "issuer" in exc.value.detail.lower()
    finally:
        os.environ.pop("SUPABASE_JWT_ISSUER", None)

