"""Fetch real live traffic for the pilot bbox and bake it into a map layer.

Two independent products from one provider:
  * flow raster tiles  -> the coloured congestion layer drawn over the roads
  * flowSegmentData    -> the numeric corridor readings shown in the panel

Both are PROVIDER_ESTIMATED and are stamped with the capture time so the UI can
say LIVE / FRESH / STALE from the timestamp rather than asserting it.
"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

BASEMAP = Path("public/demo/bengaluru-basemap.json")
OUT_PNG = Path("public/demo/bengaluru-traffic.png")
OUT_JSON = Path("public/demo/bengaluru-traffic.json")
ZOOM = 14

# Real, named Bengaluru arterials inside the pilot footprint. These are read
# from the provider one by one; nothing is averaged or invented.
CORRIDORS = [
    ("Outer Ring Road (Marathahalli)", 12.9560, 77.6970),
    ("Hosur Road (Silk Board)", 12.9170, 77.6230),
    ("Old Airport Road (Domlur)", 12.9610, 77.6390),
    ("100 Feet Road (Indiranagar)", 12.9720, 77.6410),
    ("MG Road / Trinity", 12.9740, 77.6190),
    ("Bannerghatta Road (Dairy Circle)", 12.9350, 77.5990),
]


def deg2tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


def tile2deg(x: int, y: int, z: int) -> tuple[float, float]:
    n = 2 ** z
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def main() -> None:
    key = Path("C:/tmp/tomtom.key").read_text().strip()
    bb = json.loads(BASEMAP.read_text(encoding="utf-8"))["bbox"]

    x0, y0 = deg2tile(bb["max_lat"], bb["min_lon"], ZOOM)
    x1, y1 = deg2tile(bb["min_lat"], bb["max_lon"], ZOOM)
    cols, rows = x1 - x0 + 1, y1 - y0 + 1
    mosaic = Image.new("RGBA", (cols * 256, rows * 256), (0, 0, 0, 0))

    fetched = 0
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            url = (f"https://api.tomtom.com/traffic/map/4/tile/flow/relative/"
                   f"{ZOOM}/{tx}/{ty}.png?key={key}&thickness=2")
            try:
                with urllib.request.urlopen(url, timeout=25) as r:
                    tile = Image.open(__import__("io").BytesIO(r.read())).convert("RGBA")
                mosaic.paste(tile, ((tx - x0) * 256, (ty - y0) * 256))
                fetched += 1
            except urllib.error.HTTPError as exc:
                print(f"  tile {tx}/{ty} HTTP {exc.code}")

    # Crop the mosaic to the exact basemap bbox so it registers with the roads.
    lat_tl, lon_tl = tile2deg(x0, y0, ZOOM)
    lat_br, lon_br = tile2deg(x1 + 1, y1 + 1, ZOOM)
    def px(lon: float) -> float:
        return (lon - lon_tl) / (lon_br - lon_tl) * mosaic.width

    def py(lat: float) -> float:
        return (lat - lat_tl) / (lat_br - lat_tl) * mosaic.height

    box = (int(px(bb["min_lon"])), int(py(bb["max_lat"])),
           int(px(bb["max_lon"])), int(py(bb["min_lat"])))
    mosaic.crop(box).resize((2560, 1440), Image.LANCZOS).save(OUT_PNG)

    captured = datetime.now(timezone.utc).isoformat()
    segments = []
    for name, lat, lon in CORRIDORS:
        url = (f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
               f"?key={key}&point={lat},{lon}")
        try:
            with urllib.request.urlopen(url, timeout=25) as r:
                f = json.loads(r.read())["flowSegmentData"]
        except Exception as exc:
            print(f"  corridor {name}: {exc}")
            continue
        cur, free = f["currentTravelTime"], f["freeFlowTravelTime"]
        segments.append({
            "name": name,
            "current_speed_kmh": f["currentSpeed"],
            "free_flow_speed_kmh": f["freeFlowSpeed"],
            "current_travel_s": cur,
            "free_flow_travel_s": free,
            "delay_s": cur - free,
            "congestion_ratio": round(cur / free, 3) if free else None,
            "confidence": f.get("confidence"),
            "road_closure": f.get("roadClosure"),
        })

    OUT_JSON.write_text(json.dumps({
        "provider": "TomTom",
        "product": "Traffic Flow (relative0 tiles + flowSegmentData)",
        "evidence_class": "PROVIDER_ESTIMATED",
        "captured_at": captured,
        "tiles_fetched": fetched,
        "zoom": ZOOM,
        "segments": segments,
    }, indent=1), encoding="utf-8")

    print(f"tiles ......... {fetched}/{cols*rows}")
    print(f"corridors ..... {len(segments)}/{len(CORRIDORS)}")
    for s in segments:
        print(f"  {s['name']:34} {s['current_speed_kmh']:>3} / {s['free_flow_speed_kmh']:>3} km/h"
              f"   x{s['congestion_ratio']}   +{s['delay_s']}s")
    print(f"{OUT_PNG} {OUT_PNG.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
