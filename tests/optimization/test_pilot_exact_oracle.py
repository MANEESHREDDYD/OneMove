"""Independent exact certification of the pilot optimum.

The pilot offers 12 candidate facilities and opens at most 4, so the feasible
facility sets number only 794. That is small enough to enumerate exhaustively
and compute the objective independently of CP-SAT, which turns "the solver says
OPTIMAL" into "an independent method agrees on the optimum".

The oracle re-derives the objective from the published contract rather than
importing the model builder, so a defect in the model construction cannot hide
by being shared with its own verifier. Concretely, this file restates the fixed
point scale and all five normalisation references as its own literals and
formulas; it imports no arithmetic from `_cp_sat`. An earlier version of this
docstring claimed that independence while the file actually imported
`FIXED_POINT` and `_normalisation_references` from the module under test, which
made the claim false: a wrong reference would have been applied identically on
both sides and cancelled out.

The independence is not silent. `test_oracle_references_match_the_model_builder`
compares this file's independent derivation against the model builder's, so the
two are proved equal rather than assumed equal, and a change to either surfaces
as a failure instead of a shared blind spot.

Scope, stated so it cannot be overclaimed: the oracle certifies the OBJECTIVE
VALUE and the OPTIMAL FACILITY SET by exhaustive enumeration. It does not
certify the solver's constraint encoding beyond what the objective and the
feasibility rule expose. It is a test-only device and never substitutes for the
production solver.
"""

from __future__ import annotations

import itertools
import os
from pathlib import Path

import pytest

DATA_ROOT = Path(os.environ.get("ZONEPILOT_DATA_ROOT", "data_root"))
MATRIX = DATA_ROOT / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"

BASIS_POINTS = 10_000
P95_BASIS_POINTS = 9_500

# Restated here as literals, deliberately NOT imported from the module under
# test. If the model builder changes its fixed-point scale, this file must fail
# rather than follow it silently.
ORACLE_FIXED_POINT = 1_000_000


def _oracle_references(problem) -> dict[str, int]:
    """Independently derive each component's normalisation reference.

    Re-derived from the problem contract -- total demand units, the travel cap,
    the total fixed cost of every candidate facility, and the facility-count
    ceiling -- not read from `_cp_sat._normalisation_references`. Duplication is
    the point: it is what makes the comparison in
    `test_oracle_references_match_the_model_builder` an actual check.
    """
    total_demand = sum(d.demand_units for d in problem.demand_points)
    horizon = problem.constraints.max_travel_seconds
    all_facility_cost = sum(f.fixed_cost_units for f in problem.facilities)
    max_open = problem.constraints.max_open_facilities

    return {
        "expected_travel": max(1, total_demand * BASIS_POINTS * horizon),
        "p95_travel": max(1, total_demand * horizon),
        "coverage_loss": max(1, total_demand * BASIS_POINTS),
        "facility_cost": max(1, all_facility_cost),
        "failure_exposure": max(1, max_open * BASIS_POINTS),
    }


def _problem():
    if not MATRIX.is_file():
        pytest.skip(f"authentic travel matrix not mounted at {MATRIX}")
    from services.api.routers.observatory import OptimizationRequest, _build_real_94x12x3_problem

    return _build_real_94x12x3_problem(
        OptimizationRequest(allow_uncovered_demand=False, max_open_facilities=4)
    )


