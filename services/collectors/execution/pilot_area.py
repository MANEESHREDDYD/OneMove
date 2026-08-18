"""The R1 pilot area, expressed once so every collector samples the same cells."""

from __future__ import annotations

from functools import lru_cache

import h3

# Bengaluru R1 pilot corridor, matching services/collectors/gold.py and dq.py.
PILOT_BBOX = (77.58, 12.90, 77.65, 12.98)  # west, south, east, north
PILOT_H3_RESOLUTION = 8
# Center-containment over the bbox yields exactly this many R8 cells. Asserting
# the count keeps an h3 upgrade from silently resizing the pilot area.
PILOT_CELL_COUNT = 94


@lru_cache(maxsize=1)
def pilot_cells() -> tuple[str, ...]:
    """Return the pilot area's H3 R8 cells, sorted for deterministic ordering."""

    west, south, east, north = PILOT_BBOX
    boundary = [(south, west), (south, east), (north, east), (north, west), (south, west)]
    cells = h3.polygon_to_cells(h3.LatLngPoly(boundary), PILOT_H3_RESOLUTION)
    ordered = tuple(sorted(cells))
    if len(ordered) != PILOT_CELL_COUNT:
        raise RuntimeError(
            f"pilot area resolved to {len(ordered)} H3 R{PILOT_H3_RESOLUTION} cells, "
            f"expected {PILOT_CELL_COUNT}; the pilot boundary or h3 version changed"
        )
    return ordered


@lru_cache(maxsize=1)
def pilot_cell_centroids() -> tuple[tuple[str, float, float], ...]:
    """Return ``(cell, latitude, longitude)`` for every pilot cell."""

    return tuple((cell, *h3.cell_to_latlng(cell)) for cell in pilot_cells())
