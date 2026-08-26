"""The recommendation must say what it is better THAN.

"OPTIMAL, 4 facilities opened, objective 8.1e12" is unfalsifiable on its own: a
reader cannot tell whether the recommendation beats leaving the network exactly
as it is. The do-nothing comparison scores the incumbent facility set under the
same problem, scenarios, travel matrices, weights and policy version, so the
only difference between the two numbers is which facilities are open.

R1 carries no facility ledger -- its twelve facilities are candidate sites
ranked by commercial POI density, not operating depots -- so the incumbent set
is an INPUT. When it is absent the comparison is UNAVAILABLE with the reason,
never a zero improvement. Manufacturing an incumbent set would fabricate the
very number the comparison exists to test.
"""

from __future__ import annotations

import pytest


def _problem(**constraint_overrides):
    """A 3x5 problem small enough that solve difficulty is not a variable."""
    from services.zonepilot.optimization.contracts import (
        CapacityMode,
        DemandPoint,
        Facility,
        MatrixEvidenceClass,
        ObjectiveWeights,
        OptimizationConstraints,
        OptimizationProblem,
        SolverSettings,
        TravelMatrix,
        UncertaintyScenario,
    )

    facility_ids = [f"fac:{i}" for i in range(3)]
    demand_ids = [f"zone:{j}" for j in range(5)]
    facilities = tuple(
        Facility(
            facility_id=facility_ids[i],
            capacity_units=1000,
            fixed_cost_units=1000 + i * 10,
            failure_exposure_basis_points=100 * (i + 1),
        )
        for i in range(3)
    )
    demands = tuple(DemandPoint(demand_id=demand_ids[j], demand_units=10 * (j + 1)) for j in range(5))
    rows = tuple(tuple(0 if i == j else 300 + 60 * j for j in range(5)) for i in range(3))
    matrix = TravelMatrix(
        matrix_id="m1",
        graph_version="g1",
        router="test",
        router_version="1",
        evidence_class=MatrixEvidenceClass.PUBLIC_GEOGRAPHIC,
        facility_ids=tuple(facility_ids),
        demand_ids=tuple(demand_ids),
        durations_seconds=rows,
    )
    defaults = dict(
        min_open_facilities=1,
        max_open_facilities=2,
        max_travel_seconds=1800,
        minimum_coverage_basis_points=0,
        allow_uncovered_demand=False,
        capacity_mode=CapacityMode.NOT_MODELED,
    )
    defaults.update(constraint_overrides)
    return OptimizationProblem(
        problem_id="baseline-fixture",
        facilities=facilities,
        demand_points=demands,
        scenarios=(UncertaintyScenario(scenario_id="s1", probability_basis_points=10000, travel_matrix=matrix),),
        constraints=OptimizationConstraints(**defaults),
        objective_weights=ObjectiveWeights(
            assumption_version="test@1",
            expected_travel=5000,
            p95_travel=1000,
            facility_cost=3000,
            failure_exposure=500,
            coverage_loss=5000,
        ),
        solver_settings=SolverSettings(max_time_seconds=30),
    )


def _baseline(*facility_ids: str):
    from services.zonepilot.optimization.contracts import DoNothingBaseline, EvidenceClass

    return DoNothingBaseline(
        baseline_id="incumbent-under-test",
        facility_ids=tuple(facility_ids),
        source="supplied by the test as the incumbent network",
        evidence_class=EvidenceClass.ASSUMPTION,
    )


def _solve(problem, baseline=None):
    from services.zonepilot.optimization._cp_sat import optimize_facilities

    return optimize_facilities(problem, baseline=baseline)


def test_process_isolated_solver_carries_the_declared_baseline() -> None:
    """The production solver boundary must not drop the demo baseline."""
    from services.zonepilot.optimization.solver import optimize_facilities

    result = optimize_facilities(_problem(), baseline=_baseline("fac:0", "fac:1"))

    assert result.baseline_comparison is not None
    assert result.baseline_comparison.status.value == "AVAILABLE"
    assert result.baseline_comparison.baseline_facility_ids == ("fac:0", "fac:1")


