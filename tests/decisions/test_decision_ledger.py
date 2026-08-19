"""Tests for R7 Decision Ledger, Time Travel, Replay, and Shadow Evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.temporal.contracts import OutcomeStatus
from services.zonepilot.decisions.contracts import (
    ShadowState,
)
from services.zonepilot.decisions.ledger import DecisionLedger


def test_record_and_retrieve_decision() -> None:
    ledger = DecisionLedger()
    t = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    rec = ledger.record_decision(
        workspace_id="ws-blr-01",
        decision_time=t,
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash="a" * 64,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:01", "fac:03", "fac:07"],
        objective_value=125000,
        expected_travel_seconds=640,
        p95_travel_seconds=920,
        coverage_basis_points=9850,
        graph_version="1.1",
        osrm_bundle_hash="b" * 64,
        solver_version="ortools-9.11",
        evidence_ids=["ev-01", "ev-02"],
    )

    assert rec.decision_id.startswith("dec-")
    assert rec.workspace_id == "ws-blr-01"
    assert len(rec.opened_facilities) == 3

    fetched = ledger.get_decision(rec.decision_id)
    assert fetched is not None
    assert fetched.decision_id == rec.decision_id


def test_decision_replay_verification() -> None:
    ledger = DecisionLedger()
    t = datetime.now(timezone.utc)
    rec = ledger.record_decision(
        workspace_id="ws-blr-01",
        decision_time=t,
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash="a" * 64,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:88618925a5fffff", "fac:88618925a7fffff", "fac:8861892ec3fffff", "fac:8861892ecbfffff"],
        objective_value=1756300000000,
        expected_travel_seconds=500,
        p95_travel_seconds=750,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash="b" * 64,
        solver_version="ortools-9.11",
    )

    replay_good = ledger.replay_decision(rec.decision_id, workspace_id="ws-blr-01")
    assert replay_good.pit_valid is True
    assert replay_good.reproduced_exact_action is True
    assert replay_good.reproduced_exact_facilities is True
    assert replay_good.objective_match is True
    assert replay_good.match_status == "EXACT_MATCH"

    # Test diverged record
    rec_diverged = ledger.record_decision(
        workspace_id="ws-blr-01",
        decision_time=t,
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash="a" * 64,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:01", "fac:04"],
        objective_value=92000,
        expected_travel_seconds=500,
        p95_travel_seconds=750,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash="b" * 64,
        solver_version="ortools-9.11",
    )
    replay_diverged = ledger.replay_decision(rec_diverged.decision_id, workspace_id="ws-blr-01")
    assert replay_diverged.reproduced_exact_facilities is False
    assert replay_diverged.match_status == "DRIFT"


def test_shadow_evaluation_loop() -> None:
    ledger = DecisionLedger()
    t = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    rec = ledger.record_decision(
        workspace_id="ws-blr-01",
        decision_time=t,
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash="a" * 64,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:01"],
        objective_value=50000,
        expected_travel_seconds=400,
        p95_travel_seconds=600,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash="b" * 64,
        solver_version="ortools-9.11",
    )

    t_future = t + timedelta(hours=2)
    shadow = ledger.create_shadow(rec, t_future)
    assert shadow.shadow_state == ShadowState.FROZEN_AWAITING_FUTURE
    assert shadow.outcome_status == OutcomeStatus.PENDING

    evaluated = ledger.evaluate_shadow(shadow.shadow_id, actual_observed_p95_seconds=650)
    assert evaluated.shadow_state == ShadowState.EVALUATED
    assert evaluated.outcome_status == OutcomeStatus.EVALUATED
    assert evaluated.regret_seconds == 50


def test_adversarial_pit_temporal_isolation() -> None:
    """Adversarial test proving future features at T+5m cannot influence frozen decision replay at T."""
    ledger = DecisionLedger()
    t_decision = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
    snapshot_hash = "c" * 64

    rec = ledger.record_decision(
        workspace_id="ws-blr-01",
        decision_time=t_decision,
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash=snapshot_hash,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:88618925a5fffff", "fac:88618925a7fffff", "fac:8861892ec3fffff", "fac:8861892ecbfffff"],
        objective_value=1756300000000,
        expected_travel_seconds=500,
        p95_travel_seconds=750,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash="b" * 64,
        solver_version="ortools-9.11",
    )

    # 1. Historical replay with exact cutoff at T -> EXACT_MATCH
    replay_exact = ledger.replay_decision(rec.decision_id, workspace_id="ws-blr-01", feature_cutoff=t_decision)
    assert replay_exact.pit_valid is True
    assert replay_exact.match_status == "EXACT_MATCH"

    # 2. Adversarial replay with future cutoff T+5m -> NON_REPLAYABLE
    t_future = t_decision + timedelta(minutes=5)
    replay_future = ledger.replay_decision(rec.decision_id, workspace_id="ws-blr-01", feature_cutoff=t_future)
    assert replay_future.pit_valid is False
    assert replay_future.match_status == "NON_REPLAYABLE"
    assert "Point-In-Time violation" in (replay_future.reason or "")

