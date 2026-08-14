from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_r1_osrm_smoke_is_owned_by_the_evidence_workflow():
    smoke_test = (ROOT / "tests/pipeline/test_osrm_smoke.py").read_text(encoding="utf-8")
    evidence_workflow = (ROOT / ".github/workflows/zonepilot-r1-evidence.yml").read_text(encoding="utf-8")
    python_workflow = (ROOT / ".github/workflows/python-ci.yml").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github/workflows/zonepilot-release.yml").read_text(encoding="utf-8")

    assert "@pytest.mark.r1_evidence" in smoke_test
    assert "python -m pytest tests/pipeline/test_osrm_smoke.py -v" in evidence_workflow
    assert 'pytest -m "not r1_evidence"' in python_workflow
    assert 'pytest -v -m "not r1_evidence"' in release_workflow


def test_codeql_scans_every_product_language_with_pinned_actions():
    workflow = (ROOT / ".github/workflows/codeql.yml").read_text(encoding="utf-8")

    for language in ("c-cpp", "java-kotlin", "javascript-typescript", "python"):
        assert f"- language: {language}" in workflow
    assert "queries: security-extended" in workflow
    assert "github/codeql-action/init@ff2f1c621b7f889edc0d3c761ac2e6a3f8cdb0dd" in workflow
    assert "github/codeql-action/analyze@ff2f1c621b7f889edc0d3c761ac2e6a3f8cdb0dd" in workflow


def test_python_gates_install_the_reviewed_runtime_manifests():
    expected_install = "-r requirements.txt -r services/api/requirements.txt"
    python_workflow = (ROOT / ".github/workflows/python-ci.yml").read_text(encoding="utf-8")
    release_workflow = (ROOT / ".github/workflows/zonepilot-release.yml").read_text(encoding="utf-8")

    assert expected_install in python_workflow
    assert expected_install in release_workflow


def test_public_workflows_do_not_execute_private_provider_acquisition():
    workflow_dir = ROOT / ".github" / "workflows"

    for workflow_path in workflow_dir.glob("*.yml"):
        workflow = workflow_path.read_text(encoding="utf-8")
        assert "services.collectors.scheduler_intraday" not in workflow
        assert "services.collectors.scheduler_midnight" not in workflow
        assert "TOMTOM_API_KEY" not in workflow
