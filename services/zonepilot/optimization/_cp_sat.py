"""Internal deterministic robust facility optimizer using OR-Tools CP-SAT."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

import ortools
from ortools.sat.python import cp_model

from services.zonepilot.optimization.contracts import (
    BASIS_POINTS,
    P95_BASIS_POINTS,
    BaselineComparison,
    BaselineEvaluationStatus,
    BaselineInfeasibility,
    BaselinePolicyViolation,
    BaselineUnavailableReason,
    CapacityMode,
    DoNothingBaseline,
    ObjectiveBreakdown,
    ObjectiveComponent,
    ObjectiveComponentDelta,
    OptimizationAction,
    OptimizationProblem,
    OptimizationResult,
    OptimizationStatus,
    ScenarioAssignment,
    ScenarioInputLineage,
    ScenarioMetrics,
    UncertaintyScenario,
    baseline_comparison_unavailable,
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


# The solver minimises a fixed-point scaled form of the normalised objective.
# Every component is divided by a declared reference so it becomes dimensionless
# basis points before any weight applies; FIXED_POINT keeps that integer-exact
# inside CP-SAT, which cannot divide.
FIXED_POINT = 1_000_000


def _normalisation_references(problem: OptimizationProblem) -> dict[str, tuple[int, str]]:
    """Declared reference for each objective component, with its unit.

    Travel is referenced against the request's own ``max_travel_seconds``: the
    model already refuses any assignment slower than that, so the worst service
    it is willing to buy is the natural yardstick for how bad abandoning a zone
    is. Nothing here invents a business SLA.
    """
    total_demand = sum(d.demand_units for d in problem.demand_points)
    horizon = problem.constraints.max_travel_seconds
    all_facility_cost = sum(f.fixed_cost_units for f in problem.facilities)
    max_open = problem.constraints.max_open_facilities

    return {
        "expected_travel": (
            max(1, total_demand * BASIS_POINTS * horizon),
            "demand_units*probability_basis_points*seconds",
        ),
        "p95_travel": (max(1, total_demand * horizon), "demand_units*seconds"),
        "coverage_loss": (
            max(1, total_demand * BASIS_POINTS),
            "demand_units*probability_basis_points",
        ),
        "facility_cost": (max(1, all_facility_cost), "cost_units"),
        "failure_exposure": (max(1, max_open * BASIS_POINTS), "facility*basis_points"),
    }


def _solver_coefficient(weight: int, reference_value: int) -> int:
    """The exact integer multiplier CP-SAT applies to a component's raw value.

    Defined once and used by both the model and the published record, so the
    two can never drift. Flooring here rather than in the display path is what
    makes the published solver contribution reconcile with the solved objective.
    """
    return weight * BASIS_POINTS * FIXED_POINT // reference_value


def _component(
    name: str,
    raw_value: int,
    raw_unit: str,
    reference: tuple[int, str],
    weight: int,
) -> ObjectiveComponent:
    reference_value, reference_unit = reference
    coefficient = _solver_coefficient(weight, reference_value)
    normalized = raw_value * BASIS_POINTS // reference_value
    return ObjectiveComponent(
        name=name,
        raw_value=raw_value,
        raw_unit=raw_unit,
        normalization_reference=reference_value,
        normalization_reference_unit=reference_unit,
        weight=weight,
        solver_coefficient=coefficient,
        solver_scaled_contribution=coefficient * raw_value,
        normalized_basis_points=normalized,
        weighted_contribution=normalized * weight,
    )


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

        # Demand here is a PUBLIC_GEOGRAPHIC proxy (commercial POI counts), not
        # orders. Constraining it with a per-facility throughput number nobody
        # measured produced a binding constraint that made full service
        # arithmetically impossible while looking like a real operating limit.
        # Under NOT_MODELED no throughput constraint is posted at all.
        if problem.constraints.capacity_mode is CapacityMode.ASSUMPTION:
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
    # Exposure is a per-facility property derived from road density. Multiplying
    # it by capacity_units would smuggle the unsupported throughput number back
    # into the objective, so it is counted per opened facility instead.
    failure_exposure = sum(
        facilities[facility_id].failure_exposure_basis_points * opened[facility_id]
        for facility_id in facility_ids
    )

    weights = problem.objective_weights
    references = _normalisation_references(problem)

    # Each term is scaled by weight * BASIS_POINTS * FIXED_POINT / reference, which
    # is the integer-exact equivalent of normalising to basis points and then
    # weighting. Without this the objective added demand-unit-seconds to a
    # unit-less uncovered count, so abandoning a zone cost about the same as one
    # second of service and the solver correctly abandoned almost everything.
    def _coefficient(name: str, weight: int) -> int:
        reference_value, _ = references[name]
        return _solver_coefficient(weight, reference_value)

    primary_objective = (
        _coefficient("expected_travel", weights.expected_travel) * sum(expected_travel_terms)
        + _coefficient("p95_travel", weights.p95_travel) * q95_travel
        + _coefficient("facility_cost", weights.facility_cost) * facility_cost
        + _coefficient("failure_exposure", weights.failure_exposure) * failure_exposure
        + _coefficient("coverage_loss", weights.coverage_loss) * sum(expected_uncovered_terms)
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
        num_search_workers=problem.solver_settings.num_search_workers,
        # A fail-closed result still says what it cannot say. Leaving the field
        # empty would read as "no comparison was asked for" when the truth is
        # "there is no recommendation to compare".
        baseline_comparison=baseline_comparison_unavailable(
            BaselineUnavailableReason.NO_RECOMMENDATION,
            f"The solve returned {status.value} rather than a proved recommendation, so there "
            "is no configuration to compare the incumbent network against.",
            problem=problem,
        ),
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



def _canonical_assignment(
    problem: OptimizationProblem,
    scenario: UncertaintyScenario,
    demand_id: str,
    open_facilities: tuple[str, ...],
) -> tuple[str | None, int]:
    """Pick this demand point's facility by rule rather than by solver choice.

    When capacity is NOT_MODELED the demand points are uncoupled: nothing
    constrains two zones from using the same facility, so each one independently
    taking its cheapest feasible facility is not merely deterministic, it is
    optimal. Ties break on facility_id so the result cannot depend on dictionary
    order, scenario order, or which parallel worker happened to finish first.

    This is what makes the decision reproducible even when the optimum is found
    by parallel search. It is NOT valid under ASSUMPTION capacity, where the
    assignments are coupled through each facility's throughput limit.
    """
    cap = problem.constraints.max_travel_seconds
    best_facility: str | None = None
    best_duration = 0
    for facility_id in sorted(open_facilities):
        duration = _duration(scenario, facility_id, demand_id)
        if duration > cap:
            continue
        if best_facility is None or duration < best_duration:
            best_facility, best_duration = facility_id, duration
    return best_facility, best_duration


@dataclass(frozen=True)
class _OpenSetEvaluation:
    """Everything the objective says about ONE facility set.

    This exists so the recommendation and the do-nothing baseline are scored by
    the same code rather than by two implementations that agree until one of
    them is edited. Both sides go through :func:`_evaluate_open_set`, which is
    also the only place the published :class:`ObjectiveBreakdown` is built.
    """

    opened: tuple[str, ...]
    assignments: tuple[ScenarioAssignment, ...]
    scenario_metrics: tuple[ScenarioMetrics, ...]
    objective: ObjectiveBreakdown


# How a single demand point is served in one scenario: the facility that serves
# it and the routed seconds to reach it, or ``None`` when it is not served.
_AssignmentReader = Callable[[UncertaintyScenario, str], tuple[str | None, int]]


def _canonical_assignment_reader(
    problem: OptimizationProblem,
    opened: tuple[str, ...],
) -> _AssignmentReader:
    """Serve each zone from its nearest open facility within the travel cap.

    Valid only when capacity is NOT_MODELED -- see :func:`_canonical_assignment`
    for why. This is the reader the do-nothing baseline uses, and it is the same
    one the published recommendation uses in that mode, so neither side gets a
    private assignment rule.
    """

    def read(scenario: UncertaintyScenario, demand_id: str) -> tuple[str | None, int]:
        return _canonical_assignment(problem, scenario, demand_id, opened)

    return read


def _solver_assignment_reader(
    problem: OptimizationProblem,
    state: _ModelState,
    solver: cp_model.CpSolver,
) -> _AssignmentReader:
    """Read the assignments CP-SAT itself chose.

    ASSUMPTION capacity couples the zones through each facility's throughput
    limit, so the solver's own choice is the only correct one to read.
    """

    facility_ids = sorted(facility.facility_id for facility in problem.facilities)

    def read(scenario: UncertaintyScenario, demand_id: str) -> tuple[str | None, int]:
        if solver.value(state.uncovered[(scenario.scenario_id, demand_id)]):
            return None, 0
        for facility_id in facility_ids:
            if solver.value(state.assigned[(scenario.scenario_id, facility_id, demand_id)]):
                return facility_id, _duration(scenario, facility_id, demand_id)
        return None, 0

    return read


def _evaluate_open_set(
    problem: OptimizationProblem,
    opened: tuple[str, ...],
    assignment_for: _AssignmentReader,
) -> _OpenSetEvaluation:
    """Score one facility set under this problem's objective.

    The single source of the published objective arithmetic. It takes no
    solution status and no notion of optimality: it answers "what does this
    objective say about THIS set of open facilities", which is exactly the
    question both the recommendation and the do-nothing baseline ask.
    """

    facilities = {facility.facility_id: facility for facility in problem.facilities}
    demands = {demand.demand_id: demand for demand in problem.demand_points}
    scenarios = {scenario.scenario_id: scenario for scenario in problem.scenarios}

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
            facility_id, duration = assignment_for(scenario, demand_id)
            if facility_id is None:
                uncovered_units += demand.demand_units
                continue
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
    failure_exposure = sum(facilities[facility_id].failure_exposure_basis_points for facility_id in opened)
    p95_travel = _weighted_p95(p95_values)
    weights = problem.objective_weights
    references = _normalisation_references(problem)

    components = (
        _component(
            "expected_travel",
            expected_travel,
            "demand_units*probability_basis_points*seconds",
            references["expected_travel"],
            weights.expected_travel,
        ),
        _component(
            "p95_travel", p95_travel, "demand_units*seconds", references["p95_travel"], weights.p95_travel
        ),
        _component(
            "coverage_loss",
            expected_uncovered,
            "demand_units*probability_basis_points",
            references["coverage_loss"],
            weights.coverage_loss,
        ),
        _component(
            "facility_cost", facility_cost, "cost_units", references["facility_cost"], weights.facility_cost
        ),
        _component(
            "failure_exposure",
            failure_exposure,
            "basis_points",
            references["failure_exposure"],
            weights.failure_exposure,
        ),
    )
    # Invariant: the published total is the sum of the published contributions.
    # Nothing is added outside this list, so a reader can reconcile it by hand.
    weighted_total = sum(component.weighted_contribution for component in components)
    solver_objective_total = sum(component.solver_scaled_contribution for component in components)

    objective = ObjectiveBreakdown(
        weights=weights,
        expected_travel_probability_demand_seconds=expected_travel,
        p95_travel_demand_seconds=p95_travel,
        facility_cost_units=facility_cost,
        failure_exposure_capacity_basis_points=failure_exposure,
        expected_uncovered_probability_demand_units=expected_uncovered,
        weighted_total=weighted_total,
        components=components,
        normalization_scale=BASIS_POINTS,
        solver_scale=FIXED_POINT,
        solver_objective_total=solver_objective_total,
    )
    return _OpenSetEvaluation(
        opened=opened,
        assignments=tuple(assignments),
        scenario_metrics=tuple(metrics),
        objective=objective,
    )


def _worst_scenario(metrics: tuple[ScenarioMetrics, ...]) -> ScenarioMetrics:
    """The binding scenario for a service commitment, chosen the same way twice."""

    return min(metrics, key=lambda item: (item.coverage_basis_points, item.scenario_id))


def _improvement_basis_points(absolute_improvement: int, baseline_total: int) -> tuple[int | None, str | None]:
    """Improvement as a fraction of the baseline, in exact integer basis points.

    Truncated toward zero rather than floored, so a 0.5 bp regression reports as
    0 rather than as -1: a rounding rule that makes a regression look larger is
    as wrong as one that makes it look smaller.
    """

    if baseline_total <= 0:
        return None, (
            "the baseline objective is not strictly positive, so an improvement "
            "expressed as a fraction of it has no meaning"
        )
    scaled = absolute_improvement * BASIS_POINTS
    magnitude = abs(scaled) // baseline_total
    return (-magnitude if scaled < 0 else magnitude), None


def evaluate_do_nothing_baseline(
    problem: OptimizationProblem,
    result: OptimizationResult,
    baseline: DoNothingBaseline | None,
) -> BaselineComparison:
    """Score the incumbent network against the recommendation, or say why not.

    Both sides are scored by :func:`_evaluate_open_set` under the same problem,
    the same scenarios, the same travel matrices, the same weights and the same
    policy version, so the only difference between them is which facilities are
    open.
    """

    if baseline is None:
        return baseline_comparison_unavailable(
            BaselineUnavailableReason.NO_BASELINE_SUPPLIED,
            "No incumbent facility set was supplied. R1 carries no facility ledger -- "
            "its twelve facilities are candidate sites ranked by commercial POI density, "
            "not operating depots -- so there is nothing to derive one from, and inventing "
            "one would manufacture the number this comparison exists to test. Supply "
            "do_nothing_baseline to obtain the comparison.",
            problem=problem,
        )

    if result.status is not OptimizationStatus.OPTIMAL or result.objective is None:
        return baseline_comparison_unavailable(
            BaselineUnavailableReason.NO_RECOMMENDATION,
            f"The solve returned {result.status.value} rather than a proved recommendation, "
            "so there is no configuration to compare the incumbent network against.",
            problem=problem,
        )

    known = {facility.facility_id for facility in problem.facilities}
    unknown = sorted(set(baseline.facility_ids) - known)
    if unknown:
        return baseline_comparison_unavailable(
            BaselineUnavailableReason.UNKNOWN_FACILITY_IDS,
            "The incumbent set names facilities this problem does not contain "
            f"({', '.join(unknown)}), so they have no row in the travel matrix and "
            "cannot be scored under the same objective.",
            problem=problem,
        )

    if problem.constraints.capacity_mode is not CapacityMode.NOT_MODELED:
        return baseline_comparison_unavailable(
            BaselineUnavailableReason.CAPACITY_MODE_COUPLES_ASSIGNMENTS,
            f"capacity_mode is {problem.constraints.capacity_mode.value}, which couples every "
            "zone through a per-facility throughput limit. The canonical nearest-facility rule "
            "is documented as invalid under that mode, and allocating the incumbent network's "
            "load any other way would mean choosing an operating policy nobody has stated.",
            problem=problem,
        )

    opened = tuple(sorted(baseline.facility_ids))
    evaluation = _evaluate_open_set(problem, opened, _canonical_assignment_reader(problem, opened))

    constraints = problem.constraints
    facilities = {facility.facility_id: facility for facility in problem.facilities}
    baseline_cost = sum(facilities[facility_id].fixed_cost_units for facility_id in opened)

    violations: list[BaselinePolicyViolation] = []
    if len(opened) > constraints.max_open_facilities:
        violations.append(BaselinePolicyViolation.ABOVE_MAX_OPEN_FACILITIES)
    if len(opened) < constraints.min_open_facilities:
        violations.append(BaselinePolicyViolation.BELOW_MIN_OPEN_FACILITIES)
    if constraints.max_total_fixed_cost_units is not None and baseline_cost > constraints.max_total_fixed_cost_units:
        violations.append(BaselinePolicyViolation.ABOVE_MAX_TOTAL_FIXED_COST)

    total_demand = sum(demand.demand_units for demand in problem.demand_points)
    infeasibilities: list[BaselineInfeasibility] = []
    if not constraints.allow_uncovered_demand and any(
        metric.uncovered_demand_units for metric in evaluation.scenario_metrics
    ):
        infeasibilities.append(BaselineInfeasibility.UNCOVERED_DEMAND_NOT_PERMITTED)
    # Compared exactly the way the model posts it, not against the floored
    # display figure, so the flag and the constraint cannot disagree on a tie.
    if any(
        metric.covered_demand_units * BASIS_POINTS < total_demand * constraints.minimum_coverage_basis_points
        for metric in evaluation.scenario_metrics
    ):
        infeasibilities.append(BaselineInfeasibility.BELOW_MINIMUM_COVERAGE)

    recommended_components = {component.name: component for component in result.objective.components}
    deltas: list[ObjectiveComponentDelta] = []
    for component in evaluation.objective.components:
        recommended = recommended_components.get(component.name)
        if recommended is None:  # pragma: no cover - both sides come from _evaluate_open_set
            raise AssertionError(f"the recommendation publishes no {component.name!r} component")
        if recommended.solver_coefficient != component.solver_coefficient:  # pragma: no cover
            raise AssertionError(
                f"{component.name}: the two sides were scaled by different coefficients, so they "
                "were not measured with the same yardstick"
            )
        deltas.append(
            ObjectiveComponentDelta(
                name=component.name,
                raw_unit=component.raw_unit,
                solver_coefficient=component.solver_coefficient,
                baseline_raw_value=component.raw_value,
                recommended_raw_value=recommended.raw_value,
                baseline_solver_scaled_contribution=component.solver_scaled_contribution,
                recommended_solver_scaled_contribution=recommended.solver_scaled_contribution,
                solver_scaled_delta=recommended.solver_scaled_contribution - component.solver_scaled_contribution,
            )
        )

    baseline_total = evaluation.objective.solver_objective_total
    recommended_total = result.objective.solver_objective_total
    total_delta = recommended_total - baseline_total
    absolute_improvement = -total_delta
    improvement_basis_points, improvement_reason = _improvement_basis_points(absolute_improvement, baseline_total)

    baseline_worst = _worst_scenario(evaluation.scenario_metrics)
    recommended_worst = _worst_scenario(result.scenario_metrics)

    if absolute_improvement > 0:
        headline = "The recommendation improves on the incumbent network"
    elif absolute_improvement == 0:
        headline = "The recommendation scores exactly as the incumbent network does"
    else:
        headline = "The recommendation scores WORSE than the incumbent network"
    coverage_delta = recommended_worst.coverage_basis_points - baseline_worst.coverage_basis_points
    coverage_note = (
        f" Worst-scenario coverage moves {coverage_delta:+d} basis points "
        f"({baseline_worst.coverage_basis_points} -> {recommended_worst.coverage_basis_points})."
    )

    return BaselineComparison(
        status=BaselineEvaluationStatus.AVAILABLE,
        message=(
            f"{headline}: {baseline_total} -> {recommended_total} on the solver scale, "
            f"a {absolute_improvement} absolute change." + coverage_note
        ),
        baseline=baseline,
        baseline_within_policy=not violations,
        baseline_policy_violations=tuple(violations),
        baseline_feasible=not infeasibilities,
        baseline_infeasibilities=tuple(infeasibilities),
        baseline_facility_ids=opened,
        baseline_open_facility_count=len(opened),
        recommended_facility_ids=tuple(result.opened_facility_ids),
        recommended_open_facility_count=len(result.opened_facility_ids),
        baseline_solver_objective_total=baseline_total,
        recommended_solver_objective_total=recommended_total,
        total_solver_scaled_delta=total_delta,
        absolute_improvement=absolute_improvement,
        improvement_basis_points=improvement_basis_points,
        improvement_basis_points_unavailable_reason=improvement_reason,
        component_deltas=tuple(deltas),
        baseline_coverage_basis_points=baseline_worst.coverage_basis_points,
        recommended_coverage_basis_points=recommended_worst.coverage_basis_points,
        coverage_delta_basis_points=coverage_delta,
        baseline_uncovered_demand_units=baseline_worst.uncovered_demand_units,
        recommended_uncovered_demand_units=recommended_worst.uncovered_demand_units,
        baseline_scenario_metrics=evaluation.scenario_metrics,
        optimization_policy_version=problem.optimization_policy_version,
        assumption_version=problem.objective_weights.assumption_version,
        graph_version=problem.scenarios[0].travel_matrix.graph_version,
        solver_scale=FIXED_POINT,
    )


def _optimal_result(
    problem: OptimizationProblem,
    state: _ModelState,
    solver: cp_model.CpSolver,
) -> OptimizationResult:
    facilities = {facility.facility_id: facility for facility in problem.facilities}
    opened = tuple(facility_id for facility_id in sorted(facilities) if solver.value(state.open_facility[facility_id]))

    # NOT_MODELED leaves the zones uncoupled, so the canonical rule reproduces
    # the optimum exactly and does not depend on which worker finished first.
    # ASSUMPTION couples them through a throughput limit, where only the
    # solver's own choice is correct.
    if problem.constraints.capacity_mode is CapacityMode.NOT_MODELED:
        assignment_for = _canonical_assignment_reader(problem, opened)
    else:
        assignment_for = _solver_assignment_reader(problem, state, solver)

    evaluation = _evaluate_open_set(problem, opened, assignment_for)
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
        opened_facility_ids=evaluation.opened,
        assignments=evaluation.assignments,
        scenario_metrics=evaluation.scenario_metrics,
        objective=evaluation.objective,
        solver_version=ortools.__version__,
        random_seed=problem.solver_settings.random_seed,
        num_search_workers=problem.solver_settings.num_search_workers,
        message="CP-SAT proved the primary objective and deterministic tie-break optimal.",
    )


def optimize_facilities(
    problem: OptimizationProblem,
    *,
    skip_implied_solves: bool = True,
    baseline: DoNothingBaseline | None = None,
) -> OptimizationResult:
    """Solve a robust capacitated facility problem, returning only proved optima.

    Facility openings are shared across scenarios while assignments can adapt to
    each scenario.  Any FEASIBLE-but-unproved or timed-out solve is deliberately
    returned without candidate decisions.

    ``skip_implied_solves`` only controls whether forced tie-break indicators are
    resolved by implication instead of by a redundant proved solve. Both modes
    emit the same result; the flag exists so the equivalence can be tested.

    ``baseline`` is the incumbent facility set to report the recommendation
    against. It is an input because R1 records no such set; omitting it yields
    an UNAVAILABLE comparison carrying that reason, never a zero improvement.
    """

    return solve_with_counters(problem, skip_implied_solves=skip_implied_solves, baseline=baseline)[0]


def solve_with_counters(
    problem: OptimizationProblem,
    *,
    skip_implied_solves: bool = True,
    baseline: DoNothingBaseline | None = None,
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
    result = _optimal_result(problem, state, solver)
    comparison = evaluate_do_nothing_baseline(problem, result, baseline)
    return result.model_copy(update={"baseline_comparison": comparison}), policy.counters
