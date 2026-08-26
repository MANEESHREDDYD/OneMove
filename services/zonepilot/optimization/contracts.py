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

from services.temporal.contracts import EvidenceClass

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


class CapacityMode(str, Enum):
    """Whether facility throughput is modelled at all.

    The public-data model has no defensible throughput dataset: demand is a
    PUBLIC_GEOGRAPHIC proxy (commercial POI counts), not orders. Constraining it
    with an invented per-facility capacity produced a binding constraint that
    made full service arithmetically impossible while looking like a real
    operating limit. NOT_MODELED says so out loud.
    """

    NOT_MODELED = "NOT_MODELED"
    ASSUMPTION = "ASSUMPTION"


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
    capacity_mode: CapacityMode = CapacityMode.NOT_MODELED
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
    """Solver configuration. Part of the problem fingerprint.

    ``num_search_workers`` was pinned to 1 because reproducibility was assumed
    to require single-threaded search. It does not: the decision is made
    reproducible by canonical assignment reconstruction and a lexicographic
    facility tie-break, neither of which depends on how the optimum was found.
    Parallel search is therefore used only to PROVE the optimum, which it does
    in roughly 0.4s where a single worker could not close a 74.7% gap in 300s.

    The value stays in the fingerprint so a decision records how it was solved.
    """

    max_time_seconds: float = Field(default=30.0, gt=0.0, le=300.0)
    random_seed: int = Field(default=0, ge=0, le=2_147_483_647)
    num_search_workers: int = Field(default=8, ge=1, le=32)


# The mathematical policy the problem is solved under. Bump this whenever the
# meaning of the objective, the constraint semantics, or the assignment rule
# changes -- not for additive fields. It is part of the problem fingerprint, so a
# decision frozen under one policy can never be silently replayed under another.
#
#   1.0.0  original: capacity always bound; objective summed raw units of
#          different dimensions; assignments read from the solver.
#   2.0.0  capacity_mode (NOT_MODELED default); objective components normalised
#          against declared references before weighting; assignments
#          canonically reconstructed when capacity is not modelled.
OPTIMIZATION_POLICY_VERSION = "2.0.0"


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
    optimization_policy_version: str = OPTIMIZATION_POLICY_VERSION

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


class ObjectiveComponent(StrictContract):
    """One objective term, from raw measurement to weighted contribution.

    Components used to be summed in their native units -- demand-unit-seconds
    added to a unit-less uncovered count -- so a weight of 5000 on each meant
    abandoning a zone cost about the same as one second of service. Each term is
    now divided by a declared reference to become dimensionless basis points
    before any weight is applied, and every step is published so the total can
    be reconciled by hand.
    """

    name: str
    raw_value: int
    raw_unit: str
    normalization_reference: int
    normalization_reference_unit: str
    weight: int

    # The exact integer coefficient CP-SAT multiplied this component by, and the
    # contribution it actually made to the minimised objective. These are the
    # authoritative numbers: summing solver_scaled_contribution reproduces the
    # value the solver ranked solutions by.
    solver_coefficient: int
    solver_scaled_contribution: int

    # Human-facing projection. Flooring happens at a different point from the
    # solver path, so this is NOT the optimisation value -- across 400k random
    # trials the two paths disagreed on every value and inverted the ordering of
    # two solutions 13 times. It is published for readability and explicitly
    # labelled as a projection so it can never be mistaken for the objective.
    normalized_basis_points: int
    weighted_contribution: int

    evidence_class: str = "DERIVED"


class ObjectiveBreakdown(StrictContract):
    weights: ObjectiveWeights
    expected_travel_probability_demand_seconds: int
    p95_travel_demand_seconds: int
    facility_cost_units: int
    failure_exposure_capacity_basis_points: int
    expected_uncovered_probability_demand_units: int
    weighted_total: int
    components: tuple[ObjectiveComponent, ...] = ()
    normalization_scale: int = 0
    # Fixed-point scale applied to the solver coefficients.
    solver_scale: int = 0
    # sum(component.solver_scaled_contribution). This is the quantity CP-SAT
    # minimised, and the one a reviewer should reconcile against.
    solver_objective_total: int = 0