def _oracle_objective(problem, open_set: frozenset[str]) -> int | None:
    """Exact solver-scale objective for one facility set, or None if infeasible.

    Mirrors the published contract: each demand point takes its cheapest open
    facility within the travel cap, and each component is multiplied by the same
    integer coefficient the solver record publishes.
    """
    demands = {d.demand_id: d.demand_units for d in problem.demand_points}
    facilities = {f.facility_id: f for f in problem.facilities}
    cap = problem.constraints.max_travel_seconds

    expected_travel = 0
    expected_uncovered = 0
    per_scenario_totals: list[tuple[int, int]] = []

    for scenario in problem.scenarios:
        matrix = scenario.travel_matrix
        f_index = {fid: i for i, fid in enumerate(matrix.facility_ids)}
        d_index = {did: j for j, did in enumerate(matrix.demand_ids)}
        scenario_travel = 0
        uncovered_units = 0

        for demand_id, units in demands.items():
            best = None
            for facility_id in open_set:
                duration = matrix.durations_seconds[f_index[facility_id]][d_index[demand_id]]
                if duration <= cap and (best is None or duration < best):
                    best = duration
            if best is None:
                if not problem.constraints.allow_uncovered_demand:
                    return None  # this facility set cannot serve every zone
                uncovered_units += units
            else:
                scenario_travel += units * best

        expected_travel += scenario.probability_basis_points * scenario_travel
        expected_uncovered += scenario.probability_basis_points * uncovered_units
        per_scenario_totals.append((scenario_travel, scenario.probability_basis_points))

    cumulative = 0
    p95 = 0
    for value, probability in sorted(per_scenario_totals):
        cumulative += probability
        if cumulative >= P95_BASIS_POINTS:
            p95 = value
            break

    facility_cost = sum(facilities[f].fixed_cost_units for f in open_set)
    failure_exposure = sum(facilities[f].failure_exposure_basis_points for f in open_set)

    references = _oracle_references(problem)
    weights = problem.objective_weights

    def coefficient(name: str, weight: int) -> int:
        return weight * BASIS_POINTS * ORACLE_FIXED_POINT // references[name]

    return (
        coefficient("expected_travel", weights.expected_travel) * expected_travel
        + coefficient("p95_travel", weights.p95_travel) * p95
        + coefficient("coverage_loss", weights.coverage_loss) * expected_uncovered
        + coefficient("facility_cost", weights.facility_cost) * facility_cost
        + coefficient("failure_exposure", weights.failure_exposure) * failure_exposure
    )


def _enumerate(problem) -> tuple[int, list[frozenset[str]]]:
    """Exhaustive optimum over every permitted facility subset."""
    ids = sorted(f.facility_id for f in problem.facilities)
    low = problem.constraints.min_open_facilities
    high = problem.constraints.max_open_facilities

    best_value: int | None = None
    best_sets: list[frozenset[str]] = []
    for size in range(low, high + 1):
        for combo in itertools.combinations(ids, size):
            value = _oracle_objective(problem, frozenset(combo))
            if value is None:
                continue
            if best_value is None or value < best_value:
                best_value, best_sets = value, [frozenset(combo)]
            elif value == best_value:
                best_sets.append(frozenset(combo))
    assert best_value is not None, "no permitted facility set could serve the network"
    return best_value, best_sets


def test_oracle_finds_a_feasible_full_service_configuration() -> None:
    """Full service must be achievable; if not, the fixture is wrong."""
    problem = _problem()
    best_value, best_sets = _enumerate(problem)
    assert best_value > 0
    assert best_sets
    assert all(len(s) <= problem.constraints.max_open_facilities for s in best_sets)


def test_oracle_search_space_is_small_enough_to_be_exhaustive() -> None:
    """State the certification's own scope, so it cannot be overclaimed."""
    problem = _problem()
    n = len(problem.facilities)
    low = problem.constraints.min_open_facilities
    high = problem.constraints.max_open_facilities
    subsets = sum(len(list(itertools.combinations(range(n), k))) for k in range(low, high + 1))
    assert n == 12
    assert subsets < 1_000, f"{subsets} subsets is too many for exhaustive certification"


@pytest.mark.slow
def test_cp_sat_optimum_matches_the_independent_oracle() -> None:
    """CP-SAT's proven optimum must equal the exhaustive optimum.

    Multi-worker search is used here only to obtain the optimal VALUE for
    comparison. It is not how a decision is produced; production keeps the
    single-worker canonical path.
    """
    from ortools.sat.python import cp_model

    from services.zonepilot.optimization import _cp_sat as cpsat

    problem = _problem()
    oracle_value, oracle_sets = _enumerate(problem)

    state = cpsat._build_model(problem)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 120.0
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = problem.solver_settings.random_seed
    status = solver.solve(state.model)

    assert status == cp_model.OPTIMAL, f"expected OPTIMAL, got {solver.status_name(status)}"
    assert int(solver.objective_value) == oracle_value, (
        f"CP-SAT optimum {int(solver.objective_value):,} != oracle optimum {oracle_value:,}"
    )

    chosen = frozenset(f for f in state.open_facility if solver.value(state.open_facility[f]))
    assert chosen in oracle_sets, "CP-SAT selected a set the oracle does not rank as optimal"


