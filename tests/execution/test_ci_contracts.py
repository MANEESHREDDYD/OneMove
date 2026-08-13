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
