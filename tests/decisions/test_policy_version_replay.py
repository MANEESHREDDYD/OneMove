"""A decision must never be silently restated under different mathematics.

Optimization policy 2.0.0 changed capacity semantics, normalised the objective
components and made assignments canonically reconstructed. Recomputing a
pre-2.0.0 decision under 2.0.0 and reporting the difference as DRIFT would read
as "same model, different answer", which is false: it is a different model.
"""

from __future__ import annotations

import os

import pytest

from services.zonepilot.optimization.contracts import OPTIMIZATION_POLICY_VERSION

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="decision ledger requires TEST_DATABASE_URL",
)


def test_policy_version_is_stamped_on_new_decisions() -> None:
    """A decision frozen today records the policy that produced it."""
    from services.zonepilot.decisions.ledger import DecisionLedger

    ledger = DecisionLedger()
    record = _record(ledger, "policy-stamp")
    assert record.optimization_policy_version == OPTIMIZATION_POLICY_VERSION

    fetched = ledger.get_decision(record.decision_id, "ws-blr-01")
    assert fetched is not None
    assert fetched.optimization_policy_version == OPTIMIZATION_POLICY_VERSION, (
        "the policy version must survive the round trip through storage"
    )


def test_legacy_decision_is_not_replayed_under_the_current_policy() -> None:
    """A pre-versioning record must return a typed legacy state, not DRIFT."""
    from services.zonepilot.decisions.ledger import DecisionLedger

    ledger = DecisionLedger()
    record = _record(ledger, "policy-legacy")

    # Simulate a decision frozen before policy versioning existed.
    with ledger.repository._connect() as conn:  # noqa: SLF001 - deliberate fixture setup
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.decision_records SET optimization_policy_version = NULL "
                "WHERE decision_id = %s",
                (record.decision_id,),
            )
        conn.commit()

    replay = ledger.replay_decision(record.decision_id, workspace_id="ws-blr-01")

    assert replay.match_status == "LEGACY_POLICY_NOT_REPLAYABLE"
    assert replay.reproduced_exact_action is False
    assert replay.objective_match is False
    assert "LEGACY_POLICY" in replay.reason
    assert replay.match_status != "EXACT_MATCH", "a legacy decision must never report EXACT_MATCH"
    assert replay.match_status != "DRIFT", "policy mismatch is not drift"


def test_mismatched_policy_version_is_not_replayed() -> None:
    """An explicitly different policy is refused just as firmly as a null one."""
    from services.zonepilot.decisions.ledger import DecisionLedger

    ledger = DecisionLedger()
    record = _record(ledger, "policy-mismatch")

    with ledger.repository._connect() as conn:  # noqa: SLF001 - deliberate fixture setup
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.decision_records SET optimization_policy_version = %s "
                "WHERE decision_id = %s",
                ("1.0.0", record.decision_id),
            )
        conn.commit()

    replay = ledger.replay_decision(record.decision_id, workspace_id="ws-blr-01")
    assert replay.match_status == "LEGACY_POLICY_NOT_REPLAYABLE"
    assert "1.0.0" in replay.reason


def _record(ledger, tag: str):
    import hashlib
    from datetime import datetime, timezone

    from services.zonepilot.optimization.r1_catalog import default_data_root

    matrix = default_data_root() / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"
    if not matrix.is_file():
        pytest.skip("authentic travel matrix not mounted")

    return ledger.record_decision(
        workspace_id="ws-blr-01",
        decision_time=datetime.now(timezone.utc),
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash=hashlib.sha256(tag.encode()).hexdigest(),
        selected_action="OPEN_FACILITIES",
        opened_facilities=[
            "fac:8861892599fffff",
            "fac:88618925a7fffff",
            "fac:88618925c5fffff",
            "fac:8861892eddfffff",
        ],
        objective_value=23548137358244,
        expected_travel_seconds=500,
        p95_travel_seconds=750,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash=hashlib.sha256(matrix.read_bytes()).hexdigest(),
        solver_version="ortools-9.11",
    )
