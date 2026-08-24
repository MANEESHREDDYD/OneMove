"""Independent exact certification of the pilot optimum.

The pilot offers 12 candidate facilities and opens at most 4, so the feasible
facility sets number only 794. That is small enough to enumerate exhaustively
and compute the objective independently of CP-SAT, which turns "the solver says
OPTIMAL" into "an independent method agrees on the optimum".

The oracle deliberately re-derives the objective from the published contract
rather than importing the model builder, so a defect in the model construction
cannot hide by being shared with its own verifier. It is a test-only device and
never substitutes for the production solver.
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
    from services.zonepilot.optimization._cp_sat import FIXED_POINT, _normalisation_references

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

    references = _normalisation_references(problem)
    weights = problem.objective_weights

    def coefficient(name: str, weight: int) -> int:
        reference_value, _ = references[name]
        return weight * BASIS_POINTS * FIXED_POINT // reference_value

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
