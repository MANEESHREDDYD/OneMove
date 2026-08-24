"""Geography integrity: prove where an artifact actually is, never trust its name.

`data/geo/bengaluru_clip.osm.pbf` was byte-identical to `andorra-latest.osm.pbf`
-- Andorra shipped under a Bengaluru name. The previous version of this file did
not catch it, because all three of its tests were vacuous:

  * the "quarantine" test only asserted `andorra_hash != pilot_hash`, which is
    true whether or not the mislabelled file is present;
  * the lineage test pointed at `data_root/.../raw/osm/`, a path that does not
    exist, so `if path.exists()` was False and it asserted nothing;
  * the bounds test compared two hard-coded literals to each other and never
    read a data file.

These tests read the actual coordinates out of the actual artifacts.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

ANDORRA_SHA256 = "f7da0ba356d7ec1a77700dc136ceb87323b7ee2e862f11505c34890f067f2bb7"
PILOT_ROADS_SHA256 = "461584ea03d2d0948a25715c0a901b8bb12f01ca15c59fc72bdeaf05e568d7a1"

PILOT_ROADS = Path("data/private/official/raw/osrm/pilot_roads.osm.pbf")

# Generous bounds around the Bengaluru metropolitan area. Wide enough that a
# legitimate re-cut of the extract still passes, tight enough that any other
# city on earth fails.
BLR_MIN_LAT, BLR_MAX_LAT = 12.70, 13.20
BLR_MIN_LON, BLR_MAX_LON = 77.30, 77.90


def _require_pilot_roads() -> None:
    """Skip -- loudly -- when the gitignored road extract is not mounted.

    `*.pbf` is excluded by .gitignore, so the extract exists on a developer
    machine and on a runner that has just built it, but never on a stock CI
    checkout. The guard has to be an explicit `pytest.skip`, not the
    `if path.exists():` this file used to carry: that idiom made all three
    tests assert nothing whatsoever when the artifact was absent, and they
    still reported green, which is exactly how Andorra shipped under a
    Bengaluru name. A skip names the missing artifact in the pytest report;
    a silent pass names nothing. When the artifact IS present every assertion
    below runs in full.
    """
    if not PILOT_ROADS.is_file():
        pytest.skip(f"road evidence artifact not mounted at {PILOT_ROADS}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _osm_bounds(path: Path) -> tuple[float, float, float, float]:
    """Return (min_lat, max_lat, min_lon, max_lon) read from the file itself."""
    osmium = pytest.importorskip("osmium", reason="osmium is required to read PBF bounds")

    class _Bounds(osmium.SimpleHandler):
        def __init__(self) -> None:
            super().__init__()
            self.min_lat = self.min_lon = 1e9
            self.max_lat = self.max_lon = -1e9

        def node(self, n) -> None:  # noqa: ANN001 - osmium callback
            if not n.location.valid():
                return
            lat, lon = n.location.lat, n.location.lon
            self.min_lat = min(self.min_lat, lat)
            self.max_lat = max(self.max_lat, lat)
            self.min_lon = min(self.min_lon, lon)
            self.max_lon = max(self.max_lon, lon)

    handler = _Bounds()
    handler.apply_file(str(path))
    return handler.min_lat, handler.max_lat, handler.min_lon, handler.max_lon


def test_pilot_roads_is_present_and_is_the_expected_artifact() -> None:
    """The canonical road evidence must be the exact artifact, byte for byte."""
    _require_pilot_roads()
    digest = _sha256(PILOT_ROADS)
    assert digest == PILOT_ROADS_SHA256
    assert digest != ANDORRA_SHA256


def test_pilot_roads_coordinates_are_actually_in_bengaluru() -> None:
    """Read the coordinates. A filename is not evidence of geography."""
    _require_pilot_roads()
    min_lat, max_lat, min_lon, max_lon = _osm_bounds(PILOT_ROADS)

    assert BLR_MIN_LAT <= min_lat <= BLR_MAX_LAT, f"southern edge {min_lat} outside Bengaluru"
    assert BLR_MIN_LAT <= max_lat <= BLR_MAX_LAT, f"northern edge {max_lat} outside Bengaluru"
    assert BLR_MIN_LON <= min_lon <= BLR_MAX_LON, f"western edge {min_lon} outside Bengaluru"
    assert BLR_MIN_LON <= max_lon <= BLR_MAX_LON, f"eastern edge {max_lon} outside Bengaluru"


def test_no_artifact_named_bengaluru_contains_another_city() -> None:
    """Any file claiming to be Bengaluru must prove it by its coordinates.

    This is the regression for the Andorra-as-Bengaluru defect. It scans by
    name and then checks the data, so re-introducing a mislabelled extract
    fails here regardless of which city it really is.
    """
    _require_pilot_roads()
    pytest.importorskip("osmium", reason="osmium is required to read PBF bounds")
    candidates = [
        p
        for p in Path("data").rglob("*.osm.pbf")
        if any(token in p.name.lower() for token in ("bengaluru", "bangalore", "blr", "pilot"))
    ]
    assert candidates, "expected at least one Bengaluru-named extract to validate"

    for path in candidates:
        digest = _sha256(path)
        assert digest != ANDORRA_SHA256, f"{path} is the Andorra extract under a Bengaluru name"

        min_lat, max_lat, min_lon, max_lon = _osm_bounds(path)
        assert BLR_MIN_LAT <= min_lat and max_lat <= BLR_MAX_LAT, (
            f"{path} latitudes {min_lat}..{max_lat} are not Bengaluru"
        )
        assert BLR_MIN_LON <= min_lon and max_lon <= BLR_MAX_LON, (
            f"{path} longitudes {min_lon}..{max_lon} are not Bengaluru"
        )


def test_h3_network_cells_fall_inside_the_road_extract() -> None:
    """The 94 pilot cells must sit on the road evidence, not merely near it."""
    pd = pytest.importorskip("pandas")
    h3 = pytest.importorskip("h3")

    gold = Path("data/private/official/gold/gold_network_h3_8.parquet")
    if not gold.is_file():
        pytest.skip(f"gold network not mounted at {gold}")

    frame = pd.read_parquet(gold)
    cells = frame["h3_index"].astype(str).tolist()
    assert len(cells) == 94
    assert {int(r) for r in frame["h3_resolution"]} == {8}

    for cell in cells:
        lat, lon = h3.cell_to_latlng(cell)
        assert BLR_MIN_LAT <= lat <= BLR_MAX_LAT, f"cell {cell} at lat {lat} is not Bengaluru"
        assert BLR_MIN_LON <= lon <= BLR_MAX_LON, f"cell {cell} at lon {lon} is not Bengaluru"
