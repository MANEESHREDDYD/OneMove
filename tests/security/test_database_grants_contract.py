"""F-007: no blanket privileges, and no tenant table without RLS.

20260809000000_explicit_grants.sql granted ALL PRIVILEGES on every public table
to anon and authenticated. RLS was the only constraint on those grants, and six
OneMove tables never enabled it -- so decision_records and decision_replays were
readable and writable by anyone holding the public anon key.

These tests read the migration set statically, so they gate in CI without a
database. They are a contract check, not a substitute for verifying the applied
schema against a live PostgreSQL, which remains outstanding.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS = sorted((Path(__file__).resolve().parents[2] / "supabase" / "migrations").glob("*.sql"))
COMBINED = "\n".join(p.read_text(encoding="utf-8") for p in MIGRATIONS)

TENANT_TABLES = {
    "decision_records",
    "decision_replays",
    "forecast_records",
    "resilience_results",
    "resilience_scenarios",
    "shadow_evaluations",
    "optimization_jobs",
    "optimization_results",
    "optimization_problem_snapshots",
    "optimization_outbox",
}

# Never reachable by a browser role, in any mode.
SERVICE_ONLY_TABLES = {"optimization_outbox", "optimization_problem_snapshots"}


def test_migrations_were_discovered() -> None:
    assert MIGRATIONS, "no migrations found; the glob is wrong"


def test_blanket_grants_are_revoked_after_being_issued() -> None:
    """A later migration must revoke the blanket grant; order matters."""
    granted_at = next(
        (i for i, p in enumerate(MIGRATIONS) if "GRANT ALL PRIVILEGES ON ALL TABLES" in p.read_text(encoding="utf-8")),
        None,
    )
    revoked_at = next(
        (i for i, p in enumerate(MIGRATIONS) if "REVOKE ALL PRIVILEGES ON ALL TABLES" in p.read_text(encoding="utf-8")),
        None,
    )
    assert granted_at is not None, "expected the historical blanket grant to still be present"
    assert revoked_at is not None, "no migration revokes the blanket grant"
    assert revoked_at > granted_at, "the revoke must be ordered after the grant it undoes"


@pytest.mark.parametrize("table", sorted(TENANT_TABLES))
def test_every_tenant_table_enables_rls(table: str) -> None:
    pattern = rf"ALTER TABLE public\.{table}\s+ENABLE ROW LEVEL SECURITY"
    assert re.search(pattern, COMBINED), f"{table} holds tenant data but never enables RLS"


@pytest.mark.parametrize("table", sorted(SERVICE_ONLY_TABLES))
def test_internal_tables_are_never_granted_to_browser_roles(table: str) -> None:
    """Internal machinery must not be reachable via PostgREST."""
    for role in ("anon", "authenticated"):
        pattern = rf"GRANT\s+(?!USAGE)[A-Z, ]+\s+ON\s+public\.{table}\s+TO\s+[^;]*\b{role}\b"
        assert not re.search(pattern, COMBINED), f"{table} must not be granted to {role}"


def test_authenticated_receives_no_mutation_rights_on_tenant_tables() -> None:
    """Writes go through the API, which scopes by workspace explicitly."""
    for match in re.finditer(r"GRANT\s+([A-Z, ]+?)\s+ON\s+public\.(\w+)\s+TO\s+([^;]+);", COMBINED):
        privileges, table, roles = match.group(1), match.group(2), match.group(3)
        if table not in TENANT_TABLES or "authenticated" not in roles:
            continue
        granted = {p.strip() for p in privileges.split(",")}
        forbidden = granted & {"INSERT", "UPDATE", "DELETE", "ALL", "ALL PRIVILEGES", "TRUNCATE"}
        assert not forbidden, f"{table} grants {forbidden} to authenticated; mutation must go through the API"