# --- the absent baseline -----------------------------------------------------


def test_absent_baseline_is_unavailable_with_a_reason_never_zero() -> None:
    """No incumbent set means no comparison -- not an improvement of zero.

    Reporting 0 would read as "the recommendation is no better than doing
    nothing", which is a claim. UNAVAILABLE is the absence of a claim, and the
    two must never be confused.
    """
    from services.zonepilot.optimization.contracts import (
        BaselineEvaluationStatus,
        BaselineUnavailableReason,
    )

    result = _solve(_problem())
    comparison = result.baseline_comparison

    assert comparison is not None, "a solve must always publish a comparison field"
    assert comparison.status is BaselineEvaluationStatus.UNAVAILABLE
    assert comparison.unavailable_reason is BaselineUnavailableReason.NO_BASELINE_SUPPLIED
    assert comparison.message, "UNAVAILABLE must always carry its reason in prose"

    # The critical property: every numeric field is None, not 0.
    for field in (
        "baseline_solver_objective_total",
        "total_solver_scaled_delta",
        "absolute_improvement",
        "improvement_basis_points",
        "coverage_delta_basis_points",
    ):
        assert getattr(comparison, field) is None, f"{field} must be None when unavailable, not 0"
    assert comparison.component_deltas == ()


def test_unknown_facility_ids_are_reported_not_silently_dropped() -> None:
    """An incumbent naming a facility this problem lacks cannot be scored."""
    from services.zonepilot.optimization.contracts import (
        BaselineEvaluationStatus,
        BaselineUnavailableReason,
    )

    comparison = _solve(_problem(), _baseline("fac:0", "fac:99")).baseline_comparison
    assert comparison.status is BaselineEvaluationStatus.UNAVAILABLE
    assert comparison.unavailable_reason is BaselineUnavailableReason.UNKNOWN_FACILITY_IDS
    assert "fac:99" in comparison.message


def test_capacity_mode_withholds_the_comparison_rather_than_guessing() -> None:
    """Under ASSUMPTION capacity the nearest-facility rule is not valid.

    Allocating the incumbent network's load some other way would mean choosing
    an operating policy nobody has stated, so the comparison is withheld.
    """
    from services.zonepilot.optimization.contracts import (
        BaselineEvaluationStatus,
        BaselineUnavailableReason,
        CapacityMode,
    )

    problem = _problem(capacity_mode=CapacityMode.ASSUMPTION)
    comparison = _solve(problem, _baseline("fac:0")).baseline_comparison
    assert comparison.status is BaselineEvaluationStatus.UNAVAILABLE
    assert comparison.unavailable_reason is BaselineUnavailableReason.CAPACITY_MODE_COUPLES_ASSIGNMENTS


# --- the evaluated baseline --------------------------------------------------


def test_recommendation_is_never_worse_than_a_feasible_in_policy_baseline() -> None:
    """If the solver's optimum loses to a legal incumbent, it is not optimal.

    The incumbent here satisfies every constraint the solver was given, so it
    was inside the solver's own search space. A baseline that scores better
    would mean CP-SAT returned OPTIMAL for a configuration it could have beaten,
    which is a defect in the model rather than an interesting result.
    """
    from services.zonepilot.optimization.contracts import BaselineEvaluationStatus

    problem = _problem()
    result = _solve(problem, _baseline("fac:0", "fac:1"))
    comparison = result.baseline_comparison

    if comparison.status is not BaselineEvaluationStatus.AVAILABLE:
        pytest.skip(f"baseline was not evaluated: {comparison.message}")

    assert comparison.baseline_within_policy is True
    assert comparison.baseline_feasible is True
    assert comparison.recommended_solver_objective_total <= comparison.baseline_solver_objective_total, (
        "CP-SAT reported OPTIMAL for a configuration the incumbent beats: "
        f"recommended={comparison.recommended_solver_objective_total:,} "
        f"baseline={comparison.baseline_solver_objective_total:,}"
    )


