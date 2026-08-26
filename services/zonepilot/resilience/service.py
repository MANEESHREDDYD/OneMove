"""Resilience Service coordinating scenario persistence and engine execution.

Order of operations is the fix for the orphan-row half of F-010. The service
used to write the scenario row and only then look for the authentic travel
matrix, so a ``MATRIX_UNAVAILABLE`` failure left a scenario in PostgreSQL with
nothing behind it. Now: validate, resolve the authentic matrix, freeze the
inputs, evaluate, and only then persist -- scenario and evaluation together, in
one transaction. A run that produced no result leaves no trace of having run.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from services.zonepilot.optimization.contracts import MatrixEvidenceClass, TravelMatrix
from services.zonepilot.optimization.r1_catalog import default_data_root
from services.zonepilot.resilience.contracts import (
    ResilienceMetrics,
    ResilienceScenario,
    ScenarioType,
)
from services.zonepilot.resilience.derivation import (
    ScenarioNotRepresentable,
    build_frozen_inputs,
)
from services.zonepilot.resilience.engine import ResilienceEngine
from services.zonepilot.resilience.repository import (
    IncompleteEvaluationError,
    ResilienceRepository,
)

__all__ = [
    "IncompleteEvaluationError",
    "ResilienceService",
    "ScenarioNotRepresentable",
    "UnknownScenarioType",
]


class UnknownScenarioType(ValueError):
    """The requested scenario type is not one this system can evaluate."""


def _authentic_baseline_matrix(graph_version: str = "1.1.0+bad320dd48da") -> TravelMatrix:
    """Load the authentic OSRM travel matrix, or fail closed.

    This function previously fabricated durations from an index arithmetic
    expression when the artifact was absent, and labelled the result
    evidence_class=PUBLIC_GEOGRAPHIC with matrix_id="matrix-canonical-r1" -- the
    same identifiers the authentic matrix uses. A resilience grade computed from
    invented travel times was therefore indistinguishable from a measured one and
    was persisted to PostgreSQL as if it were evidence (F-010).

    The optimization path already fails closed here and says so explicitly
    ("Failing closed without synthetic substitution"). This path now matches it.

    Simulation remains legitimate for the counterfactual disruption applied ON TOP
    of an authentic baseline; manufacturing the baseline itself is not.
    """
    mat_path = default_data_root() / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"
    if not mat_path.is_file():
        raise FileNotFoundError(
            "MATRIX_UNAVAILABLE: Authentic r1_osrm_travel_matrix.json is missing. "
            "Refusing to synthesize a baseline travel matrix; no resilience result will be produced."
        )

    doc = json.loads(mat_path.read_text(encoding="utf-8"))
    return TravelMatrix(
        matrix_id="matrix-canonical-r1",
        graph_version=doc.get("graph_version", graph_version),
        router=doc.get("router", "osrm-routed-table"),
        router_version=doc.get("router_version", "1.0.0"),
        evidence_class=MatrixEvidenceClass.PUBLIC_GEOGRAPHIC,
        facility_ids=tuple(doc["facility_ids"]),
        demand_ids=tuple(doc["demand_ids"]),
        durations_seconds=tuple(tuple(r) for r in doc["base_durations_seconds"]),
    )


def _compute_grade(metrics: ResilienceMetrics) -> str:
    """Grade the evaluation, or decline to grade it.

    A grade summarises coverage and p95 travel. If either is UNAVAILABLE there is
    nothing to summarise, and emitting the worst or best bucket would invent a
    judgement the data does not support.
    """
    coverage = metrics.coverage_basis_points
    p95 = metrics.p95_duration_seconds
    if coverage is None or p95 is None:
        return "UNAVAILABLE"
    if coverage >= 9500 and p95 <= 1200:
        return "ROBUST"
    if coverage >= 8500 and p95 <= 1800:
        return "MODERATE_DEGRADATION"
    if coverage >= 7000:
        return "SEVERE_DEGRADATION"
    return "CRITICAL_FAILURE"


class ResilienceService:
    def __init__(
        self,
        repository: ResilienceRepository | None = None,
        engine: ResilienceEngine | None = None,
    ) -> None:
        self.repository = repository or ResilienceRepository()
        self.engine = engine or ResilienceEngine()

    def execute_scenario(
        self,
        *,
        workspace_id: str,
        scenario_type: str,
        description: str = "",
        parameters: dict[str, Any] | None = None,
        seed: int = 42,
        graph_version: str = "1.1",
        created_by: str | None = None,
        baseline_matrix: TravelMatrix | None = None,
        code_sha: str | None = None,
    ) -> dict[str, Any]:
        """Execute a resilience failure scenario, evaluate metrics, and persist.

        Nothing is written until a complete, derived evaluation exists. Every
        failure mode below -- unknown scenario type, missing authentic matrix,
        a disruption that cannot be expressed against that matrix, or a metric
        that could not be derived -- raises before the first INSERT.
        """
        # 1. Validate the request. An unrecognised scenario type used to be
        #    silently rewritten to ROAD_CLOSURE while the caller's original
        #    string was persisted, so the stored type and the evaluated type
        #    disagreed.
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("execute_scenario requires a non-empty workspace_id")
        try:
            resolved_type = ScenarioType(scenario_type)
        except ValueError as exc:
            supported = sorted(member.value for member in ScenarioType)
            raise UnknownScenarioType(f"unsupported scenario_type {scenario_type!r}; supported: {supported}") from exc

        params = dict(parameters or {})
        h = hashlib.sha256(f"{workspace_id}:{scenario_type}:{description}:{seed}".encode()).hexdigest()[:12]
        scenario_id = f"scen-{h}"
        desc = description or f"Scenario {resolved_type.value}"

        res_scen = ResilienceScenario(
            scenario_id=scenario_id,
            scenario_type=resolved_type,
            description=desc,
            parameters=params,
            seed=seed,
            graph_version=graph_version,
        )

        # 2. Resolve the authentic routing base (PUBLIC_GEOGRAPHIC). Raises
        #    FileNotFoundError when absent, before anything is persisted.
        base_mat = baseline_matrix or _authentic_baseline_matrix(graph_version)

        # 3. Freeze the inputs: authentic matrix + SIMULATED disruption +
        #    declared assumptions. Raises ScenarioNotRepresentable when the
        #    requested disruption cannot be applied to that matrix.
        inputs = build_frozen_inputs(base_mat, scenario_type=resolved_type, parameters=params)

        # 4. Evaluate. Every metric is DERIVED from the frozen inputs or is
        #    reported UNAVAILABLE with a reason.
        engine = self.engine if code_sha is None else ResilienceEngine(code_sha=code_sha)
        res_eval = engine.evaluate_scenario(res_scen, inputs)
        metrics = res_eval.metrics
        grade = _compute_grade(metrics)

        # 5. Persist scenario + evaluation in one transaction, or not at all.
        self.repository.save_evaluation(
            scenario_id=scenario_id,
            workspace_id=workspace_id,
            scenario_type=resolved_type.value,
            description=desc,
            parameters=params,
            seed=seed,
            graph_version=graph_version,
            created_by=created_by,
            evaluation_id=res_eval.evaluation_id,
            metrics=metrics,
            degradation_grade=grade,
            code_sha=res_eval.code_sha,
            evidence_class=res_scen.evidence_class.value,
        )

        stored = self.repository.get_scenario(scenario_id, workspace_id) or {}
        stored["derivation"] = res_eval.inputs.lineage()
        stored["metrics_evidence_class"] = metrics.evidence_class.value
        stored["unavailable_metrics"] = metrics.unavailable_reasons()
        return stored

    def get_scenario(self, scenario_id: str, workspace_id: str | None = None) -> dict[str, Any] | None:
        """Fetch scenario and evaluated metrics from PostgreSQL."""
        return self.repository.get_scenario(scenario_id, workspace_id)

    def list_scenarios(self, workspace_id: str) -> list[dict[str, Any]]:
        """List all workspace scenarios from PostgreSQL."""
        return self.repository.list_scenarios(workspace_id)
