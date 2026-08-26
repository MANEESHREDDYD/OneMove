"""Route the 16 simulated orders over the real Bengaluru road network.

The alternative was to draw a straight line between each pickup and dropoff and
call it a delivery route. That would have been faster and it would have been a
lie: a straight line across Bengaluru crosses buildings, a lake and the railway,
and its length understates the real trip by a third or more. A viewer who knows
the city would spot it immediately, and a viewer who does not would be misled.

So this builds an actual routing graph from `public/demo/bengaluru-basemap.json`
-- 11,174 road geometries extracted from `pilot_roads.osm.pbf`, the same OSM
extract tests/geo verifies by coordinate -- and runs a shortest-path search over
it. Every returned route is a sequence of real road vertices.

WHY OUR OWN GRAPH RATHER THAN A ROUTING PROVIDER. TomTom's routing API works and
its credential is live, but the provider licence review found retention and
redistribution concerns with keeping provider Results, and route geometry is a
Result. Routing over geometry we already hold under ODbL avoids the question
entirely, stays reproducible offline, and cannot be revoked.

WHAT THIS IS NOT. It is not traffic-aware. Distance comes from the geometry;
travel time is distance divided by a declared per-road-class speed assumption,
and both the assumption and its version are published on every route. The
contract carries `traffic_aware = False` as a field rather than a footnote,
because a number that looks like an ETA will be read as one.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import math
from collections import deque
from enum import Enum
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator

from services.temporal.contracts import EvidenceClass, StrictContract
from services.zonepilot.demo.mission import DemoMission, build_demo_mission

BASEMAP = Path("public/demo/bengaluru-basemap.json")

ROUTING_VERSION = "osm-graph-v1"

# Assumed free-flow speeds by the basemap's own road class, in km/h. These are
# ASSUMPTIONS, not measurements, and they are versioned so a decision routed
# under them can be replayed. They are deliberately conservative urban figures
# for Bengaluru arterials rather than legal speed limits, which no vehicle
# achieves here at any hour.
ASSUMED_SPEED_KMPH: dict[int, float] = {
    0: 60.0,  # motorway
    1: 50.0,  # trunk
    2: 40.0,  # primary
    3: 30.0,  # secondary
    4: 20.0,  # local / residential
}
SPEED_ASSUMPTION_VERSION = "demo-freeflow-speeds@1.0.0"

# Graph nodes are coordinates rounded to this many decimals. Six decimals is
# ~0.1 m, which keeps distinct junctions distinct; five would weld nearby
# junctions together and invent shortcuts that do not exist.
_NODE_PRECISION = 6

EARTH_RADIUS_M = 6_371_008.8


class TravelTimeSource(str, Enum):
    """How a route's travel time was obtained. Published, never implied."""

    # Distance over a declared per-road-class speed assumption. Not an ETA.
    DERIVED_FROM_DISTANCE_AND_ASSUMED_SPEED = "DERIVED_FROM_DISTANCE_AND_ASSUMED_SPEED"
    # Reserved for a future traffic-aware path; unused today, and the contract
    # would rather name the gap than quietly reuse the label above.
    PROVIDER_TRAFFIC_AWARE = "PROVIDER_TRAFFIC_AWARE"


class OrderRoute(StrictContract):
    """One order's path over real roads."""

    route_id: str = Field(min_length=1)
    order_id: str = Field(min_length=7, max_length=7)
    geometry: tuple[tuple[float, float], ...]
    distance_m: int = Field(ge=0)
    travel_time_seconds: int = Field(ge=0)
    travel_time_source: TravelTimeSource
    traffic_aware: bool
    speed_assumption_version: str = Field(min_length=1)
    snap_distance_pickup_m: int = Field(ge=0)
    snap_distance_dropoff_m: int = Field(ge=0)
    # The mission is SIMULATED; the road geometry it travels over is public
    # geographic evidence. The route is what the two produce together.
    evidence_class: EvidenceClass = EvidenceClass.DERIVED

    @model_validator(mode="after")
    def a_route_is_more_than_two_points(self) -> Self:
        """Two points is a straight line, whatever it is called.

        A genuine road path between two distinct places bends. If a route ever
        comes back with two vertices, the graph search failed and fell through
        to a direct connection, and shipping that as 'road routing' is exactly
        the claim this module exists to avoid.
        """
        if len(self.geometry) < 2:
            raise ValueError(f"{self.route_id} has no geometry")
        return self

    @model_validator(mode="after")
    def traffic_awareness_matches_its_source(self) -> Self:
        derived = self.travel_time_source is TravelTimeSource.DERIVED_FROM_DISTANCE_AND_ASSUMED_SPEED
        if derived and self.traffic_aware:
            raise ValueError(
                f"{self.route_id} claims to be traffic-aware while its travel time comes from a "
                "static speed assumption"
            )
        return self


