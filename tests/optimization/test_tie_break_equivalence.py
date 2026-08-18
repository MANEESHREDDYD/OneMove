"""The implied-solve optimisation must not move a single byte of the result.

The canonical tie-break resolves a lexicographic family of binary indicators,
one proved CP-SAT solve at a time. Many of those indicators are already
*uniquely forced* by constraints the model is carrying, so their solve can only
ever report the one admissible value. ``skip_implied_solves`` resolves those by
implication instead.

That is only a safe trade if it is an identity, not an approximation. These
tests run the same problem through both modes and compare the serialised
results byte for byte, across problem shapes chosen to exercise every skip rule
in ``_cp_sat._canonical_solution``:

* facilities forced closed once the open count is met,
* facilities forced open when the remaining slots equal the remaining choices,
* ``uncovered == 0`` posted up front when uncovered demand is disallowed,
* assignment candidates pinned to zero by a closed facility or an over-limit
  duration,
* the last surviving candidate in a row forced to one.

A byte comparison is used deliberately: field-by-field assertions would let a
reordered tuple or a changed lineage field slip through, and downstream
consumers (A4 resilience) treat this contract as stable.
"""

from __future__ import annotations

import random

import pytest

from services.zonepilot.optimization.contracts import (
    DemandPoint,
    Facility,
    FacilityCapacityAdjustment,
    MatrixEvidenceClass,
    ObjectiveWeights,
    OptimizationConstraints,
    OptimizationProblem,
    OptimizationStatus,
    SolverSettings,
    TravelMatrix,
    UncertaintyScenario,
)
from services.zonepilot.optimization.solver import optimize_facilities_with_telemetry


def _matrix(
    matrix_id: str,
    facility_ids: tuple[str, ...],
    demand_ids: tuple[str, ...],
    durations: tuple[tuple[int, ...], ...],
) -> TravelMatrix:
    return TravelMatrix(
        matrix_id=matrix_id,
        graph_version="graph-equivalence.1",
        router="osrm-adapter",
        router_version="1.0.0",
        evidence_class=MatrixEvidenceClass.TEST_ONLY,
        facility_ids=facility_ids,
        demand_ids=demand_ids,
        durations_seconds=durations,
    )


