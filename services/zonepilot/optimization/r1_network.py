"""Build optimizer inputs from the real R1 artifacts, not from fixtures.

What is real here, and what is not, is stated explicitly because the two must
never be confused:

* **Real, routed** — the travel matrix. Durations come from the versioned OSRM
  graph built from the pinned Geofabrik extract, queried over its ``/table``
  endpoint and quantized by ceiling to integer seconds. If OSRM cannot route a
  pair it returns ``null``; this module raises rather than substituting a
  straight-line estimate. ``TravelMatrix`` forbids a geographic fallback and
  that prohibition is honoured end to end.
* **Real, observed geography** — the zone set and the per-zone feature columns
  (road length, intersection count, POI counts) read from the Gold H3 R8
  Parquet artifact.
* **Assumption, derived from geography** — facility capacity, fixed cost, and
  failure exposure. R1 contains no facility ledger, no cost data, and no
  observed demand. These are transparent integer proxies computed from the real
  POI and road columns so the optimizer has a well-posed instance to solve.
  They carry an explicit ``assumption_version`` and support no claim about any
  real operation, cost, or outcome.
* **Simulated** — the degraded scenarios. Their matrices are labelled
  ``SIMULATED_FAILURE`` so a stress case can never be read as an observation.
"""

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Any, Protocol

import h3

from services.zonepilot.optimization.contracts import (
    BASIS_POINTS,
    DemandPoint,
    Facility,
    FacilityCapacityAdjustment,
    MatrixEvidenceClass,
    ObjectiveWeights,
    OptimizationConstraints,
    OptimizationProblem,
    SolverSettings,
    TravelMatrix,
    UncertaintyScenario,
)

R1_BBOX = "77.58,12.90,77.65,12.98"
R1_H3_RESOLUTION = 8
FACILITY_ID_PREFIX = "fac:"
DEMAND_ID_PREFIX = "zone:"

# The proxies below are assumptions, versioned so a later change is visible in
# every result lineage rather than silently altering past comparisons.
R1_ASSUMPTION_VERSION = "r1-geographic-proxy-1.0.0"


class R1NetworkUnavailable(RuntimeError):
    """A required R1 artifact or the routing service is not usable."""


class R1RoutingIncomplete(R1NetworkUnavailable):
    """The router could not produce a finite duration for every required pair."""


class ArtifactCatalog(Protocol):
    """The read-only slice of the artifact catalogue this adapter needs."""

    def gold_rows(self) -> list[dict[str, Any]]: ...
    def gold_manifest(self) -> dict[str, Any]: ...
    def osrm_build_manifest(self) -> dict[str, Any] | None: ...
    def osrm_graph_bundle_hash(self) -> str: ...


@dataclass(frozen=True)
class ScenarioSpec:
    """A named uncertainty scenario over the same routed graph.

    ``travel_inflation_basis_points`` scales the baseline routed durations;
    10_000 leaves them untouched. ``capacity_basis_points`` optionally derates
    the worst-exposed facilities to represent an outage.
    """

    scenario_id: str
    probability_basis_points: int
    travel_inflation_basis_points: int
    degraded_facility_count: int = 0
    degraded_capacity_basis_points: int = BASIS_POINTS


DEFAULT_SCENARIOS: tuple[ScenarioSpec, ...] = (
    ScenarioSpec(
        scenario_id="s1_free_flow",
        probability_basis_points=6_000,
        travel_inflation_basis_points=BASIS_POINTS,
    ),
    ScenarioSpec(
        scenario_id="s2_congested",
        probability_basis_points=3_000,
        travel_inflation_basis_points=14_000,
    ),
    ScenarioSpec(
        scenario_id="s3_congested_outage",
        probability_basis_points=1_000,
        travel_inflation_basis_points=16_000,
        degraded_facility_count=1,
        degraded_capacity_basis_points=0,
    ),
)


