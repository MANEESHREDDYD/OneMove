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
    t = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    rec = ledger.record_decision(
        workspace_id="ws-blr-01",
        decision_time=t,
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash="a" * 64,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:01", "fac:03"],
        objective_value=85000,
        expected_travel_seconds=500,
        p95_travel_seconds=750,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash="b" * 64,
        solver_version="ortools-9.11",
    )

    replay_good = ledger.replay_decision(
        rec.decision_id,
        recomputed_action="OPEN_FACILITIES",
        recomputed_facilities=["fac:01", "fac:03"],
        recomputed_objective=85000,
    )
    assert replay_good.reproduced_exact_action is True
    assert replay_good.reproduced_exact_facilities is True
    assert replay_good.objective_match is True

    replay_diverged = ledger.replay_decision(
        rec.decision_id,
        recomputed_action="OPEN_FACILITIES",
        recomputed_facilities=["fac:01", "fac:04"],
        recomputed_objective=92000,
    )
    assert replay_diverged.reproduced_exact_facilities is False
    assert replay_diverged.objective_match is False


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
