"""F-010 and F-011: the system must not manufacture evidence or lineage.

F-010: the resilience service fabricated a travel matrix from index arithmetic
when the authentic OSRM artifact was missing, labelled it PUBLIC_GEOGRAPHIC with
the same matrix_id the authentic matrix uses, and persisted the resulting grade.

F-011: the persistence layer defaulted code_sha, graph_version,
assumption_version and solver_version, so a result claimed provenance it never had.
"""

from __future__ import annotations

import inspect

import pytest

from services.zonepilot.optimization.repository import OptimizationRepository
from services.zonepilot.optimization.service import SOLVER_VERSION
from services.zonepilot.resilience import service as resilience_service


def test_synthetic_matrix_generator_is_gone() -> None:
    assert not hasattr(resilience_service, "_mock_or_real_baseline_matrix")
    src = inspect.getsource(resilience_service)
    # The exact fabrication expression must not reappear in any form.
    assert "% 600" not in src, "index-arithmetic travel durations must not be synthesised"


def test_missing_matrix_fails_closed_instead_of_fabricating(tmp_path, monkeypatch) -> None:
    """With no authentic artifact, the baseline must refuse rather than invent."""
    monkeypatch.setattr(resilience_service, "default_data_root", lambda: tmp_path)
    with pytest.raises(FileNotFoundError) as exc:
        resilience_service._authentic_baseline_matrix()
    assert "MATRIX_UNAVAILABLE" in str(exc.value)


def test_save_result_requires_full_lineage() -> None:
    """No lineage parameter may carry a default."""
    sig = inspect.signature(OptimizationRepository.save_result)
    for name in ("code_sha", "graph_version", "assumption_version", "solver_version"):
        param = sig.parameters[name]
        assert param.default is inspect.Parameter.empty, f"{name} must not default; lineage cannot be invented"


def test_save_result_rejects_empty_lineage() -> None:
    repo = OptimizationRepository(dsn="postgresql://unused:unused@127.0.0.1:1/none")
    with pytest.raises(ValueError) as exc:
        repo.save_result(
            job_id="00000000-0000-0000-0000-000000000000",
            result_document={},
            pareto_document=None,
            problem_fingerprint="x",
            solver_status="OPTIMAL",
            action="NONE",
            fail_closed=False,
            code_sha="",
            graph_version="  ",
            assumption_version="",
            solver_version="",
        )
    message = str(exc.value)
    for name in ("code_sha", "graph_version", "assumption_version", "solver_version"):
        assert name in message


def test_solver_version_reports_the_installed_solver() -> None:
    """Provenance must identify the actual solver, not a generic literal."""
    assert SOLVER_VERSION.startswith("ortools-cp-sat-")
    assert SOLVER_VERSION != "ortools-cp-sat"
    assert "UNKNOWN_VERSION" not in SOLVER_VERSION


def test_every_save_result_call_site_supplies_all_required_arguments() -> None:
    """AUDIT-2 found a call site missing three required arguments.

    Making save_result's lineage mandatory (F-011) silently broke the fail-closed
    path in OptimizationService, which would have raised TypeError the first time
    a solve failed in production. The suite missed it because that path only runs
    with a database. This check is static, so it gates without one.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    sig = inspect.signature(OptimizationRepository.save_result)
    required = {
        name for name, param in sig.parameters.items() if param.default is inspect.Parameter.empty and name != "self"
    }

    offenders: list[str] = []
    for path in (root / "services").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "save_result"):
                continue
            # Only the optimization repository takes this contract.
            if "optimization" not in str(path):
                continue
            supplied = {kw.arg for kw in node.keywords if kw.arg}
            if any(kw.arg is None for kw in node.keywords):
                continue  # **kwargs expansion; cannot check statically
            missing = required - supplied
            if missing:
                rel = path.relative_to(root).as_posix()
                offenders.append(f"{rel}:{node.lineno} missing {sorted(missing)}")

    assert not offenders, "save_result called without required lineage: " + "; ".join(offenders)