class OsrmTableClient:
    """Minimal client for a running ``osrm-routed`` table endpoint."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 120.0, profile: str = "driving") -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.profile = profile

    def durations_seconds(
        self,
        coordinates: list[tuple[float, float]],
        source_indices: list[int],
        destination_indices: list[int],
    ) -> list[list[float]]:
        """Return the routed duration sub-matrix, or raise.

        ``coordinates`` are ``(longitude, latitude)`` pairs in OSRM's own order.
        """

        import httpx

        coordinate_text = ";".join(f"{longitude:.6f},{latitude:.6f}" for longitude, latitude in coordinates)
        url = f"{self.base_url}/table/v1/{self.profile}/{coordinate_text}"
        params = {
            "sources": ";".join(str(index) for index in source_indices),
            "destinations": ";".join(str(index) for index in destination_indices),
            "annotations": "duration",
        }
        try:
            response = httpx.get(url, params=params, timeout=self.timeout_seconds)
        except httpx.HTTPError as exc:
            raise R1NetworkUnavailable(f"OSRM table request failed: {exc}") from exc
        if response.status_code != 200:
            raise R1NetworkUnavailable(f"OSRM table request returned HTTP {response.status_code}")
        payload = response.json()
        if payload.get("code") != "Ok":
            raise R1NetworkUnavailable(f"OSRM table request returned code {payload.get('code')!r}")
        durations = payload.get("durations")
        if not isinstance(durations, list) or len(durations) != len(source_indices):
            raise R1NetworkUnavailable("OSRM returned a table with unexpected dimensions")
        for row in durations:
            if not isinstance(row, list) or len(row) != len(destination_indices):
                raise R1NetworkUnavailable("OSRM returned a table with unexpected row width")
        return durations


def osrm_client_from_environment() -> OsrmTableClient:
    base_url = os.environ.get("ZONEPILOT_OSRM_URL")
    if not base_url:
        raise R1NetworkUnavailable(
            "ZONEPILOT_OSRM_URL is not set; the optimizer refuses to invent travel times without a router"
        )
    return OsrmTableClient(base_url)


def _ceil_positive_seconds(value: float, inflation_basis_points: int) -> int:
    """Quantize a routed duration to a strictly positive integer second count.

    Zero is reserved for a genuinely co-located pair; OSRM's self-pair duration
    is 0.0 and must stay 0 so a facility serving its own cell is free.
    """

    if value is None or not math.isfinite(value) or value < 0:
        raise R1RoutingIncomplete("OSRM produced a missing or non-finite duration; no fallback is permitted")
    inflated = value * inflation_basis_points / BASIS_POINTS
    return int(math.ceil(inflated - 1e-9))


def _router_version(catalog: ArtifactCatalog) -> str:
    manifest = catalog.osrm_build_manifest()
    if manifest and isinstance(manifest.get("image"), str) and manifest["image"].strip():
        return manifest["image"].strip()
    raise R1NetworkUnavailable("OSRM build manifest is missing; the router version cannot be established")


def _graph_version(catalog: ArtifactCatalog) -> str:
    manifest = catalog.gold_manifest()
    graph_version = manifest.get("graph_version")
    if not isinstance(graph_version, str) or not graph_version.strip():
        raise R1NetworkUnavailable("Gold manifest does not declare a graph_version")
    return graph_version.strip()


def _matrix_id(
    *,
    scenario_id: str,
    graph_version: str,
    router_version: str,
    graph_bundle_sha256: str,
    facility_ids: tuple[str, ...],
    demand_ids: tuple[str, ...],
    inflation_basis_points: int,
) -> str:
    digest = hashlib.sha256()
    for part in (
        "zonepilot.r1_travel_matrix",
        scenario_id,
        graph_version,
        router_version,
        graph_bundle_sha256,
        str(inflation_basis_points),
        "|".join(facility_ids),
        "|".join(demand_ids),
    ):
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return f"r1-matrix-{digest.hexdigest()[:32]}"


def _integer_column(row: dict[str, Any], column: str) -> int:
    value = row.get(column)
    if value is None:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError) as exc:
        raise R1NetworkUnavailable(f"Gold column {column!r} is not an integer") from exc


def _float_column(row: dict[str, Any], column: str) -> float:
    value = row.get(column)
    if value is None:
        return 0.0
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise R1NetworkUnavailable(f"Gold column {column!r} is not numeric") from exc
    if not math.isfinite(numeric):
        raise R1NetworkUnavailable(f"Gold column {column!r} is not finite")
    return numeric


@dataclass(frozen=True)
class R1ProblemBuild:
    """A built problem plus the shape facts a measured run should report."""

    problem: OptimizationProblem
    zone_count: int
    candidate_facility_count: int
    scenario_count: int
    graph_version: str
    router_version: str
    graph_bundle_sha256: str
    gold_dataset_version: str
    routed_pair_count: int


def build_r1_problem(
    *,
    catalog: ArtifactCatalog,
    osrm: OsrmTableClient,
    problem_id: str = "r1-bengaluru-pilot",
    zone_limit: int | None = None,
    candidate_facility_limit: int = 12,
    max_open_facilities: int = 4,
    min_open_facilities: int = 1,
    max_travel_seconds: int = 2_400,
    minimum_coverage_basis_points: int = BASIS_POINTS,
    scenarios: tuple[ScenarioSpec, ...] = DEFAULT_SCENARIOS,
    objective_weights: ObjectiveWeights | None = None,
    solver_settings: SolverSettings | None = None,
) -> R1ProblemBuild:
    """Assemble a real R1-derived :class:`OptimizationProblem`.

    ``zone_limit`` and ``candidate_facility_limit`` exist because the canonical
    tie-break cost grows with ``scenarios x zones x facilities``; they select a
    deterministic prefix of the real zone set rather than fabricating a smaller
    one. Leaving ``zone_limit`` as ``None`` uses every Gold zone.
    """

    rows = catalog.gold_rows()
    if not rows:
        raise R1NetworkUnavailable("Gold network artifact contains no H3 rows")
    rows = sorted(rows, key=lambda row: str(row["h3_index"]))
    if zone_limit is not None:
        if zone_limit < 1:
            raise ValueError("zone_limit must be positive")
        rows = rows[:zone_limit]

    graph_version = _graph_version(catalog)
    router_version = _router_version(catalog)
    graph_bundle_sha256 = catalog.osrm_graph_bundle_hash()
    gold_manifest = catalog.gold_manifest()
    gold_dataset_version = str(gold_manifest.get("dataset_version", "unknown"))

    zone_ids = [str(row["h3_index"]) for row in rows]
    coordinates: list[tuple[float, float]] = []
    for zone_id in zone_ids:
        latitude, longitude = h3.cell_to_latlng(zone_id)
        coordinates.append((longitude, latitude))

    # Candidate facilities: the zones with the most real commercial POIs, then
    # by H3 index so the selection is total and reproducible.
    ranked = sorted(
        range(len(rows)),
        key=lambda index: (-_integer_column(rows[index], "commercial_poi_count"), zone_ids[index]),
    )
    if candidate_facility_limit < 1:
        raise ValueError("candidate_facility_limit must be positive")
    facility_indices = sorted(ranked[:candidate_facility_limit])
    if not facility_indices:
        raise R1NetworkUnavailable("No candidate facility zones could be selected")

    demand_points: list[DemandPoint] = []
    for index, row in enumerate(rows):
        # Demand proxy: real commercial POI count, floored at one so every real
        # zone must still be served. This is an assumption, not observed demand.
        units = max(1, _integer_column(row, "commercial_poi_count"))
        demand_points.append(DemandPoint(demand_id=f"{DEMAND_ID_PREFIX}{zone_ids[index]}", demand_units=units))
    total_demand = sum(point.demand_units for point in demand_points)

    facilities: list[Facility] = []
    for index in facility_indices:
        row = rows[index]
        # Capacity proxy: enough that a small open set can cover the pilot, tied
        # to the zone's real commercial density so the ranking is geographic.
        density = _float_column(row, "road_density_km_per_sqkm")
        capacity = max(1, int(math.ceil(total_demand * 0.60)))
        # Exposure proxy: sparser road networks are treated as more exposed.
        exposure = max(0, min(BASIS_POINTS, int(round((1.0 / (1.0 + density)) * BASIS_POINTS))))
        cost = 1_000 + 10 * _integer_column(row, "intersection_count")
        facilities.append(
            Facility(
                facility_id=f"{FACILITY_ID_PREFIX}{zone_ids[index]}",
                capacity_units=capacity,
                fixed_cost_units=cost,
                failure_exposure_basis_points=exposure,
            )
        )

    facility_ids = tuple(facility.facility_id for facility in facilities)
    demand_ids = tuple(point.demand_id for point in demand_points)

    baseline = osrm.durations_seconds(
        coordinates,
        source_indices=facility_indices,
        destination_indices=list(range(len(rows))),
    )
    routed_pair_count = len(facility_indices) * len(rows)

    # Exposure ranking drives which facilities a simulated outage hits, so the
    # degraded scenario is reproducible rather than arbitrary.
    exposure_ranking = [
        facility.facility_id
        for facility in sorted(facilities, key=lambda item: (-item.failure_exposure_basis_points, item.facility_id))
    ]

    built_scenarios: list[UncertaintyScenario] = []
    for spec in scenarios:
        durations = tuple(
            tuple(_ceil_positive_seconds(value, spec.travel_inflation_basis_points) for value in row)
            for row in baseline
        )
        is_baseline = spec.travel_inflation_basis_points == BASIS_POINTS and spec.degraded_facility_count == 0
        evidence_class = (
            MatrixEvidenceClass.PUBLIC_GEOGRAPHIC if is_baseline else MatrixEvidenceClass.SIMULATED_FAILURE
        )
        matrix = TravelMatrix(
            matrix_id=_matrix_id(
                scenario_id=spec.scenario_id,
                graph_version=graph_version,
                router_version=router_version,
                graph_bundle_sha256=graph_bundle_sha256,
                facility_ids=facility_ids,
                demand_ids=demand_ids,
                inflation_basis_points=spec.travel_inflation_basis_points,
            ),
            graph_version=graph_version,
            router="OSRM",
            router_version=router_version,
            evidence_class=evidence_class,
            facility_ids=facility_ids,
            demand_ids=demand_ids,
            durations_seconds=durations,
        )
        adjustments = tuple(
            FacilityCapacityAdjustment(
                facility_id=facility_id,
                available_capacity_basis_points=spec.degraded_capacity_basis_points,
            )
            for facility_id in exposure_ranking[: spec.degraded_facility_count]
        )
        built_scenarios.append(
            UncertaintyScenario(
                scenario_id=spec.scenario_id,
                probability_basis_points=spec.probability_basis_points,
                travel_matrix=matrix,
                capacity_adjustments=adjustments,
            )
        )

    weights = objective_weights or ObjectiveWeights(
        assumption_version=R1_ASSUMPTION_VERSION,
        expected_travel=1,
        p95_travel=1,
        facility_cost=1,
        failure_exposure=1,
        coverage_loss=1,
    )
    constraints = OptimizationConstraints(
        min_open_facilities=min_open_facilities,
        max_open_facilities=min(max_open_facilities, len(facilities)),
        max_travel_seconds=max_travel_seconds,
        minimum_coverage_basis_points=minimum_coverage_basis_points,
        allow_uncovered_demand=False,
        allow_no_action=False,
    )
    problem = OptimizationProblem(
        problem_id=problem_id,
        facilities=tuple(facilities),
        demand_points=tuple(demand_points),
        scenarios=tuple(built_scenarios),
        constraints=constraints,
        objective_weights=weights,
        solver_settings=solver_settings or SolverSettings(),
    )
    return R1ProblemBuild(
        problem=problem,
        zone_count=len(rows),
        candidate_facility_count=len(facilities),
        scenario_count=len(built_scenarios),
        graph_version=graph_version,
        router_version=router_version,
        graph_bundle_sha256=graph_bundle_sha256,
        gold_dataset_version=gold_dataset_version,
        routed_pair_count=routed_pair_count,
    )
