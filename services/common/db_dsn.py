"""Database DSN resolution.

P0-CREDENTIAL-001: this module previously embedded a live hosted Supabase
credential as a hard-coded return value, and additionally discarded any
DATABASE_URL that did not match one specific pooler host -- pinning every
process, including the test suite, to the production database.

The contract is now:

  * The DSN comes from the environment. There is no source-code fallback.
  * Missing configuration is a hard, loud failure -- never a silent connection.
  * Under a test runner the DSN comes from TEST_DATABASE_URL, and pointing it
    at a protected (staging/production) database is refused.
"""

from __future__ import annotations

import hashlib
import os
import sys
from urllib.parse import urlsplit

__all__ = [
    "DatabaseConfigurationError",
    "ProtectedDatabaseError",
    "database_fingerprint",
    "get_database_dsn",
    "running_under_test_runner",
]

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db", "postgres", "host.docker.internal"}


class DatabaseConfigurationError(RuntimeError):
    """Required database configuration is absent or unusable."""


class ProtectedDatabaseError(RuntimeError):
    """A test runner attempted to connect to a protected (shared) database."""


def running_under_test_runner() -> bool:
    """True when executing under pytest."""
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules


def database_fingerprint(dsn: str) -> str:
    """Stable, non-reversible identifier for a database target.

    Derived from host/port/path only -- deliberately excludes credentials so
    fingerprints are safe to log, compare, and publish in incident evidence.
    """
    parts = urlsplit(dsn)
    target = f"{(parts.hostname or '').lower()}:{parts.port or 5432}{parts.path or ''}"
    return hashlib.sha256(target.encode("utf-8")).hexdigest()[:16]


def _protected_fingerprints() -> set[str]:
    raw = os.environ.get("PROTECTED_DATABASE_FINGERPRINTS", "")
    return {f.strip() for f in raw.split(",") if f.strip()}


def _is_local_host(dsn: str) -> bool:
    return (urlsplit(dsn).hostname or "").lower() in _LOCAL_HOSTS


def _assert_test_database_is_safe(dsn: str) -> None:
    """Refuse to run a destructive test suite against a shared database."""
    fingerprint = database_fingerprint(dsn)

    if fingerprint in _protected_fingerprints():
        raise ProtectedDatabaseError(
            f"TEST_DATABASE_URL resolves to protected database {fingerprint}, which is listed in "
            "PROTECTED_DATABASE_FINGERPRINTS. The test suite performs destructive writes and will not run against it."
        )

    if not _is_local_host(dsn) and os.environ.get("ALLOW_NONLOCAL_TEST_DATABASE") != "1":
        raise ProtectedDatabaseError(
            f"TEST_DATABASE_URL points at non-local host database {fingerprint}. The test suite performs "
            "destructive writes. Use a local/ephemeral PostgreSQL, or set ALLOW_NONLOCAL_TEST_DATABASE=1 to "
            "acknowledge the risk explicitly."
        )


def get_database_dsn() -> str:
    """Resolve the database DSN from the environment. Never falls back to a literal."""
    if running_under_test_runner():
        dsn = os.environ.get("TEST_DATABASE_URL", "").strip()
        if not dsn:
            raise DatabaseConfigurationError(
                "TEST_DATABASE_URL is required when running the test suite. It must point at a local or "
                "ephemeral PostgreSQL instance -- never at staging or production. See docs/DEPLOYMENT.md."
            )
        _assert_test_database_is_safe(dsn)
        return dsn

    dsn = (os.environ.get("DATABASE_URL") or os.environ.get("EXECUTION_DATABASE_URL") or "").strip()
    if not dsn:
        env = os.environ.get("ENVIRONMENT", "").lower() or "unset"
        raise DatabaseConfigurationError(
            f"DATABASE_URL is required (ENVIRONMENT={env}) and is not set. There is no built-in database "
            "credential. Configure it from the platform secret store before starting the service."
        )
    return dsn