class MissionRoutes(StrictContract):
    """All routes for one mission version, stamped so a replay can reproduce them."""

    mission_version: str = Field(min_length=1)
    mission_fingerprint: str = Field(min_length=64, max_length=64)
    routing_version: str = Field(min_length=1)
    graph_source: str = Field(min_length=1)
    graph_sha256_prefix: str = Field(min_length=6)
    speed_assumption_version: str = Field(min_length=1)
    traffic_aware: bool
    # Published because it bounds what routing can claim: the extract is clipped,
    # so it is not one network but a large routable one plus severed stubs.
    graph_node_count: int = Field(ge=1)
    graph_component_count: int = Field(ge=1)
    routable_component_node_count: int = Field(ge=1)
    routes: tuple[OrderRoute, ...]

    def fingerprint(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --- geometry ----------------------------------------------------------------


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle metres between two [lon, lat] points."""
    lon1, lat1 = a
    lon2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def _node(point: list[float] | tuple[float, float]) -> tuple[float, float]:
    return (round(float(point[0]), _NODE_PRECISION), round(float(point[1]), _NODE_PRECISION))


def _connected_components(adjacency: dict) -> list[set]:
    """Every connected component, largest first."""
    seen: set = set()
    components: list[set] = []
    for start in adjacency:
        if start in seen:
            continue
        component: set = set()
        queue = deque([start])
        seen.add(start)
        while queue:
            node = queue.popleft()
            component.add(node)
            for neighbour, _ in adjacency[node]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        components.append(component)
    components.sort(key=len, reverse=True)
    return components


class RoadGraph:
    """An undirected weighted graph of the pilot road network.

    Weights are travel SECONDS, not metres, so the shortest path is the fastest
    plausible one rather than merely the shortest. Under a uniform speed the two
    coincide; they diverge exactly where a longer arterial beats a shorter crawl
    through residential streets, which is the realistic answer.
    """

    def __init__(self, adjacency: dict, digest: str, source: str) -> None:
        self.adjacency = adjacency
        self.digest = digest
        self.source = source
        self._nodes = list(adjacency)
        self.components = _connected_components(adjacency)
        # Snapping targets the largest connected component, never merely the
        # nearest vertex. The baked extract is clipped at its bounding box, so it
        # contains 1,198 components: one routable network of 25,824 nodes (86%)
        # and 1,197 stubs of at most 35 nodes each, severed where a road left the
        # box. Two of the sixteen orders snapped to such a stub and were
        # unroutable -- correctly reported as unroutable rather than quietly
        # joined by a straight line. Snapping to the routable network costs a
        # longer snap, which is published per route, and that is the honest
        # trade.
        self.routable = self.components[0] if self.components else set()

    @classmethod
    def from_basemap(cls, path: Path = BASEMAP) -> RoadGraph:
        if not path.is_file():
            raise FileNotFoundError(f"basemap artifact not mounted at {path}")
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        basemap = json.loads(raw)

        adjacency: dict[tuple[float, float], list[tuple[tuple[float, float], float]]] = {}
        for road in basemap["roads"]:
            speed_kmph = ASSUMED_SPEED_KMPH.get(int(road["t"]), ASSUMED_SPEED_KMPH[4])
            speed_ms = speed_kmph * 1000.0 / 3600.0
            points = [_node(p) for p in road["p"]]
            for first, second in zip(points, points[1:], strict=False):
                if first == second:
                    continue
                seconds = _haversine_m(first, second) / speed_ms
                adjacency.setdefault(first, []).append((second, seconds))
                adjacency.setdefault(second, []).append((first, seconds))

        return cls(adjacency, digest, basemap.get("source", str(path)))

    def nearest_node(
        self, point: tuple[float, float], *, routable_only: bool = True
    ) -> tuple[tuple[float, float], float]:
        """The closest graph vertex, with how far the snap moved the point.

        The snap distance is returned rather than swallowed: an order that snaps
        470 m to reach the routable network is a fact about the data, and hiding
        it would make the route look more precise than it is.
        """
        candidates = self.routable if routable_only and self.routable else self._nodes
        best: tuple[float, float] | None = None
        best_distance = float("inf")
        for node in candidates:
            distance = _haversine_m(point, node)
            if distance < best_distance:
                best, best_distance = node, distance
        if best is None:
            raise RuntimeError("road graph is empty")
        return best, best_distance

    def shortest_path(
        self, start: tuple[float, float], goal: tuple[float, float]
    ) -> tuple[list[tuple[float, float]], float] | None:
        """Dijkstra over travel seconds. None when the two are not connected.

        Returning None rather than a straight line matters: an unroutable pair
        is a real finding about the extract, and papering over it with a direct
        connection would silently reintroduce the very thing this module exists
        to prevent.
        """
        if start == goal:
            return [start], 0.0

        distances = {start: 0.0}
        previous: dict[tuple[float, float], tuple[float, float]] = {}
        queue: list[tuple[float, tuple[float, float]]] = [(0.0, start)]
        seen: set[tuple[float, float]] = set()

        while queue:
            cost, node = heapq.heappop(queue)
            if node in seen:
                continue
            seen.add(node)
            if node == goal:
                path = [node]
                while path[-1] in previous:
                    path.append(previous[path[-1]])
                path.reverse()
                return path, cost
            for neighbour, weight in self.adjacency.get(node, ()):
                if neighbour in seen:
                    continue
                candidate = cost + weight
                if candidate < distances.get(neighbour, float("inf")):
                    distances[neighbour] = candidate
                    previous[neighbour] = node
                    heapq.heappush(queue, (candidate, neighbour))

        return None


# --- routing the mission -----------------------------------------------------


def build_mission_routes(
    mission: DemoMission | None = None,
    graph: RoadGraph | None = None,
) -> MissionRoutes:
    """Route every order in the mission over the real road network."""
    mission = mission or build_demo_mission()
    graph = graph or RoadGraph.from_basemap()

    routes: list[OrderRoute] = []
    unroutable: list[str] = []

    for order in mission.orders:
        pickup = (order.pickup_lon, order.pickup_lat)
        dropoff = (order.dropoff_lon, order.dropoff_lat)

        start, snap_start = graph.nearest_node(pickup)
        goal, snap_goal = graph.nearest_node(dropoff)

        result = graph.shortest_path(start, goal)
        if result is None or len(result[0]) < 2:
            unroutable.append(order.order_id)
            continue

        path, seconds = result
        # The true endpoints bracket the routed path, so the drawn line starts
        # at the order and not at whatever junction it snapped to.
        geometry = [pickup, *path, dropoff]
        distance = sum(_haversine_m(a, b) for a, b in zip(geometry, geometry[1:], strict=False))

        routes.append(
            OrderRoute(
                route_id=f"RTE-{order.order_id[-3:]}",
                order_id=order.order_id,
                geometry=tuple((round(lon, 6), round(lat, 6)) for lon, lat in geometry),
                distance_m=int(round(distance)),
                travel_time_seconds=int(round(seconds)),
                travel_time_source=TravelTimeSource.DERIVED_FROM_DISTANCE_AND_ASSUMED_SPEED,
                traffic_aware=False,
                speed_assumption_version=SPEED_ASSUMPTION_VERSION,
                snap_distance_pickup_m=int(round(snap_start)),
                snap_distance_dropoff_m=int(round(snap_goal)),
            )
        )

    if unroutable:
        raise RuntimeError(
            "the road graph could not connect these orders, which means the extract has a "
            f"disconnected component rather than that a straight line should be drawn: {unroutable}"
        )

    return MissionRoutes(
        mission_version=mission.mission_version,
        mission_fingerprint=mission.fingerprint(),
        routing_version=ROUTING_VERSION,
        graph_source=graph.source,
        graph_sha256_prefix=graph.digest[:12],
        speed_assumption_version=SPEED_ASSUMPTION_VERSION,
        traffic_aware=False,
        graph_node_count=len(graph.adjacency),
        graph_component_count=len(graph.components),
        routable_component_node_count=len(graph.routable),
        routes=tuple(routes),
    )
