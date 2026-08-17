"""Process-isolated public interface for the native OR-Tools solver."""

from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys

from pydantic import ValidationError

from services.zonepilot.optimization.contracts import (
    OptimizationAction,
    OptimizationProblem,
    OptimizationResult,
    OptimizationStatus,
    ScenarioInputLineage,
    problem_fingerprint,
)

_WORKER_STARTUP_GRACE_SECONDS = 10.0


def _solver_version() -> str:
    try:
        return importlib.metadata.version("ortools")
    except importlib.metadata.PackageNotFoundError:
        return "UNAVAILABLE"


def _scenario_inputs(problem: OptimizationProblem) -> tuple[ScenarioInputLineage, ...]:
    return tuple(
        ScenarioInputLineage(
            scenario_id=scenario.scenario_id,
            matrix_id=scenario.travel_matrix.matrix_id,
            graph_version=scenario.travel_matrix.graph_version,
            evidence_class=scenario.travel_matrix.evidence_class,
        )
        for scenario in sorted(problem.scenarios, key=lambda item: item.scenario_id)
    )


def _closed_result(
    problem: OptimizationProblem,
    *,
    status: OptimizationStatus,
    message: str,
) -> OptimizationResult:
    return OptimizationResult(
        problem_id=problem.problem_id,
        problem_fingerprint=problem_fingerprint(problem),
        graph_version=problem.scenarios[0].travel_matrix.graph_version,
        assumption_version=problem.objective_weights.assumption_version,
        scenario_inputs=_scenario_inputs(problem),
        status=status,
        action=OptimizationAction.NONE,
        fail_closed=True,
        solver_version=_solver_version(),
        random_seed=problem.solver_settings.random_seed,
        message=message,
    )


def optimize_facilities(problem: OptimizationProblem) -> OptimizationResult:
    """Solve in an isolated worker and verify its typed result lineage.

    OR-Tools and analytical libraries can load conflicting native runtimes in a
    long-lived API or test process. Isolation also lets a native crash or hard
    timeout become a typed fail-closed response instead of taking down the host.
    """

    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = "0"
    timeout = problem.solver_settings.max_time_seconds + _WORKER_STARTUP_GRACE_SECONDS
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "services.zonepilot.optimization._worker"],
            input=problem.model_dump_json(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return _closed_result(
            problem,
            status=OptimizationStatus.TIME_LIMIT,
            message="The isolated solver exceeded its hard process deadline; no decision is returned.",
        )
    if completed.returncode != 0:
        return _closed_result(
            problem,
            status=OptimizationStatus.SOLVER_ERROR,
            message="The isolated solver process failed; no decision is returned.",
        )
    try:
        result = OptimizationResult.model_validate_json(completed.stdout)
    except ValidationError:
        return _closed_result(
            problem,
            status=OptimizationStatus.SOLVER_ERROR,
            message="The isolated solver returned an invalid result contract; no decision is returned.",
        )
    expected_fingerprint = problem_fingerprint(problem)
    if result.problem_id != problem.problem_id or result.problem_fingerprint != expected_fingerprint:
        return _closed_result(
            problem,
            status=OptimizationStatus.SOLVER_ERROR,
            message="The isolated solver result did not match the requested problem lineage.",
        )
    return result
