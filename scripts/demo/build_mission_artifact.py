"""Bake the simulated mission and its routes into an artifact the page can read.

The mission is deterministic and the routing is deterministic, so this produces
byte-identical output for a given mission version and road graph. Generating it
once at build time rather than on every page load keeps a 30,040-node Dijkstra
out of the request path without making the result any less reproducible -- the
fingerprints travel with the artifact, so a frozen decision can still prove which
mission and which graph it referred to.

Nothing here is provider data. The orders are SIMULATED and the geometry is our
own ODbL extract, so unlike the TomTom rasters this artifact is safe to commit.
"""

from __future__ import annotations

import json
from pathlib import Path

from services.zonepilot.demo.mission import build_demo_mission
from services.zonepilot.demo.routing import RoadGraph, build_mission_routes

OUTPUT = Path("public/demo/mission-routes.json")


def main() -> int:
    mission = build_demo_mission()
    routes = build_mission_routes(mission=mission, graph=RoadGraph.from_basemap())

    payload = {
        "mission_version": mission.mission_version,
        "mission_fingerprint": mission.fingerprint(),
        "routes_fingerprint": routes.fingerprint(),
        "routing_version": routes.routing_version,
        "graph_source": routes.graph_source,
        "graph_sha256_prefix": routes.graph_sha256_prefix,
        "speed_assumption_version": routes.speed_assumption_version,
        # Carried into the UI so the interface can state it rather than the
        # narration having to remember to.
        "traffic_aware": routes.traffic_aware,
        "graph_component_count": routes.graph_component_count,
        "graph_node_count": routes.graph_node_count,
        "routable_component_node_count": routes.routable_component_node_count,
        "evidence_class": "SIMULATED",
        "orders": [
            {
                "order_id": order.order_id,
                "pickup": [order.pickup_lon, order.pickup_lat],
                "dropoff": [order.dropoff_lon, order.dropoff_lat],
                "pickup_h3": order.pickup_h3,
                "dropoff_h3": order.dropoff_h3,
                "priority": order.priority.value,
                "shape": order.shape.value,
                "created_at": order.created_at.isoformat(),
                "evidence_class": order.evidence_class.value,
            }
            for order in mission.orders
        ],
        "routes": [
            {
                "route_id": route.route_id,
                "order_id": route.order_id,
                "geometry": [list(point) for point in route.geometry],
                "distance_m": route.distance_m,
                "travel_time_seconds": route.travel_time_seconds,
                "travel_time_source": route.travel_time_source.value,
                "traffic_aware": route.traffic_aware,
                "snap_distance_pickup_m": route.snap_distance_pickup_m,
                "snap_distance_dropoff_m": route.snap_distance_dropoff_m,
                "evidence_class": route.evidence_class.value,
            }
            for route in routes.routes
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Newline-terminated, sorted, compact separators: identical inputs give an
    # identical file, so a rebuild that changes nothing produces no diff.
    OUTPUT.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"wrote {OUTPUT} ({size_kb:.0f} KB)")
    print(f"  mission {payload['mission_version']} fingerprint {payload['mission_fingerprint'][:12]}")
    print(f"  routes  {len(payload['routes'])} fingerprint {payload['routes_fingerprint'][:12]}")
    print(f"  traffic_aware={payload['traffic_aware']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