# ---------------------------------------------------------------------------
# DO-NOTHING BASELINE
# ---------------------------------------------------------------------------
#
# WHAT THE BASELINE IS
# --------------------
# The DO_NOTHING baseline is the INCUMBENT FACILITY SET -- the sites the network
# already operates -- scored by the *identical* objective the solver minimised:
#
#   * the same ``OptimizationProblem``: the same demand points and demand units,
#     the same candidate facility ledger (capacity, fixed cost, failure
#     exposure), the same constraints;
#   * the same scenarios, with the same probabilities and the same travel
#     matrices (same ``graph_version``, same router, same matrix ids);
#   * the same ``ObjectiveWeights``, and therefore the same
#     ``assumption_version``;
#   * the same ``optimization_policy_version``: the same normalisation
#     references, the same ``FIXED_POINT`` scale, the same assignment rule.
#
# Exactly ONE thing differs between the two sides: which facilities are open.
# That is what makes the difference attributable to the recommendation rather
# than to a changed yardstick.
#
# WHY IT IS AN INPUT AND NOT SOMETHING WE DERIVE
# ----------------------------------------------
# R1 contains no facility ledger. ``r1_network`` says so in its own module
# docstring: capacity, fixed cost and failure exposure are geographic proxies,
# and the twelve "facilities" in the pilot are CANDIDATE SITES ranked by
# commercial POI density, not operating depots. Nothing in the Gold artifacts,
# the OSRM bundle, or ``supabase/migrations`` records which sites are open
# today.
#
# Inventing an incumbent set -- "the four cheapest", "the four most central" --
# would manufacture the very number the comparison exists to test, and would
# turn the reported improvement into a statement about our own guess. So the
# baseline is an OPTIONAL INPUT the caller supplies, and when it is absent the
# comparison is published as UNAVAILABLE with a machine-readable reason. It is
# never reported as zero and never silently dropped: a reader who sees no
# improvement figure is told exactly why there is none.
#
# The comparison itself is DERIVED -- computed from a declared input and a
# solved result by the same arithmetic. It observes nothing.


class BaselineEvaluationStatus(str, Enum):
    """Whether a do-nothing comparison could be computed at all."""

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class BaselineUnavailableReason(str, Enum):
    """Why no do-nothing comparison exists. Always paired with a message."""

    # No incumbent set was supplied, and none can be derived from R1 artifacts.
    NO_BASELINE_SUPPLIED = "NO_BASELINE_SUPPLIED"
    # The solve produced no proved recommendation, so there is no right-hand
    # side to compare against.
    NO_RECOMMENDATION = "NO_RECOMMENDATION"
    # The supplied set names facilities this problem does not contain, so they
    # have no row in the travel matrix and cannot be scored.
    UNKNOWN_FACILITY_IDS = "UNKNOWN_FACILITY_IDS"
    # Under CapacityMode.ASSUMPTION the per-zone assignments are coupled through
    # a per-facility throughput limit, so the canonical nearest-facility rule is
    # explicitly not valid (see ``_cp_sat._canonical_assignment``). Allocating
    # the incumbent network's load would mean choosing an operating policy
    # nobody has stated, so the comparison is withheld rather than guessed.
    CAPACITY_MODE_COUPLES_ASSIGNMENTS = "CAPACITY_MODE_COUPLES_ASSIGNMENTS"
    # The stored result predates this contract.
    NOT_RECORDED = "NOT_RECORDED"


