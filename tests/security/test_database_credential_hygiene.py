"""P0-CREDENTIAL-001 regression: no built-in database credential, ever.

The DSN resolver previously returned a hard-coded hosted Supabase credential and
discarded any DATABASE_URL that did not match one specific pooler host. That made
every process -- including CI -- silently connect to the production database.
"""

from __future__ import annotations

import inspect
import re

import pytest

from services.common import db_dsn
from services.common.db_dsn import (
    DatabaseConfigurationError,
    ProtectedDatabaseError,
    database_fingerprint,
    get_database_dsn,
)

LOCAL_DSN = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
HOSTED_DSN = "postgresql://postgres.someproject:fake-fixture-password@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"


def test_module_source_contains_no_embedded_credential() -> None:
    """The resolver must not carry any URI-embedded credential literal."""
    source = inspect.getsource(db_dsn)
    embedded = re.findall(r"postgres(?:ql)?://[^:@/\s\"']+:[^@\s\"']+@", source)
    assert embedded == [], f"db_dsn.py contains embedded credential literal(s): {len(embedded)}"


def test_missing_test_database_url_fails_closed(monkeypatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConfigurationError):
        get_database_dsn()


def test_test_runner_refuses_nonlocal_database(monkeypatch) -> None:
    """A destructive suite must not silently target a hosted database."""
    monkeypatch.setenv("TEST_DATABASE_URL", HOSTED_DSN)
    monkeypatch.delenv("ALLOW_NONLOCAL_TEST_DATABASE", raising=False)
    with pytest.raises(ProtectedDatabaseError):
        get_database_dsn()


def test_test_runner_refuses_protected_fingerprint(monkeypatch) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", LOCAL_DSN)
    monkeypatch.setenv("PROTECTED_DATABASE_FINGERPRINTS", database_fingerprint(LOCAL_DSN))
    with pytest.raises(ProtectedDatabaseError):
        get_database_dsn()


def test_local_test_database_is_accepted(monkeypatch) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", LOCAL_DSN)
    monkeypatch.delenv("PROTECTED_DATABASE_FINGERPRINTS", raising=False)
    assert get_database_dsn() == LOCAL_DSN


def test_fingerprint_excludes_credentials() -> None:
    """Fingerprints are safe to publish: same target, different password."""
    a = "postgresql://user:secret-one@db.example.com:5432/postgres"
    b = "postgresql://user:secret-two@db.example.com:5432/postgres"
    assert database_fingerprint(a) == database_fingerprint(b)
    assert database_fingerprint(a) != database_fingerprint(LOCAL_DSN)
