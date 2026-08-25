"""A deterministic multi-order delivery mission on real Bengaluru geography.

The orders are SIMULATED. The geography is not.

That split is the whole point of this module, and it is enforced rather than
promised. Every order's pickup and dropoff is a real coordinate inside one of
the 94 real H3 resolution-8 cells of the pilot network -- cells cut from the
OpenStreetMap road extract, carrying real road length, real intersection counts
and real commercial POI counts. What is invented is the demand: that someone
ordered something, when, and how urgently. Nobody ordered anything. There is no
customer, no merchant, no rider and no address.

So the contract below carries ``evidence_class = SIMULATED`` on every order and
on the mission, and there is deliberately no field for a customer name, a phone
number, a street address or a merchant identity. A field that does not exist
cannot be filled in later by someone who forgets what this is.

WHY THE ORDERS LOOK THE WAY THEY DO
-----------------------------------
A mission of sixteen evenly-scattered orders would be pretty and would prove
nothing: any facility configuration serves a uniform blob about equally well.
This mission is built to create an actual planning problem, so the difference
between doing nothing and acting is visible on the map:

  * short trips inside a single dense cell, which almost any configuration wins;
  * cross-zone trips from merchant-dense cells to sparse ones, which is where
    facility placement starts to matter;
  * a corridor group sharing one pickup cell, so consolidation is visible;
  * one high-priority order;
  * one deliberately inconvenient order, placed in the cell that is farthest
    from every candidate facility.

The selection is driven by the real attributes in the gold network -- commercial
POI density for pickups, road density for the sparse end of cross-zone trips,
and true travel time from the frozen OSRM matrix for the inconvenient one. That
is a defensible basis rather than a hand-picked one, and it is reproducible: the
same gold network yields the same sixteen orders, forever.

DETERMINISM
-----------
Seeded by ``DEMO_SEED`` and stamped with ``DEMO_MISSION_VERSION``. Two runs of
the same version against the same network produce byte-identical orders, so a
decision frozen against this mission can be replayed against it later. Changing
the generation rules requires bumping the version; the tests pin the current
version's fingerprint so a silent change fails.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator, model_validator

from services.temporal.contracts import EvidenceClass, StrictContract

DEMO_MISSION_VERSION = "cto-outreach-v1"

# A fixed, documented seed. It is the deadline date, chosen only because it is
# arbitrary and memorable; nothing about the mission depends on its value beyond
# reproducibility.
DEMO_SEED = 20260825

ORDER_COUNT = 16

# Anchor for created_at. Wall-clock time must not leak into a fixture that a
# point-in-time replay has to reproduce months later.
MISSION_EPOCH = datetime(2026, 8, 25, 9, 0, 0, tzinfo=timezone.utc)

DATA_ROOT = Path(os.environ.get("ZONEPILOT_DATA_ROOT", "data_root"))
GOLD_NETWORK = DATA_ROOT / "private" / "official" / "gold" / "gold_network_h3_8.parquet"
TRAVEL_MATRIX = DATA_ROOT / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"

# The pilot envelope, identical to tests/geo/test_pilot_roads_lineage.py and
# lib/geo/projection.ts. Geography is verified by coordinates, never by a name.
BLR_MIN_LAT, BLR_MAX_LAT = 12.70, 13.20
BLR_MIN_LON, BLR_MAX_LON = 77.30, 77.90


class OrderPriority(str, Enum):
    """How urgent the simulated demand is. Not an SLA, and not a promise."""

    STANDARD = "STANDARD"
    HIGH = "HIGH"


class OrderShape(str, Enum):
    """Why this order exists in the mission -- its role in the planning problem.

    Published so a reader can see the mission was constructed to be a real
    problem rather than a flattering one.
    """

    SHORT_INTRA_CELL = "SHORT_INTRA_CELL"
    CROSS_ZONE = "CROSS_ZONE"
    SHARED_CORRIDOR = "SHARED_CORRIDOR"
    NEAR_CANDIDATE_FACILITY = "NEAR_CANDIDATE_FACILITY"
    GEOGRAPHICALLY_INCONVENIENT = "GEOGRAPHICALLY_INCONVENIENT"


class SimulatedOrder(StrictContract):
    """One simulated delivery order at real coordinates.

    There is no customer name, phone number, address or merchant identity here,
    and there is no field to put one in.
    """

    order_id: str = Field(min_length=7, max_length=7)
    pickup_lat: float
    pickup_lon: float
    dropoff_lat: float
    dropoff_lon: float
    pickup_h3: str = Field(min_length=15, max_length=15)
    dropoff_h3: str = Field(min_length=15, max_length=15)
    priority: OrderPriority
    shape: OrderShape
    created_at: datetime
    evidence_class: EvidenceClass = EvidenceClass.SIMULATED

    @field_validator("evidence_class")
    @classmethod
    def orders_are_always_simulated(cls, value: EvidenceClass) -> EvidenceClass:
        """No caller may relabel an invented order as observed demand."""
        if value is not EvidenceClass.SIMULATED:
            raise ValueError(
                f"a demo order is SIMULATED by construction; refusing to label it {value.value}"
            )
        return value

    @model_validator(mode="after")
    def coordinates_are_inside_the_pilot_envelope(self) -> Self:
        """Simulated demand, real geography -- so the coordinates must be real."""
        for name, lat, lon in (
            ("pickup", self.pickup_lat, self.pickup_lon),
            ("dropoff", self.dropoff_lat, self.dropoff_lon),
        ):
            if not (BLR_MIN_LAT <= lat <= BLR_MAX_LAT and BLR_MIN_LON <= lon <= BLR_MAX_LON):
                raise ValueError(f"{self.order_id} {name} ({lat}, {lon}) is outside the Bengaluru pilot envelope")
        return self


class DemoMission(StrictContract):
    """The full simulated mission, stamped so a replay can reproduce it."""

    mission_version: str = Field(min_length=1)
    seed: int
    network_fingerprint: str = Field(min_length=64, max_length=64)
    generated_from_epoch: datetime
    orders: tuple[SimulatedOrder, ...]
    evidence_class: EvidenceClass = EvidenceClass.SIMULATED

    @model_validator(mode="after")
    def order_ids_are_unique_and_sequential(self) -> Self:
        expected = [f"ORD-{i:03d}" for i in range(1, len(self.orders) + 1)]
        actual = [order.order_id for order in self.orders]
        if actual != expected:
            raise ValueError("order ids must be ORD-001..ORD-NNN in sequence")
        return self

    def fingerprint(self) -> str:
        """A stable digest of the mission, for freezing and for replay."""
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --- network loading ---------------------------------------------------------


def _load_network() -> tuple[list[dict], str]:
    """Read the 94 real cells and a fingerprint of the file they came from."""
    import pandas as pd

    if not GOLD_NETWORK.is_file():
        raise FileNotFoundError(f"gold network not mounted at {GOLD_NETWORK}")

    digest = hashlib.sha256(GOLD_NETWORK.read_bytes()).hexdigest()
    frame = pd.read_parquet(GOLD_NETWORK)
    cells = [
        {
            "h3_index": str(row.h3_index),
            "commercial_poi_count": int(row.commercial_poi_count),
            "road_density": float(row.road_density_km_per_sqkm),
        }
        for row in frame.itertuples()
    ]
    # Sort by id so the ordering never depends on parquet row order.
    cells.sort(key=lambda c: c["h3_index"])
    return cells, digest


def _load_travel_matrix() -> dict:
    if not TRAVEL_MATRIX.is_file():
        raise FileNotFoundError(f"travel matrix not mounted at {TRAVEL_MATRIX}")
    return json.loads(TRAVEL_MATRIX.read_text(encoding="utf-8"))


def _point_in_cell(h3_index: str, salt: int) -> tuple[float, float]:
    """A deterministic point inside a real H3 cell, not merely at its centre.

    Sixteen orders stacked on cell centroids would look like a diagram rather
    than a delivery network. The offset is derived from the cell id and a salt,
    is bounded well inside the cell's inradius, and the result is checked to
    still resolve to the same cell -- so 'inside the real cell' stays true
    rather than approximately true.
    """
    import h3

    lat, lon = h3.cell_to_latlng(h3_index)

    # An r8 cell is ~0.75 km2; its inradius is roughly 450 m. Stay within 40% of
    # that so rounding at the boundary cannot push a point into a neighbour.
    max_offset_m = 180.0
    digest = hashlib.sha256(f"{h3_index}:{salt}:{DEMO_SEED}".encode()).digest()
    angle = (int.from_bytes(digest[0:4], "big") / 2**32) * 2 * math.pi
    radius = math.sqrt(int.from_bytes(digest[4:8], "big") / 2**32) * max_offset_m

    d_lat = (radius * math.cos(angle)) / 111_320.0
    d_lon = (radius * math.sin(angle)) / (111_320.0 * math.cos(math.radians(lat)))
    candidate_lat, candidate_lon = lat + d_lat, lon + d_lon

    if h3.latlng_to_cell(candidate_lat, candidate_lon, 8) != h3_index:
        # The offset would have escaped the cell. The centroid is always inside.
        return lat, lon
    return candidate_lat, candidate_lon


# --- mission construction ----------------------------------------------------


def build_demo_mission() -> DemoMission:
    """Construct the sixteen-order mission. Same inputs, same orders, always."""
    cells, network_digest = _load_network()
    matrix = _load_travel_matrix()

    by_poi = sorted(cells, key=lambda c: (-c["commercial_poi_count"], c["h3_index"]))
    by_road = sorted(cells, key=lambda c: (c["road_density"], c["h3_index"]))

    dense = [c["h3_index"] for c in by_poi[:12]]
    sparse = [c["h3_index"] for c in by_road[:12]]

    # The cell whose best candidate facility is the slowest to reach: the honest
    # definition of 'inconvenient', taken from the frozen travel matrix rather
    # than from straight-line distance or from taste.
    demand_ids = [d.removeprefix("zone:") for d in matrix["demand_ids"]]
    durations = matrix["base_durations_seconds"]
    best_by_demand = {
        demand_ids[j]: min(durations[i][j] for i in range(len(durations)))
        for j in range(len(demand_ids))
    }
    inconvenient = max(sorted(best_by_demand), key=lambda cell: best_by_demand[cell])

    # A candidate facility's own cell, for the order placed next to one.
    facility_cells = sorted(f.removeprefix("fac:") for f in matrix["facility_ids"])
    near_facility_cell = facility_cells[0]

    plan: list[tuple[str, str, OrderShape, OrderPriority]] = []

    # 1-4: short trips inside a single dense cell. Easy for any configuration.
    for i in range(4):
        cell = dense[i]
        plan.append((cell, cell, OrderShape.SHORT_INTRA_CELL, OrderPriority.STANDARD))

    # 5-10: cross-zone, merchant-dense to sparse. Where placement starts to bite.
    for i in range(6):
        plan.append((dense[i % len(dense)], sparse[i], OrderShape.CROSS_ZONE, OrderPriority.STANDARD))

    # 11-13: one shared pickup cell, three separate dropoffs -- a corridor.
    corridor_origin = dense[0]
    for i in range(3):
        plan.append((corridor_origin, sparse[6 + i], OrderShape.SHARED_CORRIDOR, OrderPriority.STANDARD))

    # 14: high priority, on the corridor, so urgency competes with consolidation.
    plan.append((corridor_origin, sparse[9], OrderShape.SHARED_CORRIDOR, OrderPriority.HIGH))

    # 15: next to a candidate facility -- the easy win, for contrast.
    plan.append((near_facility_cell, dense[1], OrderShape.NEAR_CANDIDATE_FACILITY, OrderPriority.STANDARD))

    # 16: the genuinely awkward one.
    plan.append((dense[2], inconvenient, OrderShape.GEOGRAPHICALLY_INCONVENIENT, OrderPriority.HIGH))

    assert len(plan) == ORDER_COUNT, f"mission plan produced {len(plan)} orders, expected {ORDER_COUNT}"

    orders: list[SimulatedOrder] = []
    for index, (pickup_cell, dropoff_cell, shape, priority) in enumerate(plan, start=1):
        pickup_lat, pickup_lon = _point_in_cell(pickup_cell, salt=index * 2)
        dropoff_lat, dropoff_lon = _point_in_cell(dropoff_cell, salt=index * 2 + 1)
        orders.append(
            SimulatedOrder(
                order_id=f"ORD-{index:03d}",
                pickup_lat=pickup_lat,
                pickup_lon=pickup_lon,
                dropoff_lat=dropoff_lat,
                dropoff_lon=dropoff_lon,
                pickup_h3=pickup_cell,
                dropoff_h3=dropoff_cell,
                priority=priority,
                shape=shape,
                # Spread across a plausible ordering window, anchored to the
                # epoch rather than to wall-clock time.
                created_at=MISSION_EPOCH + timedelta(minutes=7 * (index - 1)),
            )
        )

    return DemoMission(
        mission_version=DEMO_MISSION_VERSION,
        seed=DEMO_SEED,
        network_fingerprint=network_digest,
        generated_from_epoch=MISSION_EPOCH,
        orders=tuple(orders),
    )
