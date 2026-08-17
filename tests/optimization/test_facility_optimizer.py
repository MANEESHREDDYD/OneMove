import random
import subprocess

import pytest
from pydantic import ValidationError

from services.zonepilot.optimization import (
    DemandPoint,
    Facility,
    FacilityCapacityAdjustment,
    MatrixEvidenceClass,
    ObjectiveWeights,
    OptimizationAction,
    OptimizationConstraints,
    OptimizationProblem,
    OptimizationStatus,
    SolverSettings,
    TravelMatrix,
    UncertaintyScenario,
    optimize_facilities,
)
from services.zonepilot.optimization import solver as solver_module


def routed_matrix(
    matrix_id: str,
    facility_ids: tuple[str, ...],
    demand_ids: tuple[str, ...],
    durations: tuple[tuple[int, ...], ...],
    *,
    evidence_class: MatrixEvidenceClass = MatrixEvidenceClass.TEST_ONLY,
) -> TravelMatrix:
    return TravelMatrix(
        matrix_id=matrix_id,
        graph_version="graph-2026-08-14.1",
        router="osrm-adapter",
        router_version="1.0.0",
        evidence_class=evidence_class,
        facility_ids=facility_ids,
        demand_ids=demand_ids,
        durations_seconds=durations,
    )


def weights(
    *,
    expected: int = 1,
    p95: int = 0,
    cost: int = 0,
    exposure: int = 0,
    coverage: int = 0,
) -> ObjectiveWeights:
    return ObjectiveWeights(
        assumption_version="test-assumptions-v1",
        expected_travel=expected,
        p95_travel=p95,
        facility_cost=cost,
        failure_exposure=exposure,
        coverage_loss=coverage,
    )


def problem(
    *,
    facilities: tuple[Facility, ...],
    demands: tuple[DemandPoint, ...],
    scenarios: tuple[UncertaintyScenario, ...],
    objective: ObjectiveWeights | None = None,
    constraints: OptimizationConstraints | None = None,
    max_time_seconds: float = 10.0,
) -> OptimizationProblem:
    return OptimizationProblem(
        problem_id="test-problem",
        facilities=facilities,
        demand_points=demands,
        scenarios=scenarios,
        constraints=constraints
        or OptimizationConstraints(
            min_open_facilities=1,
            max_open_facilities=len(facilities),
            max_travel_seconds=1_000,
            minimum_coverage_basis_points=10_000,
        ),
        objective_weights=objective or weights(),
        solver_settings=SolverSettings(max_time_seconds=max_time_seconds),
    )


def facility(facility_id: str, *, capacity: int = 10, cost: int = 0, exposure: int = 0) -> Facility:
    return Facility(
        facility_id=facility_id,
        capacity_units=capacity,
        fixed_cost_units=cost,
        failure_exposure_basis_points=exposure,
    )


def test_contracts_reject_non_network_non_integer_and_malformed_matrices():
    valid = routed_matrix("valid", ("a",), ("d",), ((12,),)).model_dump()

    non_network = {**valid, "source_kind": "EUCLIDEAN"}
    with pytest.raises(ValidationError):
        TravelMatrix.model_validate(non_network)

    non_integer = {**valid, "durations_seconds": ((12.5,),)}
    with pytest.raises(ValidationError):
        TravelMatrix.model_validate(non_integer)

    non_finite = {**valid, "durations_seconds": ((float("inf"),),)}
    with pytest.raises(ValidationError):
        TravelMatrix.model_validate(non_finite)

    wrong_shape = {**valid, "durations_seconds": ((12, 13),)}
    with pytest.raises(ValidationError, match="one duration per demand_id"):
        TravelMatrix.model_validate(wrong_shape)

    unknown_field = {**valid, "straight_line_fallback": True}
    with pytest.raises(ValidationError):
        TravelMatrix.model_validate(unknown_field)


