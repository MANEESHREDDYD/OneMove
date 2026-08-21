"""Render an offline Bengaluru basemap from the authentic pilot OSM extract.

The demo must not depend on a remote tile server: a blank map mid-recording is
worse than no map. This pre-renders road geometry from pilot_roads.osm.pbf into
a compact local asset the frontend can draw with no network access.

Nothing here invents geography. Every coordinate comes from the PBF.
"""

from __future__ import annotations

import json
from pathlib import Path

import h3
import osmium
import pandas as pd

PBF = Path("data/private/official/raw/osrm/pilot_roads.osm.pbf")
GOLD = Path("data/private/official/gold/gold_network_h3_8.parquet")
OUT = Path("public/demo/bengaluru-basemap.json")

# Road classes worth drawing, heaviest first. Anything else is dropped so the
# asset stays small enough to render at 25fps.
CLASS_WEIGHT = {
    "motorway": 0, "motorway_link": 0, "trunk": 0, "trunk_link": 0,
    "primary": 1, "primary_link": 1,
    "secondary": 2, "secondary_link": 2,
    "tertiary": 3, "tertiary_link": 3,
    "residential": 4, "unclassified": 4, "living_street": 4,
}


class Roads(osmium.SimpleHandler):
    def __init__(self, bbox):
        super().__init__()
        self.minlat, self.maxlat, self.minlon, self.maxlon = bbox
        self.ways: list[tuple[int, list[list[float]]]] = []
        self.named: dict[str, tuple[float, float]] = {}

    def way(self, w):
        hw = w.tags.get("highway")
        if hw not in CLASS_WEIGHT:
            return
        tier = CLASS_WEIGHT[hw]
        pts = []
        for n in w.nodes:
            try:
                la, lo = n.lat, n.lon
            except osmium.InvalidLocationError:
                continue
            if self.minlat <= la <= self.maxlat and self.minlon <= lo <= self.maxlon:
                pts.append([round(lo, 5), round(la, 5)])
        if len(pts) < 2:
            return
        # Drop collinear noise: residential streets carry far more vertices than
        # a 1920px canvas can resolve.
        if tier >= 4 and len(pts) > 4:
            pts = pts[::2]
        self.ways.append((tier, pts))
        name = w.tags.get("name")
        if name and tier <= 1 and name not in self.named:
            mid = pts[len(pts) // 2]
            self.named[name] = (mid[0], mid[1])


def main() -> None:
    cells = pd.read_parquet(GOLD)
    ids = cells["h3_index"].astype(str).tolist()

    boundaries = {i: [[round(lo, 5), round(la, 5)] for la, lo in h3.cell_to_boundary(i)] for i in ids}
    clat = [h3.cell_to_latlng(i)[0] for i in ids]
    clon = [h3.cell_to_latlng(i)[1] for i in ids]

    # The viewport is exactly 16:9 in PROJECTED units (degrees of longitude
    # scaled by cos(lat)), so the raster basemap and the SVG overlay share one
    # linear mapping and hexagons keep their true shape instead of stretching
    # into lozenges.
    #
    # The 94 zones are taller than the drivable extract is wide, so honouring
    # 16:9 leaves a margin left and right. That is deliberate: cropping to fill
    # the width would cut zones out of the network, and the side panels sit
    # over those margins anyway. Longitude is centred between the zone centroid
    # and the road centroid so the two margins come out even.
    import math as _m

    pad = 0.08
    lat_lo, lat_hi = min(clat), max(clat)
    lat_span = (lat_hi - lat_lo) * (1 + pad)
    lat_mid = (lat_lo + lat_hi) / 2
    xs = _m.cos(_m.radians(lat_mid))
    lon_span = lat_span * 16 / (9 * xs)
    # Nudged east so the facility cluster in the north of the pilot area lands
    # clear of the right-hand panel instead of under it.
    lon_mid = ((min(clon) + max(clon)) / 2 + 77.61910) / 2 + 0.005
    bbox = (
        lat_mid - lat_span / 2,
        lat_mid + lat_span / 2,
        lon_mid - lon_span / 2,
        lon_mid + lon_span / 2,
    )

    roads = Roads(bbox)
    roads.apply_file(str(PBF), locations=True)

    payload = {
        "source": "pilot_roads.osm.pbf",
        "source_sha256_prefix": "461584ea03d2",
        "evidence_class": "PUBLIC_GEOGRAPHIC",
        "bbox": {"min_lat": bbox[0], "max_lat": bbox[1], "min_lon": bbox[2], "max_lon": bbox[3]},
        "roads": [{"t": t, "p": p} for t, p in roads.ways],
        "labels": [{"name": n, "lon": c[0], "lat": c[1]} for n, c in sorted(roads.named.items())][:14],
        "zones": [
            {
                "h3": i,
                "b": boundaries[i],
                "c": [round(h3.cell_to_latlng(i)[1], 5), round(h3.cell_to_latlng(i)[0], 5)],
                "road_km": round(float(r.road_length_km), 2),
                "intersections": int(r.intersection_count),
                "pois": int(r.commercial_poi_count),
                "road_density": round(float(r.road_density_km_per_sqkm), 2),
            }
            for i, r in zip(ids, cells.itertuples())
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    print(f"roads drawn ......... {len(payload['roads']):,}")
    print(f"named arterials ..... {len(payload['labels'])}")
    print(f"zones ............... {len(payload['zones'])}")
    print(f"bbox ................ lat {bbox[0]:.4f}..{bbox[1]:.4f}  lon {bbox[2]:.4f}..{bbox[3]:.4f}")
    print(f"asset ............... {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
