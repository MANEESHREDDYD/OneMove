"""Non-dominated alternatives instead of one opaque weighted score.

A single scalarized objective hides the trade the operator is actually being
asked to make. This module evaluates a fixed, deterministic family of weight
vectors derived from the caller's own weights, then returns the non-dominated
set over five explicit axes.

Honest scope: weighted-sum scalarization can only recover *supported* efficient
points — those on the convex hull of the objective set. Points that are Pareto
optimal but lie in a non-convex pocket are unreachable this way and are not
reported. ``method`` records that limit in the contract itself rather than
letting the output imply a complete frontier.

Every candidate is produced by the same fail-closed engine, so a weight vector
whose solve is not proved optimal contributes no candidate at all; it is listed
under ``unproved_evaluations`` so a shrunken frontier can never be mistaken for
a genuinely small one.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from services.zonepilot.optimization.contracts import (
    BASIS_POINTS,
    ObjectiveWeights,
    OptimizationProblem,
    OptimizationResult,
    OptimizationStatus,
    problem_fingerprint,
)
from services.zonepilot.optimization.solver import optimize_facilities

# Ordered axis catalogue. Each entry names the objective-weight fields kept
# active for that probe; every other weight is zeroed. Weights are only ever
# zeroed, never raised, so a probe can never breach the int64 objective safety
# bound that the base problem already satisfies.
_WEIGHT_PROBES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SCALARIZED", ("expected_travel", "p95_travel", "facility_cost", "failure_exposure", "coverage_loss")),
    ("COST_AND_EXPOSURE", ("facility_cost", "failure_exposure")),
    ("COVERAGE", ("coverage_loss",)),
    ("EXPECTED_TRAVEL", ("expected_travel",)),
    ("FACILITY_COST", ("facility_cost",)),
    ("FAILURE_EXPOSURE", ("failure_exposure",)),
    ("P95_TRAVEL", ("p95_travel",)),
    ("TRAVEL_AND_COVERAGE", ("expected_travel", "coverage_loss")),
)

_WEIGHT_FIELDS = ("expected_travel", "p95_travel", "facility_cost", "failure_exposure", "coverage_loss")


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ParetoObjectiveVector(StrictContract):
    """The five comparable axes, in their raw integer units.

    Four axes are minimised. ``expected_coverage_basis_points`` is maximised and
    is stated as coverage rather than loss so the sign convention is visible in
    the field name.
    """

    expected_travel_probability_demand_seconds: int = Field(ge=0)
    p95_travel_demand_seconds: int = Field(ge=0)
    facility_cost_units: int = Field(ge=0)
    failure_exposure_capacity_basis_points: int = Field(ge=0)
    expected_coverage_basis_points: int = Field(ge=0, le=BASIS_POINTS)


class ParetoCandidate(StrictContract):
    probe_id: str = Field(min_length=1)
    weights: ObjectiveWeights
    opened_facility_ids: tuple[str, ...]
    objective_vector: ParetoObjectiveVector
    scalarized_weighted_total: int


class UnprovedEvaluation(StrictContract):
    """A weight vector that produced no candidate, and why."""

    probe_id: str = Field(min_length=1)
    status: OptimizationStatus
    message: str


class ParetoFrontier(StrictContract):
    schema_name: Literal["zonepilot.facility_optimization_pareto"] = "zonepilot.facility_optimization_pareto"
    schema_version: Literal["1.0.0"] = "1.0.0"
    problem_id: str
    problem_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    method: Literal["WEIGHTED_SUM_SUPPORTED_SET"] = "WEIGHTED_SUM_SUPPORTED_SET"
    evaluated_probe_count: int = Field(ge=0)
    dominated_candidate_count: int = Field(ge=0)
    candidates: tuple[ParetoCandidate, ...] = ()
    unproved_evaluations: tuple[UnprovedEvaluation, ...] = ()


def _probe_weights(base: ObjectiveWeights, active_fields: tuple[str, ...]) -> ObjectiveWeights | None:
    values = {field: (getattr(base, field) if field in active_fields else 0) for field in _WEIGHT_FIELDS}
    if not any(values.values()):
        # ObjectiveWeights requires at least one active weight; a probe whose
        # axes are all unweighted in the caller's own configuration is simply
        # not expressible and is skipped rather than invented.
        return None
    return ObjectiveWeights(assumption_version=base.assumption_version, **values)


def _expected_coverage_basis_points(result: OptimizationResult) -> int:
    """Probability-weighted coverage, kept in integer basis points."""

    weighted = sum(metric.probability_basis_points * metric.coverage_basis_points for metric in result.scenario_metrics)
    return weighted // BASIS_POINTS


def _objective_vector(result: OptimizationResult) -> ParetoObjectiveVector:
    assert result.objective is not None
    objective = result.objective
    return ParetoObjectiveVector(
        expected_travel_probability_demand_seconds=objective.expected_travel_probability_demand_seconds,
        p95_travel_demand_seconds=objective.p95_travel_demand_seconds,
        facility_cost_units=objective.facility_cost_units,
        failure_exposure_capacity_basis_points=objective.failure_exposure_capacity_basis_points,
        expected_coverage_basis_points=_expected_coverage_basis_points(result),
    )


def _dominates(left: ParetoObjectiveVector, right: ParetoObjectiveVector) -> bool:
    """True when ``left`` is at least as good on every axis and better on one."""

    minimised = (
        "expected_travel_probability_demand_seconds",
        "p95_travel_demand_seconds",
        "facility_cost_units",
        "failure_exposure_capacity_basis_points",
    )
    at_least_as_good = all(getattr(left, axis) <= getattr(right, axis) for axis in minimised)
    at_least_as_good = at_least_as_good and left.expected_coverage_basis_points >= right.expected_coverage_basis_points
    if not at_least_as_good:
        return False
    strictly_better = any(getattr(left, axis) < getattr(right, axis) for axis in minimised)
    strictly_better = strictly_better or left.expected_coverage_basis_points > right.expected_coverage_basis_points
    return strictly_better


def _candidate_sort_key(candidate: ParetoCandidate) -> tuple:
    vector = candidate.objective_vector
    return (
        vector.expected_travel_probability_demand_seconds,
        vector.p95_travel_demand_seconds,
        vector.facility_cost_units,
        vector.failure_exposure_capacity_basis_points,
        -vector.expected_coverage_basis_points,
        candidate.opened_facility_ids,
        candidate.probe_id,
    )


def build_pareto_frontier(problem: OptimizationProblem) -> ParetoFrontier:
    """Evaluate the deterministic probe family and return its non-dominated set.

    Cost is one full canonical solve per probe. The probe list is fixed and
    ordered, so the frontier is reproducible for a given problem fingerprint.
    """

    fingerprint = problem_fingerprint(problem)
    evaluated: list[ParetoCandidate] = []
    unproved: list[UnprovedEvaluation] = []
    evaluated_probes = 0
    seen_weights: set[tuple[int, ...]] = set()

    for probe_id, active_fields in _WEIGHT_PROBES:
        weights = _probe_weights(problem.objective_weights, active_fields)
        if weights is None:
            continue
        signature = tuple(getattr(weights, field) for field in _WEIGHT_FIELDS)
        if signature in seen_weights:
            continue
        seen_weights.add(signature)

        probe_problem = problem.model_copy(update={"objective_weights": weights})
        evaluated_probes += 1
        result = optimize_facilities(probe_problem)
        if result.status is not OptimizationStatus.OPTIMAL or result.objective is None:
            unproved.append(
                UnprovedEvaluation(probe_id=probe_id, status=result.status, message=result.message)
            )
            continue
        evaluated.append(
            ParetoCandidate(
                probe_id=probe_id,
                weights=weights,
                opened_facility_ids=result.opened_facility_ids,
                objective_vector=_objective_vector(result),
                scalarized_weighted_total=result.objective.weighted_total,
            )
        )

    # Collapse probes that landed on the same decision before filtering, so the
    # candidate count reports distinct plans rather than duplicate probes.
    unique: list[ParetoCandidate] = []
    seen_plans: set[tuple[tuple[str, ...], tuple]] = set()
    for candidate in sorted(evaluated, key=_candidate_sort_key):
        key = (candidate.opened_facility_ids, _candidate_sort_key(candidate)[:5])
        if key in seen_plans:
            continue
        seen_plans.add(key)
        unique.append(candidate)

    non_dominated = [
        candidate
        for candidate in unique
        if not any(_dominates(other.objective_vector, candidate.objective_vector) for other in unique)
    ]
    return ParetoFrontier(
        problem_id=problem.problem_id,
        problem_fingerprint=fingerprint,
        evaluated_probe_count=evaluated_probes,
        dominated_candidate_count=len(unique) - len(non_dominated),
        candidates=tuple(sorted(non_dominated, key=_candidate_sort_key)),
        unproved_evaluations=tuple(unproved),
    )
