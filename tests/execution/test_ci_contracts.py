"""Contracts that keep the public repository a source repository.

These tests encode invariants rather than a blocklist of known-bad strings, so
a newly added workflow cannot reintroduce private execution by using a name
nobody thought to forbid.
"""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = ROOT / ".github" / "workflows"

# Credentials that only the private execution plane may ever hold.
PRIVATE_EXECUTION_SECRETS = (
    "TOMTOM_API_KEY",
    "ZONEPILOT_DB_URL",
    "EXECUTION_DATABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
)

# Entry points that perform provider acquisition against live sources.
PRIVATE_ACQUISITION_ENTRYPOINTS = (
    "services.collectors.scheduler_intraday",
    "services.collectors.scheduler_midnight",
    "services.collectors.scheduler",
)


def _workflow_paths() -> list[Path]:
    return sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _triggers(document: dict) -> dict:
    """Return the ``on:`` block.

    YAML 1.1 parses a bare ``on`` key as the boolean ``True``, so both forms
    have to be checked or every scheduled workflow silently passes.
    """
    raw = document.get("on", document.get(True, {}))
    if isinstance(raw, str):
        return {raw: None}
    if isinstance(raw, list):
        return {item: None for item in raw}
    return raw or {}


def _permissions(document: dict) -> dict:
    merged = {}
    top = document.get("permissions")
    if isinstance(top, dict):
        merged.update(top)
    for job in (document.get("jobs") or {}).values():
        if isinstance(job, dict) and isinstance(job.get("permissions"), dict):
            merged.update(job["permissions"])
    return merged


@pytest.mark.parametrize("path", _workflow_paths(), ids=lambda p: p.name)
def test_public_workflow_never_references_private_execution_secrets(path: Path):
    """Public CI may name a variable; it may never read the private secret.

    ``zonepilot-release.yml`` legitimately sets ``ZONEPILOT_DB_URL`` to the
    ephemeral local Supabase it starts itself, so the invariant is about
    ``secrets.*`` lookups rather than the bare identifier.
    """
    workflow = path.read_text(encoding="utf-8")
    for secret in PRIVATE_EXECUTION_SECRETS:
        for lookup in (f"secrets.{secret}", f"secrets['{secret}']", f'secrets["{secret}"]'):
            assert lookup not in workflow, (
                f"{path.name} reads {lookup}. Provider credentials belong to the "
                "private execution repository, never to public CI."
            )


@pytest.mark.parametrize("path", _workflow_paths(), ids=lambda p: p.name)
def test_public_workflow_never_runs_provider_acquisition(path: Path):
    workflow = path.read_text(encoding="utf-8")
    for entrypoint in PRIVATE_ACQUISITION_ENTRYPOINTS:
        assert entrypoint not in workflow, (
            f"{path.name} invokes {entrypoint}. Acquisition runs in the private execution plane."
        )


@pytest.mark.parametrize("path", _workflow_paths(), ids=lambda p: p.name)
def test_scheduled_public_workflow_never_writes_to_the_repository(path: Path):
    """A cron job that commits to a protected branch can only ever fail.

    ``zonepilot-data-maintenance.yml`` did exactly this and failed on every run
    because it tried to push pruned rolling data into a protected public branch.
    """
    document = _load(path)
    if "schedule" not in _triggers(document):
        return

    assert _permissions(document).get("contents") != "write", (
        f"{path.name} is scheduled and requests contents:write. Scheduled public "
        "workflows must not mutate the repository."
    )

    workflow = path.read_text(encoding="utf-8")
    for forbidden in ("git push", "git commit"):
        assert forbidden not in workflow, (
            f"{path.name} is scheduled and runs '{forbidden}'. Rolling data state "
            "belongs to the private execution plane."
        )


def test_no_public_workflow_manages_rolling_dataset_state():
    for path in _workflow_paths():
        workflow = path.read_text(encoding="utf-8")
        assert "data/rolling" not in workflow, (
            f"{path.name} manages data/rolling. Rolling acquisition state is private execution data."
        )


def test_r1_osrm_smoke_is_owned_by_the_evidence_workflow():
    smoke_test = (ROOT / "tests/pipeline/test_osrm_smoke.py").read_text(encoding="utf-8")
    evidence_workflow = (WORKFLOW_DIR / "zonepilot-r1-evidence.yml").read_text(encoding="utf-8")
    python_workflow = (WORKFLOW_DIR / "python-ci.yml").read_text(encoding="utf-8")
    release_workflow = (WORKFLOW_DIR / "zonepilot-release.yml").read_text(encoding="utf-8")

    assert "@pytest.mark.r1_evidence" in smoke_test
    assert "python -m pytest tests/pipeline/test_osrm_smoke.py -v" in evidence_workflow
    assert 'pytest -m "not r1_evidence"' in python_workflow
    assert 'pytest -v -m "not r1_evidence"' in release_workflow


def test_codeql_scans_every_product_language_with_pinned_actions():
    workflow = (WORKFLOW_DIR / "codeql.yml").read_text(encoding="utf-8")

    for language in ("c-cpp", "java-kotlin", "javascript-typescript", "python"):
        assert f"- language: {language}" in workflow
    assert "queries: security-extended" in workflow
    assert "github/codeql-action/init@ff2f1c621b7f889edc0d3c761ac2e6a3f8cdb0dd" in workflow
    assert "github/codeql-action/analyze@ff2f1c621b7f889edc0d3c761ac2e6a3f8cdb0dd" in workflow


def test_python_gates_install_the_reviewed_runtime_manifests():
    expected_install = "-r requirements.txt -r services/api/requirements.txt"
    python_workflow = (WORKFLOW_DIR / "python-ci.yml").read_text(encoding="utf-8")
    release_workflow = (WORKFLOW_DIR / "zonepilot-release.yml").read_text(encoding="utf-8")

    assert expected_install in python_workflow
    assert expected_install in release_workflow