def test_problem_rejects_probability_axis_adjustment_and_objective_overflow_attacks():
    base_facilities = (facility("a", capacity=1_000_000_000, cost=1_000_000_000),)
    base_demands = (DemandPoint(demand_id="d", demand_units=1_000_000_000),)
    matrix = routed_matrix("m", ("a",), ("d",), ((604_800,),))

    with pytest.raises(ValidationError, match="sum to 10000"):
        problem(
            facilities=base_facilities,
            demands=base_demands,
            scenarios=(UncertaintyScenario(scenario_id="only", probability_basis_points=9_999, travel_matrix=matrix),),
        )

    wrong_axis = routed_matrix("wrong", ("other",), ("d",), ((10,),))
    with pytest.raises(ValidationError, match="exactly the problem facility_ids"):
        problem(
            facilities=base_facilities,
            demands=base_demands,
            scenarios=(
                UncertaintyScenario(scenario_id="only", probability_basis_points=10_000, travel_matrix=wrong_axis),
            ),
        )

    with pytest.raises(ValidationError, match="known facilities"):
        problem(
            facilities=base_facilities,
            demands=base_demands,
            scenarios=(
                UncertaintyScenario(
                    scenario_id="only",
                    probability_basis_points=10_000,
                    travel_matrix=matrix,
                    capacity_adjustments=(
                        FacilityCapacityAdjustment(facility_id="unknown", available_capacity_basis_points=0),
                    ),
                ),
            ),
        )

    with pytest.raises(ValidationError, match="int64 safety bound"):
        problem(
            facilities=base_facilities,
            demands=base_demands,
            scenarios=(UncertaintyScenario(scenario_id="only", probability_basis_points=10_000, travel_matrix=matrix),),
            objective=weights(expected=1_000_000_000),
        )


def test_known_robust_optimum_uses_scenario_recourse_and_capacity_outage():
    facilities = (facility("a"), facility("b"))
    demands = (DemandPoint(demand_id="d1", demand_units=5), DemandPoint(demand_id="d2", demand_units=5))
    nominal = UncertaintyScenario(
        scenario_id="nominal",
        probability_basis_points=9_000,
        travel_matrix=routed_matrix("nominal", ("a", "b"), ("d1", "d2"), ((1, 2), (5, 4))),
    )
    outage = UncertaintyScenario(
        scenario_id="a-outage",
        probability_basis_points=1_000,
        travel_matrix=routed_matrix(
            "a-outage",
            ("a", "b"),
            ("d1", "d2"),
            ((100, 100), (5, 4)),
            evidence_class=MatrixEvidenceClass.SIMULATED_FAILURE,
        ),
        capacity_adjustments=(FacilityCapacityAdjustment(facility_id="a", available_capacity_basis_points=0),),
    )

    result = optimize_facilities(problem(facilities=facilities, demands=demands, scenarios=(nominal, outage)))

    assert result.status is OptimizationStatus.OPTIMAL
    assert result.opened_facility_ids == ("a", "b")
    assignment_map = {(row.scenario_id, row.demand_id): row.facility_id for row in result.assignments}
    assert assignment_map == {
        ("a-outage", "d1"): "b",
        ("a-outage", "d2"): "b",
        ("nominal", "d1"): "a",
        ("nominal", "d2"): "a",
    }
    assert result.objective is not None
    assert result.objective.expected_travel_probability_demand_seconds == 180_000
    assert result.graph_version == "graph-2026-08-14.1"
    assert [(row.scenario_id, row.matrix_id, row.evidence_class) for row in result.scenario_inputs] == [
        ("a-outage", "a-outage", MatrixEvidenceClass.SIMULATED_FAILURE),
        ("nominal", "nominal", MatrixEvidenceClass.TEST_ONLY),
    ]


def test_capacity_and_network_coverage_constraints_are_hard_constraints():
    facilities = (facility("a"), facility("b"))
    demand = (DemandPoint(demand_id="d", demand_units=10),)
    scenario = UncertaintyScenario(
        scenario_id="nominal",
        probability_basis_points=10_000,
        travel_matrix=routed_matrix("coverage", ("a", "b"), ("d",), ((500,), (50,))),
    )
    constraints = OptimizationConstraints(
        min_open_facilities=1,
        max_open_facilities=1,
        max_travel_seconds=100,
        minimum_coverage_basis_points=10_000,
    )

    result = optimize_facilities(
        problem(facilities=facilities, demands=demand, scenarios=(scenario,), constraints=constraints)
    )
    assert result.status is OptimizationStatus.OPTIMAL
    assert result.opened_facility_ids == ("b",)

    insufficient = (facility("a", capacity=10), facility("b", capacity=9))
    infeasible = optimize_facilities(
        problem(facilities=insufficient, demands=demand, scenarios=(scenario,), constraints=constraints)
    )
    assert infeasible.status is OptimizationStatus.INFEASIBLE
    assert infeasible.fail_closed is True
    assert infeasible.action is OptimizationAction.NONE
    assert infeasible.opened_facility_ids == ()
    assert infeasible.assignments == ()
    assert infeasible.objective is None


