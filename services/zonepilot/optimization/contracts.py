"""Strict, versioned contracts for deterministic facility optimization.

The optimizer consumes routed-network travel matrices supplied by an upstream
adapter.  It never invents straight-line distances or calls a routing provider.
Scenario evidence remains explicit so simulated failures cannot be mistaken for
observed outcomes.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BASIS_POINTS = 10_000
P95_BASIS_POINTS = 9_500
MAX_TRAVEL_SECONDS = 7 * 24 * 60 * 60
MAX_COEFFICIENT = 1_000_000_000
MAX_SAFE_OBJECTIVE = 2**62


class StrictContract(BaseModel):
    """Reject unknown fields, implicit coercion, and mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("identifier must not be blank")
    return value


class MatrixEvidenceClass(str, Enum):
    """Evidence attached to a routed network matrix."""

    OBSERVED_CURRENT_STATE = "OBSERVED_CURRENT_STATE"
    PUBLIC_GEOGRAPHIC = "PUBLIC_GEOGRAPHIC"
    PROVIDER_ESTIMATED = "PROVIDER_ESTIMATED"
    SIMULATED_FAILURE = "SIMULATED_FAILURE"
    SIMULATED = "SIMULATED"
    DERIVED = "DERIVED"
    TEST_ONLY = "TEST_ONLY"


class OptimizationStatus(str, Enum):
    OPTIMAL = "OPTIMAL"
    INFEASIBLE = "INFEASIBLE"
    TIME_LIMIT = "TIME_LIMIT"
    MODEL_INVALID = "MODEL_INVALID"
    SOLVER_ERROR = "SOLVER_ERROR"


class OptimizationAction(str, Enum):
    OPEN_FACILITIES = "OPEN_FACILITIES"
    NO_ACTION = "NO_ACTION"
    NONE = "NONE"