class DoNothingBaseline(StrictContract):
    """The incumbent facility set a recommendation is judged against. INPUT.

    ``facility_ids`` may legitimately be empty: a greenfield network where doing
    nothing serves nobody is a real baseline, and it scores as total coverage
    loss rather than as a missing comparison. Every id must exist in the problem
    so that the same travel matrix rows are used on both sides.

    ``source`` and ``evidence_class`` are required because an incumbent set with
    no stated provenance is exactly the kind of unsourced number this contract
    exists to keep out. Nothing here is defaulted or inferred.
    """

    schema_name: Literal["zonepilot.do_nothing_baseline"] = "zonepilot.do_nothing_baseline"
    schema_version: Literal["1.0.0"] = "1.0.0"
    baseline_id: str = Field(min_length=1)
    facility_ids: tuple[str, ...] = Field(default=(), max_length=200)
    source: str = Field(min_length=1)
    evidence_class: EvidenceClass
    as_of: str | None = None

    @field_validator("baseline_id", "source")
    @classmethod
    def identifier_is_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("facility_ids")
    @classmethod
    def facility_ids_are_unique_and_named(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("baseline facility identifiers must not be blank")
        if len(values) != len(set(values)):
            raise ValueError("baseline facility identifiers must be unique")
        return values


class BaselinePolicyViolation(str, Enum):
    """A way the incumbent set breaks the request's own policy envelope.

    A violation is REPORTED, never a rejection. The network as it stands today
    is a fact; that a request would not be permitted to PROPOSE it says
    something about the request, not about whether the fact can be measured.
    """

    ABOVE_MAX_OPEN_FACILITIES = "ABOVE_MAX_OPEN_FACILITIES"
    BELOW_MIN_OPEN_FACILITIES = "BELOW_MIN_OPEN_FACILITIES"
    ABOVE_MAX_TOTAL_FIXED_COST = "ABOVE_MAX_TOTAL_FIXED_COST"


class BaselineInfeasibility(str, Enum):
    """A service commitment the incumbent set fails to meet."""

    UNCOVERED_DEMAND_NOT_PERMITTED = "UNCOVERED_DEMAND_NOT_PERMITTED"
    BELOW_MINIMUM_COVERAGE = "BELOW_MINIMUM_COVERAGE"


class ObjectiveComponentDelta(StrictContract):
    """One objective component, on both sides, in the solver's own integers.

    ``solver_scaled_delta`` is ``recommended - baseline``: NEGATIVE means the
    recommendation improves this component. The same integer coefficient applies
    to both sides -- the normalisation references depend only on the problem,
    never on which facilities are open -- so the component deltas sum EXACTLY to
    the total delta, with no rounding residue to absorb.
    """

    name: str
    raw_unit: str
    solver_coefficient: int
    baseline_raw_value: int
    recommended_raw_value: int
    baseline_solver_scaled_contribution: int
    recommended_solver_scaled_contribution: int
    solver_scaled_delta: int
    evidence_class: Literal["DERIVED"] = "DERIVED"

    @model_validator(mode="after")
    def delta_reconciles_with_its_own_sides(self) -> Self:
        if self.baseline_solver_scaled_contribution != self.solver_coefficient * self.baseline_raw_value:
            raise ValueError("baseline contribution is not coefficient * raw value")
        if self.recommended_solver_scaled_contribution != self.solver_coefficient * self.recommended_raw_value:
            raise ValueError("recommended contribution is not coefficient * raw value")
        expected = self.recommended_solver_scaled_contribution - self.baseline_solver_scaled_contribution
        if self.solver_scaled_delta != expected:
            raise ValueError("solver_scaled_delta is not recommended minus baseline")
        return self


class BaselineComparison(StrictContract):
    """What the recommendation is better THAN -- or why that cannot be said.

    Sign conventions, stated once:

    * ``total_solver_scaled_delta`` and every ``component_deltas`` entry are
      ``recommended - baseline``. Negative is an improvement.
    * ``absolute_improvement`` is ``baseline - recommended``. Positive is an
      improvement. It is exactly ``-total_solver_scaled_delta``; both are
      published because reversing a sign in the reader's head is how a
      regression gets reported as a win.

    Coverage is reported for the WORST scenario on each side -- the binding one
    for any service commitment, and the same statistic the read path already
    reports -- so an "improvement" bought by abandoning zones appears as a
    negative ``coverage_delta_basis_points`` beside the positive objective
    delta instead of hiding inside it.
    """

    schema_name: Literal["zonepilot.do_nothing_baseline_comparison"] = (
        "zonepilot.do_nothing_baseline_comparison"
    )
    schema_version: Literal["1.0.0"] = "1.0.0"

    status: BaselineEvaluationStatus
    unavailable_reason: BaselineUnavailableReason | None = None
    message: str = Field(min_length=1)
    # The comparison observes nothing; it is arithmetic over a declared input
    # and a solved result.
    evidence_class: Literal["DERIVED"] = "DERIVED"

    baseline: DoNothingBaseline | None = None

    # Conformance of the SUPPLIED set: evaluated and reported, never enforced.
    baseline_within_policy: bool | None = None
    baseline_policy_violations: tuple[BaselinePolicyViolation, ...] = ()
    baseline_feasible: bool | None = None
    baseline_infeasibilities: tuple[BaselineInfeasibility, ...] = ()

    baseline_facility_ids: tuple[str, ...] = ()
    baseline_open_facility_count: int | None = None
    recommended_facility_ids: tuple[str, ...] = ()
    recommended_open_facility_count: int | None = None

    baseline_solver_objective_total: int | None = None
    recommended_solver_objective_total: int | None = None
    total_solver_scaled_delta: int | None = None
    absolute_improvement: int | None = None
    improvement_basis_points: int | None = None
    improvement_basis_points_unavailable_reason: str | None = None
    component_deltas: tuple[ObjectiveComponentDelta, ...] = ()

    baseline_coverage_basis_points: int | None = None
    recommended_coverage_basis_points: int | None = None
    coverage_delta_basis_points: int | None = None
    baseline_uncovered_demand_units: int | None = None
    recommended_uncovered_demand_units: int | None = None
    baseline_scenario_metrics: tuple[ScenarioMetrics, ...] = ()

    # The yardstick both sides were measured with. If any of these differs from
    # the result's own lineage, the comparison is not like-for-like.
    optimization_policy_version: str | None = None
    assumption_version: str | None = None
    graph_version: str | None = None
    solver_scale: int | None = None

    @model_validator(mode="after")
    def unavailable_is_never_reported_as_zero(self) -> Self:
        numeric = (
            self.baseline_solver_objective_total,
            self.recommended_solver_objective_total,
            self.total_solver_scaled_delta,
            self.absolute_improvement,
            self.baseline_coverage_basis_points,
            self.recommended_coverage_basis_points,
        )
        if self.status is BaselineEvaluationStatus.UNAVAILABLE:
            if self.unavailable_reason is None:
                raise ValueError("an UNAVAILABLE comparison must name its reason")
            if any(value is not None for value in numeric):
                raise ValueError(
                    "an UNAVAILABLE comparison must not publish figures; a missing "
                    "comparison reported as a number is indistinguishable from a real one"
                )
            if self.component_deltas:
                raise ValueError("an UNAVAILABLE comparison must not publish component deltas")
            return self

        if self.unavailable_reason is not None:
            raise ValueError("an AVAILABLE comparison must not name an unavailability reason")
        if any(value is None for value in numeric):
            raise ValueError("an AVAILABLE comparison must publish every headline figure")
        if self.baseline is None:
            raise ValueError("an AVAILABLE comparison must publish the baseline it used")
        if not self.component_deltas:
            raise ValueError("an AVAILABLE comparison must publish its component deltas")

        baseline_total = self.baseline_solver_objective_total
        recommended_total = self.recommended_solver_objective_total
        total_delta = self.total_solver_scaled_delta
        baseline_coverage = self.baseline_coverage_basis_points
        recommended_coverage = self.recommended_coverage_basis_points
        assert baseline_total is not None
        assert recommended_total is not None
        assert total_delta is not None
        assert baseline_coverage is not None
        assert recommended_coverage is not None

        # The reconciliation a reviewer would do by hand, enforced by the type.
        component_sum = sum(delta.solver_scaled_delta for delta in self.component_deltas)
        if component_sum != total_delta:
            raise ValueError(
                f"component deltas sum to {component_sum} but the total delta is "
                f"{total_delta}; the breakdown does not reconcile"
            )
        if total_delta != recommended_total - baseline_total:
            raise ValueError("total_solver_scaled_delta is not recommended minus baseline")
        if self.absolute_improvement != -total_delta:
            raise ValueError("absolute_improvement is not the negation of the total delta")
        if self.coverage_delta_basis_points != recommended_coverage - baseline_coverage:
            raise ValueError("coverage_delta_basis_points is not recommended minus baseline")
        return self


def baseline_comparison_unavailable(
    reason: BaselineUnavailableReason,
    message: str,
    *,
    problem: OptimizationProblem | None = None,
) -> BaselineComparison:
    """The only way to say "no comparison", so it can never be said as a zero."""

    return BaselineComparison(
        status=BaselineEvaluationStatus.UNAVAILABLE,
        unavailable_reason=reason,
        message=message,
        optimization_policy_version=problem.optimization_policy_version if problem is not None else None,
        assumption_version=problem.objective_weights.assumption_version if problem is not None else None,
        graph_version=problem.scenarios[0].travel_matrix.graph_version if problem is not None else None,
    )


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
    # What the recommendation is better THAN. Always present on a solved result:
    # when no incumbent set was supplied this carries status UNAVAILABLE and a
    # reason, so "optimal, 4 facilities opened, objective 8.1e12" can never be
    # published with nothing to compare it to and no explanation of why.
    baseline_comparison: BaselineComparison | None = None
    solver: Literal["OR_TOOLS_CP_SAT"] = "OR_TOOLS_CP_SAT"
    solver_version: str
    random_seed: int
    # Records how the solve was ACTUALLY run. This was Literal[1] back when
    # SolverSettings pinned a single worker; once parallel search was allowed
    # for the optimality proof, the result kept asserting 1 while real solves
    # used 8. A frozen lineage record that misstates its own solver
    # configuration is worse than one that omits it -- an auditor checking
    # reproducibility would be told the solve was single-threaded when it was
    # not. It now carries the real value.
    num_search_workers: int = Field(default=1, ge=1, le=32)
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
        if (
            self.baseline_comparison is not None
            and self.baseline_comparison.status is not BaselineEvaluationStatus.UNAVAILABLE
        ):
            raise ValueError(
                "a fail-closed result has no recommendation, so it cannot publish an "
                "improvement over the do-nothing baseline"
            )
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