def test_explicit_no_action_option_can_be_proved_optimal():
    facilities = (facility("a", cost=10),)
    demands = (DemandPoint(demand_id="d", demand_units=4),)
    scenario = UncertaintyScenario(
        scenario_id="nominal",
        probability_basis_points=10_000,
        travel_matrix=routed_matrix("no-action", ("a",), ("d",), ((10,),)),
    )
    constraints = OptimizationConstraints(
        min_open_facilities=0,
        max_open_facilities=1,
        max_travel_seconds=100,
        minimum_coverage_basis_points=0,
        allow_uncovered_demand=True,
        allow_no_action=True,
    )

    result = optimize_facilities(
        problem(
            facilities=facilities,
            demands=demands,
            scenarios=(scenario,),
            constraints=constraints,
            objective=weights(expected=0, cost=1),
        )
    )

    assert result.status is OptimizationStatus.OPTIMAL
    assert result.action is OptimizationAction.NO_ACTION
    assert result.opened_facility_ids == ()
    assert result.scenario_metrics[0].uncovered_demand_units == 4


def test_tie_breaking_is_deterministic_and_independent_of_input_axis_order():
    demand = (DemandPoint(demand_id="d", demand_units=1),)
    constraints = OptimizationConstraints(
        min_open_facilities=1,
        max_open_facilities=1,
        max_travel_seconds=100,
        minimum_coverage_basis_points=10_000,
    )

    def tied(order: tuple[str, str]) -> OptimizationProblem:
        scenario = UncertaintyScenario(
            scenario_id="nominal",
            probability_basis_points=10_000,
            travel_matrix=routed_matrix("tie", order, ("d",), ((10,), (10,))),
        )
        return problem(
            facilities=tuple(facility(facility_id) for facility_id in order),
            demands=demand,
            scenarios=(scenario,),
            constraints=constraints,
        )

    first = optimize_facilities(tied(("b", "a")))
    second = optimize_facilities(tied(("a", "b")))
    repeated = optimize_facilities(tied(("b", "a")))

    assert first.opened_facility_ids == second.opened_facility_ids == repeated.opened_facility_ids == ("a",)
    assert tuple((row.facility_id, row.demand_id) for row in first.assignments) == (("a", "d"),)
    assert first.objective == second.objective == repeated.objective


@pytest.mark.parametrize(
    ("nominal_probability", "disruption_probability", "expected_p95"),
    [(9_500, 500, 10), (9_499, 501, 100)],
)
def test_weighted_p95_respects_the_discrete_probability_boundary(
    nominal_probability: int,
    disruption_probability: int,
    expected_p95: int,
):
    facilities = (facility("a"),)
    demands = (DemandPoint(demand_id="d", demand_units=1),)
    scenarios = (
        UncertaintyScenario(
            scenario_id="nominal",
            probability_basis_points=nominal_probability,
            travel_matrix=routed_matrix("nominal", ("a",), ("d",), ((10,),)),
        ),
        UncertaintyScenario(
            scenario_id="disruption",
            probability_basis_points=disruption_probability,
            travel_matrix=routed_matrix(
                "disruption",
                ("a",),
                ("d",),
                ((100,),),
                evidence_class=MatrixEvidenceClass.SIMULATED_FAILURE,
            ),
        ),
    )

    result = optimize_facilities(
        problem(facilities=facilities, demands=demands, scenarios=scenarios, objective=weights(expected=0, p95=1))
    )

    assert result.status is OptimizationStatus.OPTIMAL
    assert result.objective is not None
    assert result.objective.p95_travel_demand_seconds == expected_p95


