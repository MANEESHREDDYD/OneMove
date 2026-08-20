"""Static contract: tenant-owned repository reads must scope by workspace.

The backend connects with an owner-role DSN, so PostgreSQL RLS is not in force
on these paths. The application-layer workspace predicate is the ONLY tenant
isolation control, which makes an optional predicate a cross-tenant read waiting
to happen:

    if workspace_id:                     # caller omits it -> no scoping at all
        query += " AND workspace_id = %s"

This test fails the build when that pattern reappears, or when a tenant-owned
read accepts `workspace_id: str | None`.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

REPOSITORY_FILES = sorted((REPO_ROOT / "services").rglob("*repositor*.py"))

# Reads of tenant-owned resources. Each must take a mandatory workspace_id.
TENANT_SCOPED_METHODS = {
    "get_decision",
    "get_shadow",
    "get_zone_forecasts",
    "get_scenario",
    "get_problem_snapshot",
    "list_decisions",
    "list_scenarios",
    "list_jobs",
}

# Methods that legitimately operate across all tenants. Each needs an explicit
# justification here, so widening the exemption is a reviewed act.
SYSTEM_WIDE_EXEMPTIONS = {
    "claim_pending_outbox_events": "Dispatcher drains the outbox across tenants; each event carries its own workspace_id.",
    "get_oldest_pending_outbox_age_seconds": "Operational SLO gauge over the whole outbox; returns no tenant data.",
    "mark_outbox_published": "Keyed by event_id, which is globally unique and already tenant-bound.",
    "mark_outbox_failed": "Keyed by event_id, which is globally unique and already tenant-bound.",
}

_CONDITIONAL_SCOPE = re.compile(r"if\s+workspace_id\s*:\s*\n\s*query\s*\+=", re.MULTILINE)


def test_repository_files_were_discovered() -> None:
    """Guard against the glob silently matching nothing."""
    assert REPOSITORY_FILES, "no repository modules found; the scan pattern is wrong"


@pytest.mark.parametrize("path", REPOSITORY_FILES, ids=lambda p: p.name)
def test_no_conditional_workspace_scoping(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    matches = _CONDITIONAL_SCOPE.findall(source)
    assert not matches, (
        f"{path.relative_to(REPO_ROOT)} builds its workspace predicate conditionally. "
        "A tenant-owned query must always scope by workspace; make the argument mandatory."
    )


@pytest.mark.parametrize("path", REPOSITORY_FILES, ids=lambda p: p.name)
def test_tenant_scoped_methods_require_a_workspace(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in TENANT_SCOPED_METHODS:
            continue
        if node.name in SYSTEM_WIDE_EXEMPTIONS:
            continue

        args = node.args.args
        names = [a.arg for a in args]
        if "workspace_id" not in names:
            offenders.append(f"{node.name}: no workspace_id parameter")
            continue

        # A default value makes the predicate skippable by any caller.
        index = names.index("workspace_id")
        defaults_start = len(args) - len(node.args.defaults)
        if index >= defaults_start:
            offenders.append(f"{node.name}: workspace_id has a default, so callers may omit it")

        annotation = args[index].annotation
        if annotation is not None and "None" in ast.unparse(annotation):
            offenders.append(f"{node.name}: workspace_id is Optional")

    assert not offenders, f"{path.relative_to(REPO_ROOT)} has unscoped tenant reads: " + "; ".join(offenders)
