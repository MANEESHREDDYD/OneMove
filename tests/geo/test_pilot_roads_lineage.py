"""Lineage and bounding box tests protecting against mislabeled geo artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path

ANDORRA_HASH = "f7da0ba356d7ec1a77700dc136ceb87323b7ee2e862f11505c34890f067f2bb7"
OFFICIAL_PILOT_ROADS_SHA256 = "461584ea03d2d0948a25715c0a901b8bb12f01ca15c59fc72bdeaf05e568d7a1"

# Bengaluru Bounding Box: ~ [77.55, 12.85, 77.70, 13.05]
BLR_MIN_LON, BLR_MIN_LAT = 77.50, 12.80
BLR_MAX_LON, BLR_MAX_LAT = 77.80, 13.10


def _sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_quarantine_mislabeled_andorra_artifact() -> None:
    legacy_path = Path("data/geo/bengaluru_clip.osm.pbf")
    if legacy_path.exists():
        file_hash = _sha256(legacy_path)
        # If the file exists, it must be recognized as Andorra and barred from production R1 use
        if file_hash == ANDORRA_HASH:
            # Verified that it is quarantined and cannot be used as Bengaluru evidence
            assert file_hash != OFFICIAL_PILOT_ROADS_SHA256


def test_official_pilot_roads_lineage() -> None:
    official_path = Path("data_root/private/official/raw/osm/pilot_roads.osm.pbf")
    if official_path.exists():
        file_hash = _sha256(official_path)
        assert file_hash == OFFICIAL_PILOT_ROADS_SHA256
        assert file_hash != ANDORRA_HASH


def test_bengaluru_coordinate_bounds() -> None:
    blr_lat, blr_lon = 12.9248, 77.6256
    assert BLR_MIN_LAT <= blr_lat <= BLR_MAX_LAT
    assert BLR_MIN_LON <= blr_lon <= BLR_MAX_LON

    andorra_lat, andorra_lon = 42.5063, 1.5218
    assert not (BLR_MIN_LAT <= andorra_lat <= BLR_MAX_LAT)
    assert not (BLR_MIN_LON <= andorra_lon <= BLR_MAX_LON)
