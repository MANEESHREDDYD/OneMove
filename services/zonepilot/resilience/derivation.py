"""Turn an authentic travel matrix plus a scenario request into frozen inputs.

This module is the boundary where a caller's free-form scenario parameters meet
the routed network. It exists because of F-010: the engine previously accepted a
scenario, ignored its parameters entirely, and reported hardcoded operational
counts -- demand, zone, capacity, disconnection, redundancy and open-facility
totals -- as if they had been measured.

Two rules govern everything below.

1. **A disruption that cannot be applied is refused, not ignored.** An OSM way
   id or a rainfall depth cannot be translated into a facility x demand duration
   without a model this system does not have. Evaluating such a scenario against
   an undisturbed matrix would publish baseline numbers under a failure label,
   which is the same lie as inventing them. Those requests raise.
2. **A quantity nobody measured is UNAVAILABLE.** Facility capacity in
   particular has no source in ZonePilot: R1 carries no facility ledger. Unless
   the caller freezes an explicit capacity assumption, capacity-derived metrics
   are reported unavailable rather than defaulted.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from services.temporal.contracts import EvidenceClass
from services.zonepilot.optimization.contracts import TravelMatrix
from services.zonepilot.resilience.contracts import (
    BASIS_POINTS,
    CapacityAssumption,
    CoverageAssumption,
    FrozenScenarioInputs,
    ScenarioDisruption,
    ScenarioType,
)

#: Declared definition of "covered". A threshold is a definition, not data about
#: the world, so it carries a version and a stated source and is frozen into
#: every record it produces. Callers may override it per scenario.
DEFAULT_COVERAGE_ASSUMPTION = CoverageAssumption(
    assumption_id="r4-coverage-threshold-1.0.0",
    max_travel_seconds=1_800,
    source=(
        "ZonePilot R4 declared service-level definition: a demand zone counts as covered when its "
        "nearest available facility is reachable within 1800 routed seconds. Not an observed or "
        "contracted SLA."
    ),
)

#: Scenario parameters that can be mapped onto a facility x demand matrix.
REPRESENTABLE_PARAMETERS: frozenset[str] = frozenset(
    {
        "disabled_facility_ids",
        "unreachable_facility_demand_pairs",
        "travel_time_inflation_basis_points",
        "facility_capacity_basis_points",
        "coverage_max_travel_seconds",
        "coverage_assumption_source",
        "facility_capacity_units",
        "capacity_assumption_source",
    }
)

#: Which effect each scenario type must actually describe. A FACILITY_OUTAGE
#: that names no facility is not a failure scenario; it is the baseline wearing
#: a failure label.
REQUIRED_EFFECTS: dict[ScenarioType, tuple[str, ...]] = {
    ScenarioType.ROAD_CLOSURE: ("unreachable_facility_demand_pairs", "travel_time_inflation_basis_points"),
    ScenarioType.FACILITY_OUTAGE: ("disabled_facility_ids",),
    ScenarioType.CONGESTION_SPIKE: ("travel_time_inflation_basis_points",),
    ScenarioType.HEAVY_RAIN: ("travel_time_inflation_basis_points",),
    ScenarioType.CAPACITY_REDUCTION: ("facility_capacity_basis_points", "disabled_facility_ids"),
    ScenarioType.COMPOUND_FAILURE: (
        "disabled_facility_ids",
        "unreachable_facility_demand_pairs",
        "travel_time_inflation_basis_points",
        "facility_capacity_basis_points",
    ),
}

UNREPRESENTABLE_HELP = (
    "ZonePilot holds no model that maps these parameters onto the routed facility x demand travel "
    "matrix. Express the disruption at matrix granularity "
    "(disabled_facility_ids, unreachable_facility_demand_pairs, travel_time_inflation_basis_points, "
    "facility_capacity_basis_points) or the scenario cannot be evaluated."
)


class ScenarioNotRepresentable(ValueError):
    """The requested disruption cannot be applied to the authentic matrix."""


@dataclass(frozen=True)
class DerivedCounts:
    """Operational counts derived from the frozen inputs, or ``None``.

    ``None`` never means zero. Each ``None`` is paired with a reason by
    :func:`unavailability_reasons` so the metric that depends on it can say why
    it was not computed.
    """

    assigned_durations_seconds: tuple[int, ...]
    total_demands: int
    covered_demands: int | None
    zone_count: int
    disconnected_count: int
    redundant_facility_count: int | None
    total_open_facilities: int
    total_capacity: int | None
    lost_capacity: int | None
    coverage_unavailable_reason: str | None
    redundancy_unavailable_reason: str | None
    capacity_unavailable_reason: str | None


def _as_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScenarioNotRepresentable(f"{field} must be an integer, got {type(value).__name__}")
    return value


def _as_str_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ScenarioNotRepresentable(f"{field} must be a list of strings")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ScenarioNotRepresentable(f"{field} must contain non-blank strings")
        out.append(item)
    return tuple(out)


def _resolve_coverage_assumption(parameters: dict[str, Any]) -> CoverageAssumption:
    if "coverage_max_travel_seconds" not in parameters:
        return DEFAULT_COVERAGE_ASSUMPTION
    seconds = _as_int(parameters["coverage_max_travel_seconds"], "coverage_max_travel_seconds")
    source = parameters.get("coverage_assumption_source")
    if not isinstance(source, str) or not source.strip():
        raise ScenarioNotRepresentable(
            "coverage_max_travel_seconds overrides the declared coverage definition and therefore "
            "requires coverage_assumption_source naming where the threshold comes from"
        )
    return CoverageAssumption(
        assumption_id=f"r4-coverage-threshold-custom-{seconds}s",
        max_travel_seconds=seconds,
        source=source,
    )


def _resolve_capacity_assumption(parameters: dict[str, Any]) -> CapacityAssumption | None:
    if "facility_capacity_units" not in parameters:
        return None
    raw = parameters["facility_capacity_units"]
    if not isinstance(raw, dict):
        raise ScenarioNotRepresentable("facility_capacity_units must be a mapping of facility_id to units")
    source = parameters.get("capacity_assumption_source")
    if not isinstance(source, str) or not source.strip():
        raise ScenarioNotRepresentable(
            "facility_capacity_units is an assumption, not a measurement, and requires "
            "capacity_assumption_source naming its origin"
        )
    units = {str(key): _as_int(value, f"facility_capacity_units[{key}]") for key, value in raw.items()}
    digest = hashlib.sha256(json.dumps(units, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return CapacityAssumption(
        assumption_id=f"r4-capacity-ledger-{digest}",
        source=source,
        facility_capacity_units=units,
    )


def resolve_disruption(
    scenario_type: ScenarioType,
    parameters: dict[str, Any],
    *,
    facility_ids: tuple[str, ...],
    demand_ids: tuple[str, ...],
) -> ScenarioDisruption:
    """Map scenario parameters onto matrix-granular effects, or refuse."""
    unknown = sorted(set(parameters) - REPRESENTABLE_PARAMETERS)
    if unknown:
        raise ScenarioNotRepresentable(
            f"SCENARIO_NOT_REPRESENTABLE: unmodelled scenario parameters {unknown}. {UNREPRESENTABLE_HELP}"
        )

    known_facilities = set(facility_ids)
    known_demands = set(demand_ids)

    disabled = _as_str_tuple(parameters.get("disabled_facility_ids", ()), "disabled_facility_ids")
    missing = sorted(set(disabled) - known_facilities)
    if missing:
        raise ScenarioNotRepresentable(f"disabled_facility_ids names facilities absent from the matrix: {missing}")
    pairs_raw = parameters.get("unreachable_facility_demand_pairs", ())
    if not isinstance(pairs_raw, (list, tuple)):
        raise ScenarioNotRepresentable("unreachable_facility_demand_pairs must be a list of [facility_id, demand_id]")
    pairs: list[tuple[str, str]] = []
    for entry in pairs_raw:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ScenarioNotRepresentable("each unreachable pair must be [facility_id, demand_id]")
        facility_id, demand_id = str(entry[0]), str(entry[1])
        if facility_id not in known_facilities:
            raise ScenarioNotRepresentable(f"unreachable pair names unknown facility {facility_id}")
        if demand_id not in known_demands:
            raise ScenarioNotRepresentable(f"unreachable pair names unknown demand zone {demand_id}")
        pairs.append((facility_id, demand_id))

    inflation = _as_int(parameters.get("travel_time_inflation_basis_points", 0), "travel_time_inflation_basis_points")
    if inflation < 0:
        raise ScenarioNotRepresentable("travel_time_inflation_basis_points must not be negative")

    capacity_bps_raw = parameters.get("facility_capacity_basis_points", {})
    if not isinstance(capacity_bps_raw, dict):
        raise ScenarioNotRepresentable("facility_capacity_basis_points must be a mapping of facility_id to bps")
    capacity_bps: dict[str, int] = {}
    for key, value in capacity_bps_raw.items():
        facility_id = str(key)
        if facility_id not in known_facilities:
            raise ScenarioNotRepresentable(f"facility_capacity_basis_points names unknown facility {facility_id}")
        capacity_bps[facility_id] = _as_int(value, f"facility_capacity_basis_points[{facility_id}]")

    disruption = ScenarioDisruption(
        disabled_facility_ids=disabled,
        unreachable_pairs=tuple(pairs),
        travel_time_inflation_basis_points=inflation,
        facility_capacity_basis_points=capacity_bps,
    )

    if disruption.is_empty:
        required = REQUIRED_EFFECTS[scenario_type]
        raise ScenarioNotRepresentable(
            f"SCENARIO_NOT_REPRESENTABLE: {scenario_type.value} describes no effect on the routed network. "
            f"Supply at least one of {sorted(required)}; evaluating an undisturbed matrix would report the "
            "baseline as though it were the failure."
        )
    return disruption


def _inputs_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_frozen_inputs(
    matrix: TravelMatrix,
    *,
    scenario_type: ScenarioType,
    parameters: dict[str, Any],
) -> FrozenScenarioInputs:
    """Freeze the authentic matrix, the simulated disruption and the assumptions."""
    try:
        evidence = EvidenceClass(matrix.evidence_class.value)
    except ValueError as exc:
        raise ScenarioNotRepresentable(
            f"the supplied matrix claims evidence_class={matrix.evidence_class.value}, which is not a "
            "recognised evidence class for a routing baseline"
        ) from exc
    disruption = resolve_disruption(
        scenario_type,
        parameters,
        facility_ids=matrix.facility_ids,
        demand_ids=matrix.demand_ids,
    )
    coverage_assumption = _resolve_coverage_assumption(parameters)
    capacity_assumption = _resolve_capacity_assumption(parameters)

    digest = _inputs_digest(
        {
            "matrix_id": matrix.matrix_id,
            "graph_version": matrix.graph_version,
            "router": matrix.router,
            "router_version": matrix.router_version,
            "evidence_class": evidence.value,
            "facility_ids": list(matrix.facility_ids),
            "demand_ids": list(matrix.demand_ids),
            "durations": [list(row) for row in matrix.durations_seconds],
            "disruption": disruption.model_dump(mode="json"),
            "coverage_assumption": coverage_assumption.model_dump(mode="json"),
            "capacity_assumption": (
                None if capacity_assumption is None else capacity_assumption.model_dump(mode="json")
            ),
        }
    )

    return FrozenScenarioInputs(
        matrix_id=matrix.matrix_id,
        graph_version=matrix.graph_version,
        router=matrix.router,
        router_version=matrix.router_version,
        matrix_evidence_class=evidence,
        facility_ids=tuple(matrix.facility_ids),
        demand_ids=tuple(matrix.demand_ids),
        baseline_durations_seconds=tuple(tuple(int(d) for d in row) for row in matrix.durations_seconds),
        disruption=disruption,
        coverage_assumption=coverage_assumption,
        capacity_assumption=capacity_assumption,
        inputs_sha256=digest,
    )


def scenario_durations(inputs: FrozenScenarioInputs) -> tuple[tuple[int | None, ...], ...]:
    """Apply the SIMULATED disruption to the authentic baseline.

    ``None`` marks a pair the scenario makes unroutable; it is distinct from a
    long duration and is what makes ``disconnected_zones_count`` a real
    measurement rather than a constant.
    """
    disruption = inputs.disruption
    disabled = set(disruption.disabled_facility_ids)
    unreachable = set(disruption.unreachable_pairs)
    multiplier = BASIS_POINTS + disruption.travel_time_inflation_basis_points

    rows: list[tuple[int | None, ...]] = []
    for facility_id, row in zip(inputs.facility_ids, inputs.baseline_durations_seconds, strict=True):
        if facility_id in disabled:
            rows.append(tuple(None for _ in row))
            continue
        cells: list[int | None] = []
        for demand_id, base in zip(inputs.demand_ids, row, strict=True):
            if (facility_id, demand_id) in unreachable:
                cells.append(None)
            else:
                cells.append(math.ceil(base * multiplier / BASIS_POINTS))
        rows.append(tuple(cells))
    return tuple(rows)


def _covered_count(
    durations: tuple[tuple[int | None, ...], ...],
    open_indices: list[int],
    threshold: int,
) -> int:
    covered = 0
    for column in range(len(durations[0]) if durations else 0):
        for index in open_indices:
            value = durations[index][column]
            if value is not None and value <= threshold:
                covered += 1
                break
    return covered


def derive_counts(inputs: FrozenScenarioInputs) -> DerivedCounts:
    """Derive every operational count from the frozen inputs.

    Nothing here is a constant: demand and zone counts come from the matrix axes,
    reachability from the disrupted matrix, coverage from the declared threshold,
    redundancy from what each facility uniquely covers, and capacity strictly
    from a frozen capacity assumption when one exists.
    """
    durations = scenario_durations(inputs)
    disabled = set(inputs.disruption.disabled_facility_ids)
    open_indices = [index for index, fid in enumerate(inputs.facility_ids) if fid not in disabled]

    total_demands = len(inputs.demand_ids)
    zone_count = total_demands

    assigned: list[int] = []
    disconnected = 0
    for column in range(total_demands):
        reachable = [durations[index][column] for index in open_indices if durations[index][column] is not None]
        if reachable:
            assigned.append(min(value for value in reachable if value is not None))
        else:
            disconnected += 1

    threshold = inputs.coverage_assumption.max_travel_seconds if inputs.coverage_assumption else None
    coverage_unavailable_reason: str | None = None
    covered: int | None = None
    if threshold is None:
        coverage_unavailable_reason = (
            "no coverage assumption was frozen for this evaluation, so 'covered' has no definition here"
        )
    else:
        covered = _covered_count(durations, open_indices, threshold)

    # Redundancy: a facility is redundant when removing it would not reduce the
    # number of covered zones -- i.e. it is nobody's sole cover.
    redundancy_unavailable_reason: str | None = None
    redundant_facility_count: int | None = None
    if threshold is None:
        redundancy_unavailable_reason = (
            "redundancy is defined against the coverage threshold, which was not frozen for this evaluation"
        )
    elif not open_indices:
        redundancy_unavailable_reason = "the scenario leaves no facility open, so redundancy is not defined"
    else:
        baseline_covered = _covered_count(durations, open_indices, threshold)
        redundant = 0
        for index in open_indices:
            without = [other for other in open_indices if other != index]
            if _covered_count(durations, without, threshold) == baseline_covered:
                redundant += 1
        redundant_facility_count = redundant

    total_capacity, lost_capacity, capacity_unavailable_reason = _derive_capacity(inputs)

    return DerivedCounts(
        assigned_durations_seconds=tuple(sorted(assigned)),
        total_demands=total_demands,
        covered_demands=covered,
        zone_count=zone_count,
        disconnected_count=disconnected,
        redundant_facility_count=redundant_facility_count,
        total_open_facilities=len(open_indices),
        total_capacity=total_capacity,
        lost_capacity=lost_capacity,
        coverage_unavailable_reason=coverage_unavailable_reason,
        redundancy_unavailable_reason=redundancy_unavailable_reason,
        capacity_unavailable_reason=capacity_unavailable_reason,
    )


def _derive_capacity(inputs: FrozenScenarioInputs) -> tuple[int | None, int | None, str | None]:
    """Capacity is only ever derived from an explicitly frozen assumption.

    The one case that needs no ledger is a scenario that removes no capacity at
    all: nothing was taken away, so the fraction lost is zero whatever the total
    is. That is a derivation, not a placeholder, and it is the only zero this
    function will produce without a capacity source.
    """
    disruption = inputs.disruption
    assumption = inputs.capacity_assumption

    if assumption is None:
        if not disruption.affects_capacity:
            return None, 0, None
        return (
            None,
            None,
            (
                "the scenario removes facility capacity but no facility-capacity assumption was frozen; "
                "ZonePilot holds no observed facility capacity, so the fraction lost is unknown"
            ),
        )

    ledger = assumption.facility_capacity_units
    missing = sorted(set(inputs.facility_ids) - set(ledger))
    if missing:
        return (
            None,
            None,
            f"the frozen capacity assumption omits {len(missing)} matrix facilities (e.g. {missing[:3]}), "
            "so total capacity cannot be totalled",
        )

    total = sum(ledger[facility_id] for facility_id in inputs.facility_ids)
    lost = 0
    for facility_id in inputs.facility_ids:
        if facility_id in set(disruption.disabled_facility_ids):
            lost += ledger[facility_id]
            continue
        bps = disruption.facility_capacity_basis_points.get(facility_id)
        if bps is not None and bps < BASIS_POINTS:
            lost += (ledger[facility_id] * (BASIS_POINTS - bps)) // BASIS_POINTS
    return total, lost, None
