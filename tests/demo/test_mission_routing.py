"""A route drawn between two points is not a road route unless it follows roads.

The failure this guards against is cosmetic and therefore dangerous: a straight
line from pickup to dropoff renders perfectly well, looks deliberate, and
understates a Bengaluru trip by a third or more. These tests check the geometry
actually bends, that its endpoints are where the order is, and that the contract
never claims a traffic-awareness it does not have.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import pytest

BASEMAP = Path("public/demo/bengaluru-basemap.json")
DATA_ROOT = Path(os.environ.get("ZONEPILOT_DATA_ROOT", "data_root"))
GOLD = DATA_ROOT / "private" / "official" / "gold" / "gold_network_h3_8.parquet"

# Pinned so a change to the graph, the speed assumptions or the mission fails
# here rather than silently altering routes a frozen decision refers to.
EXPECTED_ROUTE_COUNT = 16


def _require_artifacts() -> None:
    if not BASEMAP.is_file():
        pytest.skip(f"basemap artifact not mounted at {BASEMAP}")
    if not GOLD.is_file():
        pytest.skip(f"gold network not mounted at {GOLD}")


@pytest.fixture(scope="module")
def graph():
    _require_artifacts()
    from services.zonepilot.demo.routing import RoadGraph

    return RoadGraph.from_basemap()


@pytest.fixture(scope="module")
def routes(graph):
    from services.zonepilot.demo.routing import build_mission_routes

    return build_mission_routes(graph=graph)


# --- the routes follow roads -------------------------------------------------


def test_every_order_is_routed(routes) -> None:
    from services.zonepilot.demo.mission import build_demo_mission

    assert len(routes.routes) == EXPECTED_ROUTE_COUNT
    assert {r.order_id for r in routes.routes} == {o.order_id for o in build_demo_mission().orders}


def test_no_route_is_a_straight_line(routes) -> None:
    """Two vertices between two distinct places means the graph search fell
    through to a direct connection. That is the defect, not a shortcut."""
    for route in routes.routes:
        assert len(route.geometry) > 2, (
            f"{route.route_id} has {len(route.geometry)} vertices, which is a straight line"
        )


def test_routes_are_longer_than_the_crow_flies(routes) -> None:
    """A road path cannot be shorter than the great-circle distance.

    If it were, the geometry is not tracing roads. The ratio is also reported
    upward: a road route across a dense city typically runs 1.2-1.6x the direct
    line, and a ratio pinned at almost exactly 1.0 would mean straight lines
    with extra vertices sprinkled on.
    """
    from services.zonepilot.demo.routing import _haversine_m

    ratios = []
    for route in routes.routes:
        direct = _haversine_m(route.geometry[0], route.geometry[-1])
        if direct < 50:  # an intra-cell hop; the ratio is meaningless at this scale
            continue
        assert route.distance_m >= direct * 0.99, (
            f"{route.route_id} is {route.distance_m} m along roads but {direct:.0f} m direct"
        )
        ratios.append(route.distance_m / direct)

    assert ratios, "expected at least one route long enough to compare"
    mean_ratio = sum(ratios) / len(ratios)
    assert mean_ratio > 1.05, (
        f"mean road-to-direct ratio is {mean_ratio:.3f}; routes that closely track the straight "
        "line are not following the road network"
    )


def test_route_geometry_stays_inside_bengaluru(routes) -> None:
    """Every vertex is a real road vertex, so every vertex is in the pilot area."""
    for route in routes.routes:
        for lon, lat in route.geometry:
            assert 12.70 <= lat <= 13.20, f"{route.route_id} vertex lat {lat} is not Bengaluru"
            assert 77.30 <= lon <= 77.90, f"{route.route_id} vertex lon {lon} is not Bengaluru"


def test_route_endpoints_are_the_order_not_the_snapped_junction(routes) -> None:
    """The drawn line must start at the order, not at whatever junction it
    snapped to, or the map shows a delivery beginning somewhere it does not."""
    from services.zonepilot.demo.mission import build_demo_mission
    from services.zonepilot.demo.routing import _haversine_m

    orders = {o.order_id: o for o in build_demo_mission().orders}
    for route in routes.routes:
        order = orders[route.order_id]
        assert _haversine_m(route.geometry[0], (order.pickup_lon, order.pickup_lat)) < 1.0
        assert _haversine_m(route.geometry[-1], (order.dropoff_lon, order.dropoff_lat)) < 1.0


def test_distances_are_plausible_for_a_city_this_size(routes) -> None:
    """A 500 km route inside a 16 km extract would mean the graph is looping."""
    for route in routes.routes:
        assert 0 < route.distance_m < 40_000, f"{route.route_id} is {route.distance_m} m"
        assert route.travel_time_seconds > 0


# --- the contract does not overclaim -----------------------------------------


def test_no_route_claims_to_be_traffic_aware(routes) -> None:
    """Travel time is distance over a static speed assumption. A number that
    looks like an ETA will be read as one, so the contract says what it is."""
    from services.zonepilot.demo.routing import TravelTimeSource

    assert routes.traffic_aware is False
    for route in routes.routes:
        assert route.traffic_aware is False
        assert route.travel_time_source is TravelTimeSource.DERIVED_FROM_DISTANCE_AND_ASSUMED_SPEED
        assert route.speed_assumption_version


def test_a_route_cannot_claim_traffic_awareness_it_does_not_have() -> None:
    """The contract refuses the inconsistent combination outright."""
    from pydantic import ValidationError

    from services.zonepilot.demo.routing import OrderRoute, TravelTimeSource

    fields = dict(
        route_id="RTE-001",
        order_id="ORD-001",
        geometry=((77.6, 12.9), (77.61, 12.91), (77.62, 12.92)),
        distance_m=1000,
        travel_time_seconds=120,
        travel_time_source=TravelTimeSource.DERIVED_FROM_DISTANCE_AND_ASSUMED_SPEED,
        speed_assumption_version="demo-freeflow-speeds@1.0.0",
        snap_distance_pickup_m=10,
        snap_distance_dropoff_m=10,
    )

    OrderRoute(**fields, traffic_aware=False)
    with pytest.raises(ValidationError, match="traffic-aware"):
        OrderRoute(**fields, traffic_aware=True)


def test_the_snap_distance_is_published_not_swallowed(routes) -> None:
    """An order that snaps 900 m to reach the routable network is a fact about
    the data. Hiding it makes the route look more precise than it is."""
    for route in routes.routes:
        assert route.snap_distance_pickup_m >= 0
        assert route.snap_distance_dropoff_m >= 0
    worst = max(max(r.snap_distance_pickup_m, r.snap_distance_dropoff_m) for r in routes.routes)
    assert worst > 0, "a snap distance of zero everywhere means it is not being measured"


# --- the graph's own limits are stated ---------------------------------------


def test_the_extract_is_reported_as_clipped_not_as_one_network(routes, graph) -> None:
    """The baked extract is cut at a bounding box, so it is a large routable
    network plus severed stubs. Two orders originally snapped to a stub and were
    correctly reported unroutable rather than joined by a straight line.

    Publishing the component structure is what stops 'routed on the real road
    network' from being read as more than it is.
    """
    assert routes.graph_component_count > 1, "a clipped extract is never a single component"
    assert routes.routable_component_node_count == len(graph.routable)
    share = routes.routable_component_node_count / routes.graph_node_count
    assert share > 0.5, f"the routable component holds only {share:.1%} of nodes"


def test_snapping_targets_the_routable_network_not_merely_the_nearest_stub(graph) -> None:
    """Nearest-vertex snapping put two of sixteen orders on a severed stub.

    This is the regression: for a point near a stub, the routable-only snap must
    return a node inside the routable component even when a closer node exists
    outside it.
    """
    stub_nodes = [n for component in graph.components[1:] for n in component]
    assert stub_nodes, "expected the clipped extract to contain stubs"

    probe = stub_nodes[0]
    routable_node, routable_distance = graph.nearest_node(probe, routable_only=True)
    any_node, any_distance = graph.nearest_node(probe, routable_only=False)

    assert routable_node in graph.routable
    assert any_node == probe and any_distance == pytest.approx(0.0, abs=1e-6)
    assert routable_distance > any_distance, (
        "the routable snap should be farther than the nearest-vertex snap; if it is not, "
        "the probe was not actually on a stub"
    )


# --- reproducibility ---------------------------------------------------------


def test_routing_is_deterministic(graph) -> None:
    """A frozen decision refers to these routes; they must not drift."""
    from services.zonepilot.demo.routing import build_mission_routes

    first = build_mission_routes(graph=graph)
    second = build_mission_routes(graph=graph)
    assert first.fingerprint() == second.fingerprint()
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_routes_are_bound_to_the_mission_and_graph_that_produced_them(routes) -> None:
    """Lineage, so a replay can tell whether it is comparing like with like."""
    from services.zonepilot.demo.mission import DEMO_MISSION_VERSION, build_demo_mission
    from services.zonepilot.demo.routing import ROUTING_VERSION

    assert routes.mission_version == DEMO_MISSION_VERSION
    assert routes.mission_fingerprint == build_demo_mission().fingerprint()
    assert routes.routing_version == ROUTING_VERSION
    assert routes.graph_sha256_prefix
    assert routes.graph_source


def test_travel_time_matches_the_declared_speed_assumption(routes) -> None:
    """Recompute the implied average speed and check it lies inside the declared
    band. A time that does not follow from the assumption is unexplainable."""
    from services.zonepilot.demo.routing import ASSUMED_SPEED_KMPH

    slowest = min(ASSUMED_SPEED_KMPH.values())
    fastest = max(ASSUMED_SPEED_KMPH.values())

    for route in routes.routes:
        if route.travel_time_seconds == 0:
            continue
        implied_kmph = (route.distance_m / 1000) / (route.travel_time_seconds / 3600)
        # Allow a margin: the drawn geometry includes the two snap legs, which
        # carry distance but no graph travel time.
        assert slowest * 0.5 <= implied_kmph <= fastest * 1.6, (
            f"{route.route_id} implies {implied_kmph:.1f} km/h, outside the declared "
            f"{slowest}-{fastest} km/h assumption band"
        )


def test_no_route_geometry_repeats_a_vertex_pathologically(routes) -> None:
    """A path that revisits the same vertex many times means the search is
    looping and the distance is inflated."""
    for route in routes.routes:
        unique = len(set(route.geometry))
        assert unique >= len(route.geometry) * 0.9, (
            f"{route.route_id} repeats vertices: {len(route.geometry)} points, {unique} unique"
        )


def test_haversine_is_correct_against_a_known_distance() -> None:
    """The distance function underpins every number above; check it separately.

    Bengaluru City Railway Station to Kempegowda International Airport is about
    30 km great-circle.
    """
    from services.zonepilot.demo.routing import _haversine_m

    station = (77.5701, 12.9784)
    airport = (77.7064, 13.1986)
    metres = _haversine_m(station, airport)
    assert 28_000 < metres < 32_000, f"got {metres:.0f} m, expected roughly 30 km"

    # And a degenerate pair must be exactly zero, not a rounding artefact.
    assert _haversine_m(station, station) == pytest.approx(0.0, abs=1e-9)
    assert not math.isnan(_haversine_m(station, airport))
