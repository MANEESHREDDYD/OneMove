"""F-016: JWT verification must require exp and verify the issuer.

Two defects: the issuer claim was omitted from decode when SUPABASE_JWT_ISSUER
and SUPABASE_URL were both unset, so a token from any issuer signed with a known
key validated; and no required-claims option was passed, so PyJWT accepted a
token with no `exp` and that session never expired.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from services.api.core import auth

SECRET = "test-only-signing-secret-at-least-32-chars"
AUD = "authenticated"
ISS = "https://issuer.example.com/auth/v1"


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", AUD)
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", ISS)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    auth._jwks_client.cache_clear()


def _mint(claims: dict, secret: str = SECRET, alg: str = "HS256") -> str:
    return jwt.encode(claims, secret, algorithm=alg)


def _valid_claims(**over) -> dict:
    base = {
        "sub": "user-1",
        "aud": AUD,
        "iss": ISS,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    base.update(over)
    return base


def test_valid_token_is_accepted() -> None:
    """Control: without this the rejection tests could pass vacuously."""
    assert auth.verify_token(_mint(_valid_claims()))["sub"] == "user-1"


def test_token_without_exp_is_rejected() -> None:
    claims = _valid_claims()
    del claims["exp"]
    with pytest.raises(HTTPException) as exc:
        auth.verify_token(_mint(claims))
    assert exc.value.status_code == 401


def test_expired_token_is_rejected() -> None:
    claims = _valid_claims(exp=datetime.now(timezone.utc) - timedelta(hours=1))
    with pytest.raises(HTTPException) as exc:
        auth.verify_token(_mint(claims))
    assert exc.value.status_code == 401


def test_wrong_issuer_is_rejected() -> None:
    with pytest.raises(HTTPException):
        auth.verify_token(_mint(_valid_claims(iss="https://attacker.example.com/auth/v1")))


def test_wrong_audience_is_rejected() -> None:
    with pytest.raises(HTTPException):
        auth.verify_token(_mint(_valid_claims(aud="some-other-audience")))


def test_tampered_signature_is_rejected() -> None:
    with pytest.raises(HTTPException):
        auth.verify_token(_mint(_valid_claims(), secret="test-only-different-secret-32-chars"))


def test_alg_none_is_rejected() -> None:
    token = jwt.encode(_valid_claims(), key="", algorithm="none")
    with pytest.raises(HTTPException):
        auth.verify_token(token)


def test_missing_sub_is_rejected() -> None:
    claims = _valid_claims()
    del claims["sub"]
    with pytest.raises(HTTPException):
        auth.verify_token(_mint(claims))


def test_future_nbf_is_rejected() -> None:
    claims = _valid_claims(nbf=datetime.now(timezone.utc) + timedelta(hours=1))
    with pytest.raises(HTTPException):
        auth.verify_token(_mint(claims))


def test_clock_skew_is_explicit_and_bounded() -> None:
    assert 0 < auth._CLOCK_SKEW_SECONDS <= 120


def test_unconfigured_issuer_fails_closed_in_production(monkeypatch) -> None:
    """Missing issuer config must not silently disable issuer verification."""
    monkeypatch.delenv("SUPABASE_JWT_ISSUER", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    claims = _valid_claims()
    del claims["iss"]
    with pytest.raises(HTTPException) as exc:
        auth.verify_token(_mint(claims))
    assert exc.value.status_code == 503, "unconfigured issuer must fail closed, not degrade to no check"
