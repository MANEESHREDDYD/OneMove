"""Pre-render the road basemap to a static raster.

The interactive layer (zones, facilities, scenario, optimization) stays live
SVG, but the roads are baked. 11k polylines re-parsed by the browser is the
kind of thing that renders blank on one run in ten, and a blank map in the
middle of a recording is unrecoverable. A raster either paints or is obviously
missing during the pre-flight gate.

Projection is plate carree with a cos(lat) correction on x, and MUST stay
identical to the frontend's projection or the overlay will not register with
the roads underneath.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = Path("public/demo/bengaluru-basemap.json")
OUT = Path("public/demo/bengaluru-roads.png")

W, H = 2560, 1440  # 2x the recording canvas, downscaled by the browser

# tier -> (colour, linewidth, z)
STYLE = {
    0: ("#93c5fd", 2.6, 5),   # motorway / trunk
    1: ("#60a5fa", 1.7, 4),   # primary
    2: ("#3b82f6", 1.05, 3),  # secondary
    3: ("#2563eb", 0.62, 2),  # tertiary
    4: ("#1e3a8a", 0.34, 1),  # residential
}


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    bb = d["bbox"]
    xs = math.cos(math.radians((bb["min_lat"] + bb["max_lat"]) / 2))

    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes((0, 0, 1, 1))
    fig.patch.set_facecolor("#060a12")
    ax.set_facecolor("#060a12")

    buckets: dict[int, list] = {t: [] for t in STYLE}
    for r in d["roads"]:
        buckets[r["t"]].append(r["p"])

    for tier in (4, 3, 2, 1, 0):
        colour, lw, z = STYLE[tier]
        segs = buckets[tier]
        # Arterials get a soft wide underlay so they read as spine roads.
        if tier <= 1:
            for p in segs:
                ax.plot([q[0] * xs for q in p], [q[1] for q in p],
                        color=colour, linewidth=lw * 3.2, alpha=0.13,
                        solid_capstyle="round", zorder=z)
        for p in segs:
            ax.plot([q[0] * xs for q in p], [q[1] for q in p],
                    color=colour, linewidth=lw, alpha=0.92,
                    solid_capstyle="round", zorder=z + 10)

    ax.set_xlim(bb["min_lon"] * xs, bb["max_lon"] * xs)
    ax.set_ylim(bb["min_lat"], bb["max_lat"])
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor="#060a12", dpi=100)
    print(f"{OUT}  {W}x{H}  {OUT.stat().st_size/1024:.0f} KB")
    print(f"projection x-scale (cos lat) = {xs:.9f}")
    print(f"bbox lat {bb['min_lat']}..{bb['max_lat']} lon {bb['min_lon']}..{bb['max_lon']}")


if __name__ == "__main__":
    main()
