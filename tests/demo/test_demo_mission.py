"""The mission is simulated. The geography under it is not.

That split is the demo's central honesty claim, and these tests are what make it
a claim rather than an assertion: the orders must be labelled SIMULATED and
refuse to be relabelled, they must carry no customer identity, every coordinate
must resolve back to the real H3 cell it declares, and the whole mission must be
byte-reproducible so a decision frozen against it can be replayed later.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

DATA_ROOT = Path(os.environ.get("ZONEPILOT_DATA_ROOT", "data_root"))
GOLD = DATA_ROOT / "private" / "official" / "gold" / "gold_network_h3_8.parquet"
MATRIX = DATA_ROOT / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"

# The current version's digest. A change to the generation rules must bump
# DEMO_MISSION_VERSION and this constant together; a silent change fails here.
EXPECTED_FINGERPRINT = "18deedebc1a708a56814999768f0436de7bc16684e53703f8b3a51b81fd67a7d"


def _require_network() -> None:
    if not GOLD.is_file():
        pytest.skip(f"gold network not mounted at {GOLD}")
    if not MATRIX.is_file():
        pytest.skip(f"travel matrix not mounted at {MATRIX}")


@pytest.fixture(scope="module")
def mission():
    _require_network()
    from services.zonepilot.demo.mission import build_demo_mission

    return build_demo_mission()


# --- the simulated half ------------------------------------------------------


def test_every_order_is_labelled_simulated(mission) -> None:
    from services.temporal.contracts import EvidenceClass

    assert mission.evidence_class is EvidenceClass.SIMULATED
    for order in mission.orders:
        assert order.evidence_class is EvidenceClass.SIMULATED, order.order_id


def test_an_order_cannot_be_relabelled_as_observed_demand() -> None:
    """The label is enforced by the contract, not by discipline.

    Nobody ordered anything. A caller that tries to present the mission as
    observed demand must fail loudly at construction rather than produce a
    plausible-looking record.
    """
    from pydantic import ValidationError

    from services.temporal.contracts import EvidenceClass
    from services.zonepilot.demo.mission import OrderPriority, OrderShape, SimulatedOrder

    fields = dict(
        order_id="ORD-001",
        pickup_lat=12.9721,
        pickup_lon=77.6452,
        dropoff_lat=12.9700,
        dropoff_lon=77.6450,
        pickup_h3="8860145b41fffff",
        dropoff_h3="8860145b41fffff",
        priority=OrderPriority.STANDARD,
        shape=OrderShape.SHORT_INTRA_CELL,
        created_at=__import__("datetime").datetime(2026, 8, 25, tzinfo=__import__("datetime").timezone.utc),
    )

    SimulatedOrder(**fields)  # the honest construction succeeds

    for forbidden in (EvidenceClass.OBSERVED, EvidenceClass.PUBLIC_OFFICIAL, EvidenceClass.DERIVED):
        with pytest.raises(ValidationError):
            SimulatedOrder(**fields, evidence_class=forbidden)


def test_no_order_field_can_hold_a_customer_identity(mission) -> None:
    """A field that does not exist cannot be filled in by someone who forgets.

    The contract forbids extra fields, so this also proves no caller can attach
    a name or address on the side.
    """
    from pydantic import ValidationError

    from services.zonepilot.demo.mission import SimulatedOrder

    declared = set(SimulatedOrder.model_fields)
    forbidden = {
        "customer_name",
        "customer_phone",
        "phone",
        "address",
        "email",
        "merchant_name",
        "restaurant",
        "rider_name",
        "rider_id",
    }
    assert declared & forbidden == set(), f"personal-identity fields present: {declared & forbidden}"

    order = mission.orders[0]
    with pytest.raises(ValidationError):
        order.model_copy(update={"customer_name": "someone"}).model_validate(
            {**order.model_dump(), "customer_name": "someone"}
        )


# --- the real half -----------------------------------------------------------


def test_every_coordinate_resolves_back_to_its_declared_cell(mission) -> None:
    """Real geography means the point is IN the cell, not near it.

    This is the same rule the road-extract tests enforce: geography is verified
    by coordinates, never by a label. An order that claims a cell it does not
    sit in would put a marker on the wrong part of the map.
    """
    h3 = pytest.importorskip("h3")

    for order in mission.orders:
        assert h3.latlng_to_cell(order.pickup_lat, order.pickup_lon, 8) == order.pickup_h3, (
            f"{order.order_id} pickup is not inside {order.pickup_h3}"
        )
        assert h3.latlng_to_cell(order.dropoff_lat, order.dropoff_lon, 8) == order.dropoff_h3, (
            f"{order.order_id} dropoff is not inside {order.dropoff_h3}"
        )


def test_every_cell_used_belongs_to_the_94_cell_pilot_network(mission) -> None:
    """Orders must sit on the network the optimizer actually reasons about."""
    pd = pytest.importorskip("pandas")

    frame = pd.read_parquet(GOLD)
    network = set(frame["h3_index"].astype(str))
    assert len(network) == 94

    used = {o.pickup_h3 for o in mission.orders} | {o.dropoff_h3 for o in mission.orders}
    assert used <= network, f"orders reference cells outside the pilot network: {sorted(used - network)}"


def test_coordinates_are_inside_the_bengaluru_envelope(mission) -> None:
    """The envelope any other city on earth fails."""
    for order in mission.orders:
        for lat, lon in ((order.pickup_lat, order.pickup_lon), (order.dropoff_lat, order.dropoff_lon)):
            assert 12.70 <= lat <= 13.20, f"{order.order_id} lat {lat} is not Bengaluru"
            assert 77.30 <= lon <= 77.90, f"{order.order_id} lon {lon} is not Bengaluru"


# --- reproducibility ---------------------------------------------------------


def test_the_mission_is_byte_reproducible(mission) -> None:
    """Same version, same network, same sixteen orders -- forever.

    A decision frozen against this mission is replayed against it months later.
    If the mission drifts, the replay is comparing against something else and
    its verdict means nothing.
    """
    from services.zonepilot.demo.mission import build_demo_mission

    again = build_demo_mission()
    assert again.fingerprint() == mission.fingerprint()
    assert again.model_dump(mode="json") == mission.model_dump(mode="json")


def test_the_published_fingerprint_has_not_drifted(mission) -> None:
    """Changing the generation rules must bump the version, visibly."""
    from services.zonepilot.demo.mission import DEMO_MISSION_VERSION

    assert mission.mission_version == DEMO_MISSION_VERSION
    assert mission.fingerprint() == EXPECTED_FINGERPRINT, (
        "the mission changed without a version bump; if the change is intended, "
        f"bump DEMO_MISSION_VERSION and update EXPECTED_FINGERPRINT to {mission.fingerprint()}"
    )


def test_created_at_is_anchored_not_wall_clock(mission) -> None:
    """Wall-clock time in a replayable fixture is a time bomb.

    This project has already shipped one: a test fixture anchored to a literal
    date, which silently inverted once that date passed. Anchoring to a declared
    epoch keeps the mission reproducible without depending on when it runs.
    """
    from services.zonepilot.demo.mission import MISSION_EPOCH

    assert mission.generated_from_epoch == MISSION_EPOCH
    times = [o.created_at for o in mission.orders]
    assert times == sorted(times), "orders must be created in sequence"
    assert min(times) == MISSION_EPOCH
    for stamp in times:
        assert stamp.tzinfo is not None, "every timestamp must be timezone-aware"


# --- the mission is a real planning problem ----------------------------------


def test_the_mission_poses_an_actual_planning_problem(mission) -> None:
    """Sixteen evenly-scattered orders would prove nothing.

    A uniform blob is served about equally well by any configuration, so the
    difference between doing nothing and acting would be invisible. Each shape
    must actually be present.
    """
    from services.zonepilot.demo.mission import ORDER_COUNT, OrderPriority, OrderShape

    assert len(mission.orders) == ORDER_COUNT
    shapes = {o.shape for o in mission.orders}
    assert shapes == set(OrderShape), f"missing order shapes: {set(OrderShape) - shapes}"

    high = [o for o in mission.orders if o.priority is OrderPriority.HIGH]
    assert high, "a mission with no urgency has no tradeoff to make"

    corridor = [o for o in mission.orders if o.shape is OrderShape.SHARED_CORRIDOR]
    assert len({o.pickup_h3 for o in corridor}) == 1, "a corridor group must share its pickup cell"

    intra = [o for o in mission.orders if o.shape is OrderShape.SHORT_INTRA_CELL]
    for order in intra:
        assert order.pickup_h3 == order.dropoff_h3

    cross = [o for o in mission.orders if o.shape is OrderShape.CROSS_ZONE]
    for order in cross:
        assert order.pickup_h3 != order.dropoff_h3


def test_the_inconvenient_order_is_chosen_by_travel_time_not_by_taste(mission) -> None:
    """'Inconvenient' is defined by the frozen matrix, not hand-picked.

    Its dropoff must be the pilot cell whose nearest candidate facility is the
    slowest to reach, so the choice is reproducible and defensible rather than
    a number someone liked.
    """
    import json

    from services.zonepilot.demo.mission import OrderShape

    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    demand_ids = [d.removeprefix("zone:") for d in matrix["demand_ids"]]
    durations = matrix["base_durations_seconds"]
    best = {
        demand_ids[j]: min(durations[i][j] for i in range(len(durations)))
        for j in range(len(demand_ids))
    }
    worst_cell = max(sorted(best), key=lambda cell: best[cell])

    awkward = [o for o in mission.orders if o.shape is OrderShape.GEOGRAPHICALLY_INCONVENIENT]
    assert len(awkward) == 1
    assert awkward[0].dropoff_h3 == worst_cell, (
        f"the inconvenient order drops at {awkward[0].dropoff_h3}, but the cell farthest "
        f"from any candidate facility is {worst_cell} ({best[worst_cell]}s)"
    )