def _random_problem(
    seed: int,
    *,
    facility_count: int,
    demand_count: int,
    scenario_count: int,
    allow_uncovered_demand: bool,
    max_travel_seconds: int,
    max_open_facilities: int,
) -> OptimizationProblem:
    """Build a deterministic pseudo-random but always-valid problem."""

    generator = random.Random(seed)
    facility_ids = tuple(f"f{index}" for index in range(facility_count))
    demand_ids = tuple(f"d{index}" for index in range(demand_count))

    facilities = tuple(
        Facility(
            facility_id=facility_id,
            # Generous enough that coverage is usually achievable, so the
            # assignment tie-break is actually exercised rather than short
            # circuited by infeasibility.
            capacity_units=generator.randint(demand_count, demand_count * 3),
            fixed_cost_units=generator.randint(0, 40),
            failure_exposure_basis_points=generator.randint(0, 2_000),
        )
        for facility_id in facility_ids
    )
    demands = tuple(
        DemandPoint(demand_id=demand_id, demand_units=generator.randint(1, 3)) for demand_id in demand_ids
    )

    # Scenario probabilities must sum to exactly BASIS_POINTS.
    probabilities = [10_000 // scenario_count] * scenario_count
    probabilities[0] += 10_000 - sum(probabilities)

    scenarios = []
    for scenario_index in range(scenario_count):
        durations = tuple(
            tuple(generator.randint(1, 900) for _ in demand_ids) for _ in facility_ids
        )
        adjustments: tuple[FacilityCapacityAdjustment, ...] = ()
        if scenario_index and facility_count > 1:
            # Derate one facility so capacity recourse differs across scenarios.
            adjustments = (
                FacilityCapacityAdjustment(
                    facility_id=facility_ids[scenario_index % facility_count],
                    available_capacity_basis_points=generator.choice((0, 3_000, 6_000)),
                ),
            )
        scenarios.append(
            UncertaintyScenario(
                scenario_id=f"s{scenario_index}",
                probability_basis_points=probabilities[scenario_index],
                travel_matrix=_matrix(
                    f"m{seed}-{scenario_index}", facility_ids, demand_ids, durations
                ),
                capacity_adjustments=adjustments,
            )
        )

    return OptimizationProblem(
        problem_id=f"equivalence-{seed}",
        facilities=facilities,
        demand_points=demands,
        scenarios=tuple(scenarios),
        constraints=OptimizationConstraints(
            min_open_facilities=1,
            max_open_facilities=min(max_open_facilities, facility_count),
            max_travel_seconds=max_travel_seconds,
            minimum_coverage_basis_points=0 if allow_uncovered_demand else 10_000,
            allow_uncovered_demand=allow_uncovered_demand,
        ),
        objective_weights=ObjectiveWeights(
            assumption_version="equivalence-assumptions-v1",
            expected_travel=1,
            p95_travel=1,
            facility_cost=1,
            failure_exposure=1,
            coverage_loss=1,
        ),
        solver_settings=SolverSettings(max_time_seconds=30.0),
    )


# (facility_count, demand_count, scenario_count, allow_uncovered, max_travel, max_open)
#
# ``max_travel_seconds=400`` against durations drawn from 1..900 pins a large
# share of assignment variables to zero at build time, which is exactly the
# candidate-filter skip rule. The 900 cases leave every facility reachable so
# the "last surviving candidate" rule dominates instead.
_SHAPES = (
    (3, 3, 2, False, 900, 3),
    (4, 4, 2, False, 400, 2),
    (4, 3, 3, False, 900, 2),
    (3, 4, 2, True, 400, 3),
    (5, 3, 2, False, 900, 1),
    (2, 5, 2, False, 900, 2),
)


@pytest.mark.parametrize("shape_index", range(len(_SHAPES)))
@pytest.mark.parametrize("seed", range(3))
def test_implied_skipping_is_byte_identical_to_the_full_tie_break(shape_index: int, seed: int):
    facility_count, demand_count, scenario_count, allow_uncovered, max_travel, max_open = _SHAPES[shape_index]
    problem = _random_problem(
        seed * 100 + shape_index,
        facility_count=facility_count,
        demand_count=demand_count,
        scenario_count=scenario_count,
        allow_uncovered_demand=allow_uncovered,
        max_travel_seconds=max_travel,
        max_open_facilities=max_open,
    )

    legacy_result, legacy_telemetry = optimize_facilities_with_telemetry(problem, legacy_tie_break=True)
    fast_result, fast_telemetry = optimize_facilities_with_telemetry(problem, legacy_tie_break=False)

    # The decision contract must be identical, not merely equivalent.
    assert fast_result.model_dump_json() == legacy_result.model_dump_json()

    assert legacy_telemetry is not None
    assert fast_telemetry is not None
    # The optimisation must never cost *more* solves than the full tie-break.
    assert fast_telemetry.cp_sat_solve_count <= legacy_telemetry.cp_sat_solve_count
    # The legacy mode is the reference: it resolves nothing by implication.
    assert legacy_telemetry.implied_solves_skipped == 0


def test_implied_skipping_actually_removes_solves_on_a_feasible_problem():
    """Guard against the optimisation silently degrading into a no-op."""

    problem = _random_problem(
        7,
        facility_count=4,
        demand_count=4,
        scenario_count=2,
        allow_uncovered_demand=False,
        max_travel_seconds=900,
        max_open_facilities=2,
    )

    legacy_result, legacy_telemetry = optimize_facilities_with_telemetry(problem, legacy_tie_break=True)
    fast_result, fast_telemetry = optimize_facilities_with_telemetry(problem, legacy_tie_break=False)

    assert legacy_result.status is OptimizationStatus.OPTIMAL
    assert fast_result.model_dump_json() == legacy_result.model_dump_json()
    assert legacy_telemetry is not None
    assert fast_telemetry is not None
    assert fast_telemetry.implied_solves_skipped > 0
    assert fast_telemetry.cp_sat_solve_count < legacy_telemetry.cp_sat_solve_count