def test_component_deltas_sum_exactly_to_the_total_delta() -> None:
    """Integer arithmetic throughout -- the parts must reconcile with the whole.

    A float would make this "close enough". The whole point of the fixed-point
    scale is that it does not have to be.
    """
    from services.zonepilot.optimization.contracts import BaselineEvaluationStatus

    comparison = _solve(_problem(), _baseline("fac:0", "fac:1")).baseline_comparison
    if comparison.status is not BaselineEvaluationStatus.AVAILABLE:
        pytest.skip(f"baseline was not evaluated: {comparison.message}")

    assert comparison.component_deltas, "an evaluated comparison must publish its components"
    summed = sum(delta.solver_scaled_delta for delta in comparison.component_deltas)
    assert summed == comparison.total_solver_scaled_delta, (
        f"components sum to {summed:,} but the total delta is {comparison.total_solver_scaled_delta:,}"
    )

    # And each component's own delta must reconcile with its two sides.
    for delta in comparison.component_deltas:
        assert delta.solver_scaled_delta == (
            delta.recommended_solver_scaled_contribution - delta.baseline_solver_scaled_contribution
        )
        assert delta.evidence_class == "DERIVED"


def test_out_of_policy_baseline_is_evaluated_and_flagged_not_rejected() -> None:
    """An incumbent that breaks today's policy is exactly what you want to see.

    Refusing to score it would hide the case the comparison is most useful for:
    the network as it actually stands, against a constraint set adopted later.
    """
    from services.zonepilot.optimization.contracts import BaselineEvaluationStatus

    # max_open_facilities is 2; the incumbent runs all three.
    comparison = _solve(_problem(), _baseline("fac:0", "fac:1", "fac:2")).baseline_comparison

    assert comparison.status is BaselineEvaluationStatus.AVAILABLE, (
        f"an out-of-policy incumbent must still be scored: {comparison.message}"
    )
    assert comparison.baseline_within_policy is False
    assert comparison.baseline_policy_violations, "the violation must be named, not merely implied"
    assert comparison.baseline_solver_objective_total is not None


def test_coverage_is_published_so_improvement_by_abandonment_is_visible() -> None:
    """An objective that improves by serving fewer zones must show that.

    Coverage sits beside the objective precisely so a reader can tell the
    difference between a better network and a smaller promise.
    """
    from services.zonepilot.optimization.contracts import BaselineEvaluationStatus

    comparison = _solve(_problem(), _baseline("fac:0", "fac:1")).baseline_comparison
    if comparison.status is not BaselineEvaluationStatus.AVAILABLE:
        pytest.skip(f"baseline was not evaluated: {comparison.message}")

    assert comparison.baseline_coverage_basis_points is not None
    assert comparison.recommended_coverage_basis_points is not None
    assert comparison.coverage_delta_basis_points == (
        comparison.recommended_coverage_basis_points - comparison.baseline_coverage_basis_points
    )


def test_both_sides_are_scored_under_the_same_policy_and_assumptions() -> None:
    """Comparability is the whole claim; the lineage must prove it."""
    from services.zonepilot.optimization.contracts import (
        OPTIMIZATION_POLICY_VERSION,
        BaselineEvaluationStatus,
    )

    problem = _problem()
    comparison = _solve(problem, _baseline("fac:0", "fac:1")).baseline_comparison
    if comparison.status is not BaselineEvaluationStatus.AVAILABLE:
        pytest.skip(f"baseline was not evaluated: {comparison.message}")

    assert comparison.optimization_policy_version == OPTIMIZATION_POLICY_VERSION
    assert comparison.assumption_version == problem.objective_weights.assumption_version
    assert comparison.evidence_class == "DERIVED"