class Facility(StrictContract):
    facility_id: str = Field(min_length=1)
    capacity_units: int = Field(gt=0, le=MAX_COEFFICIENT)
    fixed_cost_units: int = Field(ge=0, le=MAX_COEFFICIENT)
    failure_exposure_basis_points: int = Field(ge=0, le=BASIS_POINTS)

    @field_validator("facility_id")
    @classmethod
    def identifier_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class DemandPoint(StrictContract):
    demand_id: str = Field(min_length=1)
    demand_units: int = Field(gt=0, le=MAX_COEFFICIENT)

    @field_validator("demand_id")
    @classmethod
    def identifier_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class TravelMatrix(StrictContract):
    """Finite routed-network durations quantized to integer seconds."""

    schema_name: Literal["zonepilot.routed_travel_matrix"] = "zonepilot.routed_travel_matrix"
    schema_version: Literal["1.0.0"] = "1.0.0"
    matrix_id: str = Field(min_length=1)
    graph_version: str = Field(min_length=1)
    router: str = Field(min_length=1)
    router_version: str = Field(min_length=1)
    source_kind: Literal["ROUTED_NETWORK"] = "ROUTED_NETWORK"
    evidence_class: MatrixEvidenceClass
    unit: Literal["seconds"] = "seconds"
    quantization: Literal["CEIL_TO_INTEGER_SECOND"] = "CEIL_TO_INTEGER_SECOND"
    facility_ids: tuple[str, ...] = Field(min_length=1, max_length=200)
    demand_ids: tuple[str, ...] = Field(min_length=1, max_length=2_000)
    durations_seconds: tuple[tuple[int, ...], ...]
    parent_matrix_id: str | None = None

    @field_validator("matrix_id", "graph_version", "router", "router_version")
    @classmethod
    def identifiers_are_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("facility_ids", "demand_ids")
    @classmethod
    def matrix_axis_ids_are_unique_and_named(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("matrix axis identifiers must not be blank")
        if len(values) != len(set(values)):
            raise ValueError("matrix axis identifiers must be unique")
        return values

    @model_validator(mode="after")
    def matrix_is_rectangular_and_finite(self) -> Self:
        if len(self.durations_seconds) != len(self.facility_ids):
            raise ValueError("travel matrix must contain one row per facility_id")
        for row in self.durations_seconds:
            if len(row) != len(self.demand_ids):
                raise ValueError("travel matrix rows must contain one duration per demand_id")
            if any(duration < 0 or duration > MAX_TRAVEL_SECONDS for duration in row):
                raise ValueError(f"travel durations must be between 0 and {MAX_TRAVEL_SECONDS} seconds")
        return self


class FacilityCapacityAdjustment(StrictContract):
    facility_id: str = Field(min_length=1)
    available_capacity_basis_points: int = Field(ge=0, le=BASIS_POINTS)

    @field_validator("facility_id")
    @classmethod
    def identifier_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class UncertaintyScenario(StrictContract):
    scenario_id: str = Field(min_length=1)
    probability_basis_points: int = Field(gt=0, le=BASIS_POINTS)
    travel_matrix: TravelMatrix
    capacity_adjustments: tuple[FacilityCapacityAdjustment, ...] = ()

    @field_validator("scenario_id")
    @classmethod
    def identifier_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @model_validator(mode="after")
    def capacity_adjustments_are_unique(self) -> Self:
        ids = [adjustment.facility_id for adjustment in self.capacity_adjustments]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario capacity adjustments must contain unique facility_id values")
        return self


class OptimizationConstraints(StrictContract):
    min_open_facilities: int = Field(ge=0, le=200)
    max_open_facilities: int = Field(gt=0, le=200)
    max_travel_seconds: int = Field(gt=0, le=MAX_TRAVEL_SECONDS)
    minimum_coverage_basis_points: int = Field(ge=0, le=BASIS_POINTS)
    allow_uncovered_demand: bool = False
    allow_no_action: bool = False
    max_total_fixed_cost_units: int | None = Field(default=None, ge=0, le=MAX_COEFFICIENT)

    @model_validator(mode="after")
    def bounds_are_coherent(self) -> Self:
        if self.min_open_facilities > self.max_open_facilities:
            raise ValueError("min_open_facilities must not exceed max_open_facilities")
        if not self.allow_no_action and self.min_open_facilities == 0:
            raise ValueError("min_open_facilities must be positive unless allow_no_action is true")
        return self


class ObjectiveWeights(StrictContract):
    assumption_version: str = Field(min_length=1)
    expected_travel: int = Field(ge=0, le=MAX_COEFFICIENT)
    p95_travel: int = Field(ge=0, le=MAX_COEFFICIENT)
    facility_cost: int = Field(ge=0, le=MAX_COEFFICIENT)
    failure_exposure: int = Field(ge=0, le=MAX_COEFFICIENT)
    coverage_loss: int = Field(ge=0, le=MAX_COEFFICIENT)

    @field_validator("assumption_version")
    @classmethod
    def version_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @model_validator(mode="after")
    def at_least_one_weight_is_active(self) -> Self:
        if not any(
            (
                self.expected_travel,
                self.p95_travel,
                self.facility_cost,
                self.failure_exposure,
                self.coverage_loss,
            )
        ):
            raise ValueError("at least one objective weight must be positive")
        return self


class SolverSettings(StrictContract):
    max_time_seconds: float = Field(default=30.0, gt=0.0, le=300.0)
    random_seed: int = Field(default=0, ge=0, le=2_147_483_647)
    num_search_workers: Literal[1] = 1


class OptimizationProblem(StrictContract):
    schema_name: Literal["zonepilot.facility_optimization_problem"] = "zonepilot.facility_optimization_problem"
    schema_version: Literal["1.0.0"] = "1.0.0"
    problem_id: str = Field(min_length=1)
    facilities: tuple[Facility, ...] = Field(min_length=1, max_length=200)
    demand_points: tuple[DemandPoint, ...] = Field(min_length=1, max_length=2_000)
    scenarios: tuple[UncertaintyScenario, ...] = Field(min_length=1, max_length=100)
    constraints: OptimizationConstraints
    objective_weights: ObjectiveWeights
    solver_settings: SolverSettings = SolverSettings()

    @field_validator("problem_id")
    @classmethod
    def identifier_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @model_validator(mode="after")
    def cross_contract_invariants_hold(self) -> Self:
        facility_ids = tuple(facility.facility_id for facility in self.facilities)
        demand_ids = tuple(demand.demand_id for demand in self.demand_points)
        scenario_ids = tuple(scenario.scenario_id for scenario in self.scenarios)
        if len(facility_ids) != len(set(facility_ids)):
            raise ValueError("facility_id values must be unique")
        if len(demand_ids) != len(set(demand_ids)):
            raise ValueError("demand_id values must be unique")
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("scenario_id values must be unique")
        if sum(scenario.probability_basis_points for scenario in self.scenarios) != BASIS_POINTS:
            raise ValueError(f"scenario probabilities must sum to {BASIS_POINTS} basis points")
        if self.constraints.max_open_facilities > len(self.facilities):
            raise ValueError("max_open_facilities must not exceed the number of facilities")
        if self.constraints.min_open_facilities > len(self.facilities):
            raise ValueError("min_open_facilities must not exceed the number of facilities")

        expected_facilities = set(facility_ids)
        expected_demands = set(demand_ids)
        graph_versions: set[str] = set()
        max_scenario_travel = 0
        total_demand = sum(demand.demand_units for demand in self.demand_points)
        facility_by_id = {facility.facility_id: facility for facility in self.facilities}
        for scenario in self.scenarios:
            matrix = scenario.travel_matrix
            if set(matrix.facility_ids) != expected_facilities:
                raise ValueError("every scenario matrix must contain exactly the problem facility_ids")
            if set(matrix.demand_ids) != expected_demands:
                raise ValueError("every scenario matrix must contain exactly the problem demand_ids")
            graph_versions.add(matrix.graph_version)
            adjustment_ids = {adjustment.facility_id for adjustment in scenario.capacity_adjustments}
            if not adjustment_ids <= expected_facilities:
                raise ValueError("scenario capacity adjustments must reference known facilities")
            max_duration = max(max(row) for row in matrix.durations_seconds)
            scenario_travel = total_demand * max_duration
            max_scenario_travel = max(max_scenario_travel, scenario_travel)
        if len(graph_versions) != 1:
            raise ValueError("all scenario matrices must use the same graph_version")

        expected_upper = BASIS_POINTS * max_scenario_travel
        p95_upper = BASIS_POINTS * max_scenario_travel
        cost_upper = BASIS_POINTS * sum(facility.fixed_cost_units for facility in self.facilities)
        exposure_upper = sum(
            facility.capacity_units * facility.failure_exposure_basis_points for facility in facility_by_id.values()
        )
        coverage_upper = BASIS_POINTS * total_demand
        weighted_upper = (
            self.objective_weights.expected_travel * expected_upper
            + self.objective_weights.p95_travel * p95_upper
            + self.objective_weights.facility_cost * cost_upper
            + self.objective_weights.failure_exposure * exposure_upper
            + self.objective_weights.coverage_loss * coverage_upper
        )
        if weighted_upper > MAX_SAFE_OBJECTIVE:
            raise ValueError("objective coefficients exceed the deterministic int64 safety bound")
        return self


class ScenarioAssignment(StrictContract):
    scenario_id: str
    facility_id: str
    demand_id: str
    assigned_demand_units: int
    travel_seconds: int


class ScenarioMetrics(StrictContract):
    scenario_id: str
    probability_basis_points: int
    covered_demand_units: int
    uncovered_demand_units: int
    coverage_basis_points: int
    total_travel_demand_seconds: int


class ScenarioInputLineage(StrictContract):
    scenario_id: str
    matrix_id: str
    graph_version: str
    evidence_class: MatrixEvidenceClass


class ObjectiveBreakdown(StrictContract):
    weights: ObjectiveWeights
    expected_travel_probability_demand_seconds: int
    p95_travel_demand_seconds: int
    facility_cost_units: int
    failure_exposure_capacity_basis_points: int
    expected_uncovered_probability_demand_units: int
    weighted_total: int


class OptimizationResult(StrictContract):
    schema_name: Literal["zonepilot.facility_optimization_result"] = "zonepilot.facility_optimization_result"
    schema_version: Literal["1.0.0"] = "1.0.0"
    problem_id: str
    problem_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    graph_version: str
    assumption_version: str
    scenario_inputs: tuple[ScenarioInputLineage, ...]
    status: OptimizationStatus
    action: OptimizationAction
    fail_closed: bool
    opened_facility_ids: tuple[str, ...] = ()
    assignments: tuple[ScenarioAssignment, ...] = ()
    scenario_metrics: tuple[ScenarioMetrics, ...] = ()
    objective: ObjectiveBreakdown | None = None
    solver: Literal["OR_TOOLS_CP_SAT"] = "OR_TOOLS_CP_SAT"
    solver_version: str
    random_seed: int
    num_search_workers: Literal[1] = 1
    message: str

    @model_validator(mode="after")
    def result_is_fail_closed_unless_optimal(self) -> Self:
        if self.status is OptimizationStatus.OPTIMAL:
            if self.fail_closed or self.action is OptimizationAction.NONE or self.objective is None:
                raise ValueError("optimal results must contain a proved decision and objective")
            return self
        if not self.fail_closed:
            raise ValueError("non-optimal results must be fail_closed")
        if self.action is not OptimizationAction.NONE:
            raise ValueError("non-optimal results must not claim an action")
        if self.opened_facility_ids or self.assignments or self.scenario_metrics or self.objective is not None:
            raise ValueError("non-optimal results must not expose unproved decisions or metrics")
        return self


def problem_fingerprint(problem: OptimizationProblem) -> str:
    """Return a stable content hash for exact-input lineage."""

    payload = problem.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ProblemSnapshot(StrictContract):
    """Immutable, cryptographically verifiable snapshot of an optimization problem."""

    schema_name: Literal["zonepilot.optimization_problem_snapshot"] = "zonepilot.optimization_problem_snapshot"
    schema_version: Literal["1.0.0"] = "1.0.0"
    problem_snapshot_id: str
    problem_snapshot_sha256: str
    created_at: str
    code_sha: str
    dataset_version: str
    graph_version: str
    assumption_version: str
    solver_version: str
    matrix_sha256: str
    gold_manifest_sha256: str
    problem: OptimizationProblem
    evidence_ids: tuple[str, ...]
    temporal_cutoff: str


def create_problem_snapshot(
    problem: OptimizationProblem,
    *,
    code_sha: str,
    dataset_version: str,
    matrix_sha256: str,
    gold_manifest_sha256: str,
    evidence_ids: tuple[str, ...],
    temporal_cutoff: str | None = None,
) -> ProblemSnapshot:
    """Construct an immutable, canonical problem snapshot with cryptographic SHA-256."""
    from datetime import datetime, timezone

    canonical_sha = problem_fingerprint(problem)
    snap_id = f"psnap-{canonical_sha[:16]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    return ProblemSnapshot(
        problem_snapshot_id=snap_id,
        problem_snapshot_sha256=canonical_sha,
        created_at=now_iso,
        code_sha=code_sha,
        dataset_version=dataset_version,
        graph_version=problem.scenarios[0].travel_matrix.graph_version if problem.scenarios else "1.1",
        assumption_version=problem.objective_weights.assumption_version,
        solver_version="ortools-cp-sat",
        matrix_sha256=matrix_sha256,
        gold_manifest_sha256=gold_manifest_sha256,
        problem=problem,
        evidence_ids=evidence_ids,
        temporal_cutoff=temporal_cutoff or now_iso,
    )

