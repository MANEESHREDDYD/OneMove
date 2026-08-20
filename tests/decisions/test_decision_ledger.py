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

    fetched = ledger.get_decision(rec.decision_id, "ws-blr-01")
    assert fetched is not None
    assert fetched.decision_id == rec.decision_id


def test_decision_replay_verification() -> None:
    import hashlib

    from services.zonepilot.optimization.r1_catalog import default_data_root

    mat_path = default_data_root() / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"
    mat_sha = hashlib.sha256(mat_path.read_bytes()).hexdigest()

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
        osrm_bundle_hash=mat_sha,
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
        osrm_bundle_hash=mat_sha,
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

    evaluated = ledger.evaluate_shadow(shadow.shadow_id, "ws-blr-01", actual_observed_p95_seconds=650)
    assert evaluated.shadow_state == ShadowState.EVALUATED
    assert evaluated.outcome_status == OutcomeStatus.EVALUATED
    assert evaluated.regret_seconds == 50


def test_adversarial_pit_temporal_isolation() -> None:
    """Adversarial test proving future features at T+5m cannot influence frozen decision replay at T."""
    import hashlib

    from services.zonepilot.optimization.r1_catalog import default_data_root

    mat_path = default_data_root() / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"
    mat_sha = hashlib.sha256(mat_path.read_bytes()).hexdigest()

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
        osrm_bundle_hash=mat_sha,
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


def test_pit_temporal_attack_and_artifact_corruption() -> None:
    """T0 -> T1 -> T2 -> T3 temporal attack and artifact corruption."""
    import hashlib

    from services.zonepilot.optimization.contracts import create_problem_snapshot
    from services.zonepilot.optimization.pubsub_worker import _reconstruct_problem_from_payload
    from services.zonepilot.optimization.r1_catalog import default_data_root
    from services.zonepilot.optimization.repository import OptimizationRepository

    opt_repo = OptimizationRepository()
    ledger = DecisionLedger(opt_repository=opt_repo)

    t2_decision = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)

    # Reconstruct authentic problem and snapshot
    problem = _reconstruct_problem_from_payload({})
    mat_path = default_data_root() / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"
    mat_sha = hashlib.sha256(mat_path.read_bytes()).hexdigest()

    snapshot = create_problem_snapshot(
        problem,
        code_sha=ledger.code_sha,
        dataset_version="1.0.0",
        matrix_sha256=mat_sha,
        gold_manifest_sha256="gold-sha-123",
        evidence_ids=("ev-gold-network-1.1", "ev-osrm-r1-table", "ev-opt-job-001"),
        temporal_cutoff=t2_decision.isoformat(),
    )
    opt_repo.save_problem_snapshot(snapshot, workspace_id="ws-blr-01")

    # Freeze decision at T2
    rec = ledger.record_decision(
        workspace_id="ws-blr-01",
        decision_time=t2_decision,
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash=snapshot.problem_snapshot_sha256,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:88618925a5fffff", "fac:88618925a7fffff", "fac:8861892ec3fffff", "fac:8861892ecbfffff"],
        objective_value=1756300000000,
        expected_travel_seconds=500,
        p95_travel_seconds=750,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash=mat_sha,
        solver_version="ortools-cp-sat",
        evidence_ids=("ev-gold-network-1.1", "ev-osrm-r1-table", "ev-opt-job-001"),
    )

    # 1. Replay frozen T2 decision -> EXACT_MATCH
    replay_res = ledger.replay_decision(rec.decision_id, workspace_id="ws-blr-01", feature_cutoff=t2_decision)
    assert replay_res.pit_valid is True
    assert replay_res.match_status == "EXACT_MATCH"

    # 2. T3 = T2 + 5m: Future cutoff -> proves future data is rejected with NON_REPLAYABLE
    t3 = t2_decision + timedelta(minutes=5)
    replay_t3 = ledger.replay_decision(rec.decision_id, workspace_id="ws-blr-01", feature_cutoff=t3)
    assert replay_t3.pit_valid is False
    assert replay_t3.match_status == "NON_REPLAYABLE"
    assert "Point-In-Time violation" in replay_t3.reason

    # 3. Intentional artifact corruption test -> NON_REPLAYABLE
    rec_corrupted = ledger.record_decision(
        workspace_id="ws-blr-01",
        decision_time=t2_decision,
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash=snapshot.problem_snapshot_sha256,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:88618925a5fffff"],
        objective_value=1000,
        expected_travel_seconds=500,
        p95_travel_seconds=750,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash="corrupted_sha_000000000000000000000000000000000000000000000000000000",
        solver_version="ortools-cp-sat",
        evidence_ids=("ev-01",),
    )
    replay_corrupt = ledger.replay_decision(
        rec_corrupted.decision_id, workspace_id="ws-blr-01", feature_cutoff=t2_decision
    )
    assert replay_corrupt.pit_valid is False
    assert replay_corrupt.match_status == "NON_REPLAYABLE"
    assert "CORRUPTED_OR_MISSING_ARTIFACT" in replay_corrupt.reason
