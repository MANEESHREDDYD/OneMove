"""Fetch one real Bengaluru route for the simulated delivery mission.

The MISSION is simulated -- there is no order, no customer and no rider. The
ROUTE and its two travel times are real: they come from the routing provider
over Bengaluru's actual road network, one of them free-flow and one of them
traffic-aware. That contrast is the entire point of the segment, so neither
number may be invented.

Endpoints are a real candidate facility and a real demand zone from the pilot
network, both resolved from their H3 cells.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import h3

OUT = Path("public/demo/mission.json")

# Both are cells the optimizer actually reasons about.
ORIGIN_CELL = "8861892ec3fffff"      # a candidate facility zone in the north-east
DEST_CELL = "88618924a9fffff"        # a demand zone in the south-west, right across the pilot


def main() -> None:
    key = Path("C:/tmp/tomtom.key").read_text().strip()
    olat, olon = h3.cell_to_latlng(ORIGIN_CELL)
    dlat, dlon = h3.cell_to_latlng(DEST_CELL)

    url = (
        f"https://api.tomtom.com/routing/1/calculateRoute/"
        f"{olat},{olon}:{dlat},{dlon}/json"
        f"?key={key}&traffic=true&travelMode=motorcycle&routeType=fastest"
        f"&computeTravelTimeFor=all"
    )
    with urllib.request.urlopen(url, timeout=30) as r:
        doc = json.loads(r.read())

    route = doc["routes"][0]
    s = route["summary"]
    pts = [[round(p["longitude"], 5), round(p["latitude"], 5)] for p in route["legs"][0]["points"]]

    traffic_s = int(s["travelTimeInSeconds"])
    baseline_s = int(s["noTrafficTravelTimeInSeconds"])

    OUT.write_text(json.dumps({
        "mission_class": "SIMULATED",
        "route_evidence_class": "PROVIDER_ESTIMATED",
        "provider": "TomTom",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "origin": {"cell": ORIGIN_CELL, "lat": round(olat, 5), "lon": round(olon, 5)},
        "destination": {"cell": DEST_CELL, "lat": round(dlat, 5), "lon": round(dlon, 5)},
        "distance_m": int(s["lengthInMeters"]),
        "baseline_eta_s": baseline_s,
        "traffic_eta_s": traffic_s,
        # Reported as the difference between the provider's own traffic-aware and
        # free-flow times. trafficDelayInSeconds counts incident delay only and
        # is frequently 0 while the route is still materially slower.
        "delay_s": traffic_s - baseline_s,
        "congestion_ratio": round(traffic_s / baseline_s, 3) if baseline_s else None,
        "points": pts,
    }, separators=(",", ":")), encoding="utf-8")

    mm = lambda v: f"{v // 60}m {v % 60}s"
    print(f"distance ........... {s['lengthInMeters']:,} m")
    print(f"baseline ETA ....... {mm(baseline_s)}")
    print(f"traffic-aware ETA .. {mm(traffic_s)}")
    print(f"delay .............. +{mm(traffic_s - baseline_s)}  (x{traffic_s / baseline_s:.3f})")
    print(f"route points ....... {len(pts)}")


if __name__ == "__main__":
    main()
