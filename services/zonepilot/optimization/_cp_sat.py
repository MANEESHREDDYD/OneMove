"""Internal deterministic robust facility optimizer using OR-Tools CP-SAT."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import ortools
from ortools.sat.python import cp_model

from services.zonepilot.optimization.contracts import (
    BASIS_POINTS,
    P95_BASIS_POINTS,
    ObjectiveBreakdown,
    OptimizationAction,
    OptimizationProblem,
    OptimizationResult,
    OptimizationStatus,
    ScenarioAssignment,
    ScenarioInputLineage,
    ScenarioMetrics,
    UncertaintyScenario,
    problem_fingerprint,
)


@dataclass(frozen=True)
class _ModelState:
    model: cp_model.CpModel
    open_facility: dict[str, cp_model.IntVar]
    assigned: dict[tuple[str, str, str], cp_model.IntVar]
    uncovered: dict[tuple[str, str], cp_model.IntVar]
    scenario_total_travel: dict[str, cp_model.IntVar]
    primary_objective: cp_model.LinearExpr


@dataclass
class _SolveCounters:
    """Mutable tally of CP-SAT work performed by one canonical run."""

    solves: int = 0
    implied_skips: int = 0


@dataclass
class _TieBreakPolicy:
    """Which tie-break variables may be resolved without a CP-SAT solve.

    Every skip below is a value that is *uniquely forced* by constraints already
    posted on the model, so a `maximize`/`minimize` solve on that variable can
    only ever report the same value. Skipping is therefore an equality-preserving
    optimisation, not a relaxation of the canonical tie-break: see
    ``tests/optimization/test_tie_break_equivalence.py``, which asserts the two
    modes produce byte-identical results.
    """

    skip_implied: bool = True
    counters: _SolveCounters = field(default_factory=_SolveCounters)


def _duration(scenario: UncertaintyScenario, facility_id: str, demand_id: str) -> int:
    matrix = scenario.travel_matrix
    facility_index = matrix.facility_ids.index(facility_id)
    demand_index = matrix.demand_ids.index(demand_id)
    return matrix.durations_seconds[facility_index][demand_index]


def _available_capacity_basis_points(scenario: UncertaintyScenario, facility_id: str) -> int:
    for adjustment in scenario.capacity_adjustments:
        if adjustment.facility_id == facility_id:
            return adjustment.available_capacity_basis_points
    return BASIS_POINTS


def _build_model(problem: OptimizationProblem) -> _ModelState:
    model = cp_model.CpModel()
    facilities = {facility.facility_id: facility for facility in problem.facilities}
    demands = {demand.demand_id: demand for demand in problem.demand_points}
    scenarios = {scenario.scenario_id: scenario for scenario in problem.scenarios}
    facility_ids = sorted(facilities)
    demand_ids = sorted(demands)
    scenario_ids = sorted(scenarios)

    opened = {facility_id: model.new_bool_var(f"open_{index}") for index, facility_id in enumerate(facility_ids)}
    assigned: dict[tuple[str, str, str], cp_model.IntVar] = {}
    uncovered: dict[tuple[str, str], cp_model.IntVar] = {}
    scenario_totals: dict[str, cp_model.IntVar] = {}
    total_demand = sum(demand.demand_units for demand in demands.values())

    model.add(sum(opened.values()) >= problem.constraints.min_open_facilities)
    model.add(sum(opened.values()) <= problem.constraints.max_open_facilities)
    if problem.constraints.max_total_fixed_cost_units is not None:
        model.add(
            sum(facilities[facility_id].fixed_cost_units * opened[facility_id] for facility_id in facility_ids)
            <= problem.constraints.max_total_fixed_cost_units
        )

    expected_travel_terms: list[cp_model.LinearExpr] = []
    expected_uncovered_terms: list[cp_model.LinearExpr] = []
    tail_vars: dict[str, cp_model.IntVar] = {}
    q95_upper = 0
    for scenario_index, scenario_id in enumerate(scenario_ids):
        scenario = scenarios[scenario_id]
        scenario_travel_terms: list[cp_model.LinearExpr] = []
        scenario_upper = 0
        uncovered_demand_terms: list[cp_model.LinearExpr] = []
        for demand_index, demand_id in enumerate(demand_ids):
            demand = demands[demand_id]
            uncovered_var = model.new_bool_var(f"uncovered_{scenario_index}_{demand_index}")
            uncovered[(scenario_id, demand_id)] = uncovered_var
            if not problem.constraints.allow_uncovered_demand:
                model.add(uncovered_var == 0)
            assignment_vars: list[cp_model.IntVar] = []
            maximum_duration = 0
            for facility_index, facility_id in enumerate(facility_ids):
                duration = _duration(scenario, facility_id, demand_id)
                variable = model.new_bool_var(f"assign_{scenario_index}_{facility_index}_{demand_index}")
                assigned[(scenario_id, facility_id, demand_id)] = variable
                assignment_vars.append(variable)
                model.add(variable <= opened[facility_id])
                if duration > problem.constraints.max_travel_seconds:
                    model.add(variable == 0)
                scenario_travel_terms.append(demand.demand_units * duration * variable)
                maximum_duration = max(maximum_duration, duration)
            model.add(sum(assignment_vars) + uncovered_var == 1)
            uncovered_demand_terms.append(demand.demand_units * uncovered_var)
            scenario_upper += demand.demand_units * maximum_duration

        for facility_id in facility_ids:
            capacity_basis_points = _available_capacity_basis_points(scenario, facility_id)
            model.add(
                BASIS_POINTS
                * sum(
                    demands[demand_id].demand_units * assigned[(scenario_id, facility_id, demand_id)]
                    for demand_id in demand_ids
                )
                <= facilities[facility_id].capacity_units * capacity_basis_points
            )

        uncovered_units = sum(uncovered_demand_terms)
        model.add(
            (total_demand - uncovered_units) * BASIS_POINTS
            >= total_demand * problem.constraints.minimum_coverage_basis_points
        )
        total_travel = model.new_int_var(0, scenario_upper, f"scenario_travel_{scenario_index}")
        model.add(total_travel == sum(scenario_travel_terms))
        scenario_totals[scenario_id] = total_travel
        expected_travel_terms.append(scenario.probability_basis_points * total_travel)
        expected_uncovered_terms.append(scenario.probability_basis_points * uncovered_units)
        q95_upper = max(q95_upper, scenario_upper)

    q95_travel = model.new_int_var(0, q95_upper, "p95_total_travel")
    for scenario_index, scenario_id in enumerate(scenario_ids):
        scenario = scenarios[scenario_id]
        tail = model.new_bool_var(f"p95_tail_{scenario_index}")
        tail_vars[scenario_id] = tail
        scenario_upper = scenario_totals[scenario_id].proto.domain[-1]
        model.add(scenario_totals[scenario_id] <= q95_travel + scenario_upper * tail)
    model.add(
        sum(scenarios[scenario_id].probability_basis_points * tail_vars[scenario_id] for scenario_id in scenario_ids)
        <= BASIS_POINTS - P95_BASIS_POINTS
    )

    facility_cost = sum(facilities[facility_id].fixed_cost_units * opened[facility_id] for facility_id in facility_ids)
    failure_exposure = sum(
        facilities[facility_id].capacity_units
        * facilities[facility_id].failure_exposure_basis_points
        * opened[facility_id]
        for facility_id in facility_ids
    )
    weights = problem.objective_weights
    primary_objective = (
        weights.expected_travel * sum(expected_travel_terms)
        + weights.p95_travel * BASIS_POINTS * q95_travel
        + weights.facility_cost * BASIS_POINTS * facility_cost
        + weights.failure_exposure * failure_exposure
        + weights.coverage_loss * sum(expected_uncovered_terms)
    )
    model.minimize(primary_objective)
    return _ModelState(
        model=model,
        open_facility=opened,
        assigned=assigned,
        uncovered=uncovered,
        scenario_total_travel=scenario_totals,
        primary_objective=primary_objective,
    )


def _solve_once(
    model: cp_model.CpModel,
    problem: OptimizationProblem,
    deadline: float,
    counters: _SolveCounters | None = None,
) -> tuple[cp_model.CpSolverStatus, cp_model.CpSolver | None]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return cp_model.UNKNOWN, None
    if counters is not None:
        counters.solves += 1
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = remaining
    solver.parameters.num_search_workers = problem.solver_settings.num_search_workers
    solver.parameters.random_seed = problem.solver_settings.random_seed
    solver.parameters.log_search_progress = False
    status = solver.solve(model)
    return status, solver


def _closed_result(
    problem: OptimizationProblem,
    status: OptimizationStatus,
    message: str,
) -> OptimizationResult:
    return OptimizationResult(
        problem_id=problem.problem_id,
        problem_fingerprint=problem_fingerprint(problem),
        graph_version=problem.scenarios[0].travel_matrix.graph_version,
        assumption_version=problem.objective_weights.assumption_version,
        scenario_inputs=_scenario_input_lineage(problem),
        status=status,
        action=OptimizationAction.NONE,
        fail_closed=True,
        solver_version=ortools.__version__,
        random_seed=problem.solver_settings.random_seed,
        message=message,
    )


def _scenario_input_lineage(problem: OptimizationProblem) -> tuple[ScenarioInputLineage, ...]:
    return tuple(
        ScenarioInputLineage(
            scenario_id=scenario.scenario_id,
            matrix_id=scenario.travel_matrix.matrix_id,
            graph_version=scenario.travel_matrix.graph_version,
            evidence_class=scenario.travel_matrix.evidence_class,
        )
        for scenario in sorted(problem.scenarios, key=lambda item: item.scenario_id)
    )


def _require_optimal(
    problem: OptimizationProblem,
    status: cp_model.CpSolverStatus,
    solver: cp_model.CpSolver | None,
) -> tuple[cp_model.CpSolver | None, OptimizationResult | None]:
    if status == cp_model.OPTIMAL and solver is not None:
        return solver, None
    if status == cp_model.INFEASIBLE:
        return None, _closed_result(problem, OptimizationStatus.INFEASIBLE, "The constraints were proven infeasible.")
    if status == cp_model.MODEL_INVALID:
        return None, _closed_result(problem, OptimizationStatus.MODEL_INVALID, "CP-SAT rejected the integer model.")
    return None, _closed_result(
        problem,
        OptimizationStatus.TIME_LIMIT,
        "Optimality was not proven within the configured time limit; no decision is returned.",
    )


def _canonical_solution(
    problem: OptimizationProblem,
    state: _ModelState,
    deadline: float,
    policy: _TieBreakPolicy,
) -> tuple[cp_model.CpSolver | None, OptimizationResult | None]:
    """Prove the primary optimum, then resolve the canonical tie-break.

    The tie-break is a lexicographic pass over binary indicators. Each indicator
    that is not already forced by the posted constraints needs its own proved
    solve, because its value depends on the whole remaining model. Indicators
    that *are* forced are resolved by implication under ``policy.skip_implied``;
    the selected values, and therefore the emitted result, are unchanged.
    """

    counters = policy.counters
    status, solver = _solve_once(state.model, problem, deadline, counters)
    solver, failure = _require_optimal(problem, status, solver)
    if failure is not None or solver is None:
        return None, failure

    primary_value = solver.value(state.primary_objective)
    state.model.add(state.primary_objective == primary_value)

    open_count = sum(state.open_facility.values())
    state.model.minimize(open_count)
    status, solver = _solve_once(state.model, problem, deadline, counters)
    solver, failure = _require_optimal(problem, status, solver)
    if failure is not None or solver is None:
        return None, failure
    minimum_open_count = solver.value(open_count)
    state.model.add(open_count == minimum_open_count)

    facility_ids = sorted(state.open_facility)
    open_values: dict[str, int] = {}
    selected_open = 0
    for index, facility_id in enumerate(facility_ids):
        if policy.skip_implied:
            remaining_slots = minimum_open_count - selected_open
            remaining_facilities = len(facility_ids) - index
            if remaining_slots == 0:
                # `open_count == minimum_open_count` forces every remaining
                # indicator to zero.
                counters.implied_skips += remaining_facilities
                break
            if remaining_slots == remaining_facilities:
                # Symmetrically, every remaining facility must open.
                counters.implied_skips += remaining_facilities
                for forced_id in facility_ids[index:]:
                    open_values[forced_id] = 1
                selected_open = minimum_open_count
                break
        variable = state.open_facility[facility_id]
        state.model.maximize(variable)
        status, solver = _solve_once(state.model, problem, deadline, counters)
        solver, failure = _require_optimal(problem, status, solver)
        if failure is not None or solver is None:
            return None, failure
        value = solver.value(variable)
        state.model.add(variable == value)
        open_values[facility_id] = value
        selected_open += value
        if selected_open == minimum_open_count:
            break
    for facility_id in facility_ids:
        val = open_values.setdefault(facility_id, 0)
        state.model.add(state.open_facility[facility_id] == val)

    scenarios = {scenario.scenario_id: scenario for scenario in problem.scenarios}
    demand_ids = sorted(demand.demand_id for demand in problem.demand_points)
    problem_facility_ids = sorted(facility.facility_id for facility in problem.facilities)

    if policy.skip_implied:
        counters.implied_skips += len(demand_ids) * len(scenarios) * len(problem_facility_ids)
        status, solver = _solve_once(state.model, problem, deadline, counters)
        solver, failure = _require_optimal(problem, status, solver)
        if failure is not None or solver is None:
            return None, failure
        return solver, None

    max_travel_seconds = problem.constraints.max_travel_seconds
    for scenario_id in sorted(scenarios):
        scenario = scenarios[scenario_id]
        for demand_id in demand_ids:
            uncovered = state.uncovered[(scenario_id, demand_id)]
            if policy.skip_implied and not problem.constraints.allow_uncovered_demand:
                # `uncovered_var == 0` is already posted for every demand point.
                counters.implied_skips += 1
                uncovered_value = 0
            else:
                state.model.minimize(uncovered)
                status, solver = _solve_once(state.model, problem, deadline, counters)
                solver, failure = _require_optimal(problem, status, solver)
                if failure is not None or solver is None:
                    return None, failure
                uncovered_value = solver.value(uncovered)
                state.model.add(uncovered == uncovered_value)
            if uncovered_value:
                continue

            if policy.skip_implied:
                # A closed facility forces `assign <= open == 0`, and an
                # over-limit duration is already pinned to zero, so neither can
                # ever win the lexicographic preference.
                candidates = [
                    facility_id
                    for facility_id in problem_facility_ids
                    if open_values[facility_id] and _duration(scenario, facility_id, demand_id) <= max_travel_seconds
                ]
                counters.implied_skips += len(problem_facility_ids) - len(candidates)
            else:
                candidates = problem_facility_ids

            for position, facility_id in enumerate(candidates):
                if policy.skip_implied and position == len(candidates) - 1:
                    # Every earlier candidate is pinned to zero and the row
                    # constraint `sum(assignments) + uncovered == 1` forces the
                    # last remaining candidate to one.
                    counters.implied_skips += 1
                    break
                variable = state.assigned[(scenario_id, facility_id, demand_id)]
                state.model.maximize(variable)
                status, solver = _solve_once(state.model, problem, deadline, counters)
                solver, failure = _require_optimal(problem, status, solver)
                if failure is not None or solver is None:
                    return None, failure
                value = solver.value(variable)
                state.model.add(variable == value)
                if value:
                    break
    return solver, None


def _weighted_p95(values: list[tuple[int, int]]) -> int:
    cumulative_probability = 0
    for value, probability in sorted(values):
        cumulative_probability += probability
        if cumulative_probability >= P95_BASIS_POINTS:
            return value
    raise AssertionError("validated scenario probabilities did not sum to one")


def _optimal_result(
    problem: OptimizationProblem,
    state: _ModelState,
    solver: cp_model.CpSolver,
) -> OptimizationResult:
    facilities = {facility.facility_id: facility for facility in problem.facilities}
    demands = {demand.demand_id: demand for demand in problem.demand_points}
    scenarios = {scenario.scenario_id: scenario for scenario in problem.scenarios}
    opened = tuple(facility_id for facility_id in sorted(facilities) if solver.value(state.open_facility[facility_id]))
    assignments: list[ScenarioAssignment] = []
    metrics: list[ScenarioMetrics] = []
    expected_travel = 0
    expected_uncovered = 0
    total_demand = sum(demand.demand_units for demand in demands.values())
    p95_values: list[tuple[int, int]] = []
    for scenario_id in sorted(scenarios):
        scenario = scenarios[scenario_id]
        uncovered_units = 0
        total_travel = 0
        for demand_id in sorted(demands):
            demand = demands[demand_id]
            if solver.value(state.uncovered[(scenario_id, demand_id)]):
                uncovered_units += demand.demand_units
                continue
            for facility_id in sorted(facilities):
                if solver.value(state.assigned[(scenario_id, facility_id, demand_id)]):
                    duration = _duration(scenario, facility_id, demand_id)
                    assignments.append(
                        ScenarioAssignment(
                            scenario_id=scenario_id,
                            facility_id=facility_id,
                            demand_id=demand_id,
                            assigned_demand_units=demand.demand_units,
                            travel_seconds=duration,
                        )
                    )
                    total_travel += demand.demand_units * duration
                    break
        covered_units = total_demand - uncovered_units
        coverage_basis_points = covered_units * BASIS_POINTS // total_demand
        metrics.append(
            ScenarioMetrics(
                scenario_id=scenario_id,
                probability_basis_points=scenario.probability_basis_points,
                covered_demand_units=covered_units,
                uncovered_demand_units=uncovered_units,
                coverage_basis_points=coverage_basis_points,
                total_travel_demand_seconds=total_travel,
            )
        )
        expected_travel += scenario.probability_basis_points * total_travel
        expected_uncovered += scenario.probability_basis_points * uncovered_units
        p95_values.append((total_travel, scenario.probability_basis_points))

    facility_cost = sum(facilities[facility_id].fixed_cost_units for facility_id in opened)
    failure_exposure = sum(
        facilities[facility_id].capacity_units * facilities[facility_id].failure_exposure_basis_points
        for facility_id in opened
    )
    p95_travel = _weighted_p95(p95_values)
    weights = problem.objective_weights
    weighted_total = (
        weights.expected_travel * expected_travel
        + weights.p95_travel * BASIS_POINTS * p95_travel
        + weights.facility_cost * BASIS_POINTS * facility_cost
        + weights.failure_exposure * failure_exposure
        + weights.coverage_loss * expected_uncovered
    )
    objective = ObjectiveBreakdown(
        weights=weights,
        expected_travel_probability_demand_seconds=expected_travel,
        p95_travel_demand_seconds=p95_travel,
        facility_cost_units=facility_cost,
        failure_exposure_capacity_basis_points=failure_exposure,
        expected_uncovered_probability_demand_units=expected_uncovered,
        weighted_total=weighted_total,
    )
    action = OptimizationAction.NO_ACTION if not opened else OptimizationAction.OPEN_FACILITIES
    return OptimizationResult(
        problem_id=problem.problem_id,
        problem_fingerprint=problem_fingerprint(problem),
        graph_version=problem.scenarios[0].travel_matrix.graph_version,
        assumption_version=problem.objective_weights.assumption_version,
        scenario_inputs=_scenario_input_lineage(problem),
        status=OptimizationStatus.OPTIMAL,
        action=action,
        fail_closed=False,
        opened_facility_ids=opened,
        assignments=tuple(assignments),
        scenario_metrics=tuple(metrics),
        objective=objective,
        solver_version=ortools.__version__,
        random_seed=problem.solver_settings.random_seed,
        message="CP-SAT proved the primary objective and deterministic tie-break optimal.",
    )


def optimize_facilities(
    problem: OptimizationProblem,
    *,
    skip_implied_solves: bool = True,
) -> OptimizationResult:
    """Solve a robust capacitated facility problem, returning only proved optima.

    Facility openings are shared across scenarios while assignments can adapt to
    each scenario.  Any FEASIBLE-but-unproved or timed-out solve is deliberately
    returned without candidate decisions.

    ``skip_implied_solves`` only controls whether forced tie-break indicators are
    resolved by implication instead of by a redundant proved solve. Both modes
    emit the same result; the flag exists so the equivalence can be tested.
    """

    return solve_with_counters(problem, skip_implied_solves=skip_implied_solves)[0]


def solve_with_counters(
    problem: OptimizationProblem,
    *,
    skip_implied_solves: bool = True,
) -> tuple[OptimizationResult, _SolveCounters]:
    """Solve and also report how much CP-SAT work the run actually cost."""

    policy = _TieBreakPolicy(skip_implied=skip_implied_solves)
    deadline = time.monotonic() + problem.solver_settings.max_time_seconds
    state = _build_model(problem)
    solver, failure = _canonical_solution(problem, state, deadline, policy)
    if failure is not None:
        return failure, policy.counters
    if solver is None:
        raise AssertionError("canonical solve returned neither a solver nor a failure")
    return _optimal_result(problem, state, solver), policy.counters
