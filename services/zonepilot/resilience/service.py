"""Resilience Service coordinating scenario persistence and engine execution."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from services.zonepilot.optimization.contracts import MatrixEvidenceClass, TravelMatrix
from services.zonepilot.optimization.r1_catalog import default_data_root
from services.zonepilot.release import current_release_sha
from services.zonepilot.resilience.contracts import (
    ResilienceScenario,
    ScenarioType,
)
from services.zonepilot.resilience.engine import ResilienceEngine
from services.zonepilot.resilience.repository import ResilienceRepository


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


def _compute_grade(metrics: Any) -> str:
    if metrics.coverage_basis_points >= 9500 and metrics.p95_duration_seconds <= 1200:
        return "ROBUST"
    elif metrics.coverage_basis_points >= 8500 and metrics.p95_duration_seconds <= 1800:
        return "MODERATE_DEGRADATION"
    elif metrics.coverage_basis_points >= 7000:
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
        """Execute a resilience failure scenario, evaluate metrics, and persist to PostgreSQL."""
        effective_code_sha = code_sha or current_release_sha()
        h = hashlib.sha256(f"{workspace_id}:{scenario_type}:{description}:{seed}".encode()).hexdigest()[:12]
        scenario_id = f"scen-{h}"
        eval_id = f"eval-{h}"
        desc = description or f"Scenario {scenario_type}"

        # 1. Save scenario definition
        self.repository.save_scenario(
            scenario_id=scenario_id,
            workspace_id=workspace_id,
            scenario_type=scenario_type,
            description=desc,
            evidence_class="SIMULATED",
            parameters=parameters,
            seed=seed,
            graph_version=graph_version,
            created_by=created_by,
        )

        # 2. Execute resilience engine
        base_mat = baseline_matrix or _authentic_baseline_matrix(graph_version)
        st = (
            ScenarioType(scenario_type)
            if scenario_type in ScenarioType._value2member_map_
            else ScenarioType.ROAD_CLOSURE
        )
        res_scen = ResilienceScenario(
            scenario_id=scenario_id,
            scenario_type=st,
            description=desc,
            parameters=parameters or {},
            seed=seed,
            graph_version=graph_version,
        )

        flat_durations = [int(dur) for row in base_mat.durations_seconds for dur in row]
        res_eval = self.engine.evaluate_scenario(res_scen, flat_durations)
        m = res_eval.metrics
        grade = _compute_grade(m)

        # 3. Save result to PostgreSQL
        self.repository.save_result(
            evaluation_id=eval_id,
            scenario_id=scenario_id,
            workspace_id=workspace_id,
            coverage_basis_points=m.coverage_basis_points,
            p50_duration_seconds=m.p50_duration_seconds,
            p90_duration_seconds=m.p90_duration_seconds,
            p95_duration_seconds=m.p95_duration_seconds,
            disconnected_zones_count=m.disconnected_zones_count,
            redundancy_index_basis_points=m.redundancy_index_basis_points,
            failure_exposure_score=m.failure_exposure_score,
            capacity_loss_basis_points=m.capacity_loss_basis_points,
            degradation_grade=grade,
            baseline_comparison=None,
            code_sha=effective_code_sha,
        )

        return self.repository.get_scenario(scenario_id, workspace_id) or {}

    def get_scenario(self, scenario_id: str, workspace_id: str | None = None) -> dict[str, Any] | None:
        """Fetch scenario and evaluated metrics from PostgreSQL."""
        return self.repository.get_scenario(scenario_id, workspace_id)

    def list_scenarios(self, workspace_id: str) -> list[dict[str, Any]]:
        """List all workspace scenarios from PostgreSQL."""
        return self.repository.list_scenarios(workspace_id)
