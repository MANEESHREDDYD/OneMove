"""F-017: every GitHub workflow must declare least-privilege token permissions.

Without an explicit `permissions:` block, GITHUB_TOKEN defaults to a write-scoped
token, so any compromised action or dependency in that workflow can push to the
repository.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).resolve().parents[2] / ".github" / "workflows").glob("*.yml"))

# Scopes beyond `contents: read` need a reason to exist.
JUSTIFIED_ELEVATED_SCOPES = {
    "security-events": "CodeQL uploads SARIF results",
    "id-token": "OIDC federation for keyless cloud auth",
    "actions": "workflow introspection required by CodeQL",
    "packages": "publishes container images",
    "pull-requests": "comments findings on the pull request",
}


def test_workflows_were_discovered() -> None:
    assert WORKFLOWS, "no workflows found; the glob is wrong"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_declares_permissions(path: Path) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    perms = doc.get("permissions")
    if perms is None:
        jobs = doc.get("jobs") or {}
        assert jobs and all("permissions" in job for job in jobs.values()), (
            f"{path.name} declares no permissions, so GITHUB_TOKEN defaults to write scope"
        )
        return
    assert isinstance(perms, dict), f"{path.name} must use a mapping, not a shorthand scope"
    assert perms.get("contents") in {"read", "write"}, f"{path.name} must state a contents scope"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_elevated_scopes_are_justified(path: Path) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    perms = doc.get("permissions")
    if not isinstance(perms, dict):
        return
    for scope, level in perms.items():
        if scope == "contents" or level in {"read", "none"}:
            continue
        assert scope in JUSTIFIED_ELEVATED_SCOPES, (
            f"{path.name} grants '{scope}: {level}' with no recorded justification"
        )