def test_objective_weight_sensitivity_changes_the_selected_tradeoff():
    facilities = (facility("fast", cost=100), facility("cheap", cost=0))
    demands = (DemandPoint(demand_id="d", demand_units=1),)
    scenario = UncertaintyScenario(
        scenario_id="nominal",
        probability_basis_points=10_000,
        travel_matrix=routed_matrix("sensitivity", ("fast", "cheap"), ("d",), ((1,), (10,))),
    )
    constraints = OptimizationConstraints(
        min_open_facilities=1,
        max_open_facilities=1,
        max_travel_seconds=100,
        minimum_coverage_basis_points=10_000,
    )

    fastest = optimize_facilities(
        problem(facilities=facilities, demands=demands, scenarios=(scenario,), constraints=constraints)
    )
    cheapest = optimize_facilities(
        problem(
            facilities=facilities,
            demands=demands,
            scenarios=(scenario,),
            constraints=constraints,
            objective=weights(expected=1, cost=1),
        )
    )

    assert fastest.opened_facility_ids == ("fast",)
    assert cheapest.opened_facility_ids == ("cheap",)


@pytest.mark.parametrize("seed", range(12))
def test_property_style_single_facility_optimum_matches_brute_force(seed: int):
    generator = random.Random(seed)
    facility_ids = ("a", "b", "c", "d")
    durations = tuple((generator.randint(1, 20),) for _ in facility_ids)
    facilities = tuple(facility(facility_id, capacity=1) for facility_id in facility_ids)
    demands = (DemandPoint(demand_id="d", demand_units=1),)
    scenario = UncertaintyScenario(
        scenario_id="nominal",
        probability_basis_points=10_000,
        travel_matrix=routed_matrix(f"property-{seed}", facility_ids, ("d",), durations),
    )
    constraints = OptimizationConstraints(
        min_open_facilities=1,
        max_open_facilities=1,
        max_travel_seconds=100,
        minimum_coverage_basis_points=10_000,
    )

    result = optimize_facilities(
        problem(facilities=facilities, demands=demands, scenarios=(scenario,), constraints=constraints)
    )
    brute_force = min(zip((row[0] for row in durations), facility_ids, strict=True))[1]

    assert result.status is OptimizationStatus.OPTIMAL
    assert result.opened_facility_ids == (brute_force,)


def test_timeout_returns_no_feasible_but_unproved_candidate():
    facilities = (facility("a"), facility("b"))
    demands = (DemandPoint(demand_id="d", demand_units=1),)
    scenario = UncertaintyScenario(
        scenario_id="nominal",
        probability_basis_points=10_000,
        travel_matrix=routed_matrix("timeout", ("a", "b"), ("d",), ((1,), (2,))),
    )

    result = optimize_facilities(
        problem(
            facilities=facilities,
            demands=demands,
            scenarios=(scenario,),
            max_time_seconds=1e-9,
        )
    )

    assert result.status is OptimizationStatus.TIME_LIMIT
    assert result.fail_closed is True
    assert result.action is OptimizationAction.NONE
    assert result.opened_facility_ids == ()
    assert result.assignments == ()
    assert result.objective is None


def test_native_worker_failure_is_converted_to_a_fail_closed_result(monkeypatch: pytest.MonkeyPatch):
    facilities = (facility("a"),)
    demands = (DemandPoint(demand_id="d", demand_units=1),)
    scenario = UncertaintyScenario(
        scenario_id="nominal",
        probability_basis_points=10_000,
        travel_matrix=routed_matrix("worker-failure", ("a",), ("d",), ((1,),)),
    )
    request = problem(facilities=facilities, demands=demands, scenarios=(scenario,))

    def failed_worker(*args, **kwargs):  # noqa: ARG001
        return subprocess.CompletedProcess(args=[], returncode=139, stdout="", stderr="native failure")

    monkeypatch.setattr(solver_module.subprocess, "run", failed_worker)
    result = solver_module.optimize_facilities(request)

    assert result.status is OptimizationStatus.SOLVER_ERROR
    assert result.fail_closed is True
    assert result.action is OptimizationAction.NONE
    assert result.opened_facility_ids == ()
    assert result.assignments == ()
    assert result.objective is None