def _assignment_hash(result) -> str:
    import hashlib

    lines = [
        f"{a.scenario_id}|{a.facility_id}|{a.demand_id}|{a.travel_seconds}"
        for a in sorted(result.assignments, key=lambda a: (a.scenario_id, a.demand_id))
    ]
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


@pytest.mark.slow
def test_decision_is_reproducible_under_parallel_search() -> None:
    """The decision must not depend on which parallel worker finished first.

    Assignments are reconstructed by a canonical rule rather than read from the
    solver, so once the facility set is fixed the result is fully determined.
    Measured across repeated runs: identical facility set, identical assignment
    hash, identical objective.
    """
    from ortools.sat.python import cp_model

    from services.zonepilot.optimization import _cp_sat as cpsat

    problem = _problem()
    oracle_value, _ = _enumerate(problem)

    facility_sets = set()
    assignment_hashes = set()
    objectives = set()

    for _ in range(5):
        state = cpsat._build_model(problem)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60.0
        solver.parameters.num_search_workers = 8
        solver.parameters.random_seed = problem.solver_settings.random_seed
        assert solver.solve(state.model) == cp_model.OPTIMAL

        result = cpsat._optimal_result(problem, state, solver)
        facility_sets.add(tuple(sorted(result.opened_facility_ids)))
        assignment_hashes.add(_assignment_hash(result))
        objectives.add(result.objective.solver_objective_total)

    assert len(facility_sets) == 1, f"facility set varied across runs: {facility_sets}"
    assert len(assignment_hashes) == 1, "assignment hash varied across runs"
    assert len(objectives) == 1, "objective varied across runs"
    assert objectives.pop() == oracle_value, "solved objective disagrees with the exact oracle"


def test_canonical_assignment_breaks_ties_on_facility_id() -> None:
    """Equal durations must resolve the same way every time, by id order."""
    from services.zonepilot.optimization._cp_sat import _canonical_assignment

    problem = _problem()
    scenario = problem.scenarios[0]
    demand_id = sorted(d.demand_id for d in problem.demand_points)[0]
    all_facilities = tuple(f.facility_id for f in problem.facilities)

    forward = _canonical_assignment(problem, scenario, demand_id, all_facilities)
    reversed_order = _canonical_assignment(problem, scenario, demand_id, tuple(reversed(all_facilities)))
    assert forward == reversed_order, "assignment depended on input ordering"


def test_oracle_references_match_the_model_builder() -> None:
    """The oracle's independent derivation must equal the model builder's.

    This is what turns the independence above from an assertion in prose into a
    checked property. The oracle derives its five normalisation references and
    its fixed-point scale from the problem contract alone; the model builder
    derives its own. They must agree exactly. If they ever diverge, one of the
    two is wrong and this test says so -- which is precisely the failure mode
    that sharing the import used to hide.
    """
    from services.zonepilot.optimization._cp_sat import (
        FIXED_POINT,
        _normalisation_references,
    )

    problem = _problem()

    assert ORACLE_FIXED_POINT == FIXED_POINT, (
        f"oracle fixed point {ORACLE_FIXED_POINT:,} != model {FIXED_POINT:,}; "
        "the model's scale changed and the oracle was not updated"
    )

    model_references = _normalisation_references(problem)
    oracle_references = _oracle_references(problem)

    assert set(oracle_references) == set(model_references), (
        "oracle and model disagree about which components are normalised"
    )
    for name, oracle_value in oracle_references.items():
        model_value, _unit = model_references[name]
        assert oracle_value == model_value, (
            f"{name}: oracle reference {oracle_value:,} != model reference {model_value:,}"
        )
