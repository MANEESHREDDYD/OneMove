"""P0-AUTH-SNAPSHOT-001 regression: cross-tenant problem-snapshot isolation.

Runs against the real PostgreSQL backend through the production repository and
ledger code paths -- not mocks. The repository connects with an owner-role DSN,
so RLS is not in force here and the application-layer workspace predicate is the
only control under test.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from services.zonepilot.decisions.ledger import DecisionLedger
from services.zonepilot.optimization.contracts import create_problem_snapshot
from services.zonepilot.optimization.pubsub_worker import _reconstruct_problem_from_payload
from services.zonepilot.optimization.repository import OptimizationRepository

TENANT_A = f"ws-isolation-a-{uuid.uuid4()}"
TENANT_B = f"ws-isolation-b-{uuid.uuid4()}"


@pytest.fixture(scope="module")
def tenant_a_snapshot() -> tuple[OptimizationRepository, str]:
    """Tenant A freezes a problem snapshot through the real write path."""
    repo = OptimizationRepository()
    problem = _reconstruct_problem_from_payload({})
    snapshot = create_problem_snapshot(
        problem,
        code_sha="isolation-test",
        dataset_version="1.0.0",
        matrix_sha256="c" * 64,
        gold_manifest_sha256="d" * 64,
        evidence_ids=("ev-isolation-a",),
    )
    repo.save_problem_snapshot(snapshot, workspace_id=TENANT_A)
    return repo, snapshot.problem_snapshot_sha256


def test_tenant_a_can_read_its_own_snapshot(tenant_a_snapshot) -> None:
    """Control case: without this, the DENY assertions below would pass vacuously."""
    repo, sha = tenant_a_snapshot
    doc = repo.get_problem_snapshot(sha, workspace_id=TENANT_A)
    assert doc is not None, "Tenant A must still be able to read its own snapshot"
    assert doc["workspace_id"] == TENANT_A


def test_tenant_b_cannot_read_tenant_a_snapshot(tenant_a_snapshot) -> None:
    """DENY: read A's snapshot as B."""
    repo, sha = tenant_a_snapshot
    assert repo.get_problem_snapshot(sha, workspace_id=TENANT_B) is None


def test_snapshot_lookup_requires_a_workspace(tenant_a_snapshot) -> None:
    """DENY: an unscoped lookup must fail closed rather than return any tenant's row."""
    repo, sha = tenant_a_snapshot
    for bad in ("", "   ", None):
        with pytest.raises(ValueError):
            repo.get_problem_snapshot(sha, workspace_id=bad)  # type: ignore[arg-type]


def test_snapshot_write_requires_a_workspace() -> None:
    """DENY: global/unscoped snapshots may not be created."""
    repo = OptimizationRepository()
    problem = _reconstruct_problem_from_payload({})
    snapshot = create_problem_snapshot(
        problem,
        code_sha="isolation-test",
        dataset_version="1.0.0",
        matrix_sha256="e" * 64,
        gold_manifest_sha256="f" * 64,
        evidence_ids=("ev-isolation-unscoped",),
    )
    for bad in ("", "   ", None):
        with pytest.raises(ValueError):
            repo.save_problem_snapshot(snapshot, workspace_id=bad)  # type: ignore[arg-type]


def test_tenant_b_cannot_replay_tenant_a_decision(tenant_a_snapshot) -> None:
    """DENY: replay A's decision as B."""
    repo, sha = tenant_a_snapshot
    ledger = DecisionLedger(opt_repository=repo)
    t = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)

    rec = ledger.record_decision(
        workspace_id=TENANT_A,
        decision_time=t,
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash=sha,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:88618925a5fffff"],
        objective_value=1000,
        expected_travel_seconds=500,
        p95_travel_seconds=750,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash="c" * 64,
        solver_version="ortools-cp-sat",
        evidence_ids=("ev-isolation-a",),
    )

    # B must not resolve A's decision at all.
    assert ledger.get_decision(rec.decision_id, TENANT_B) is None

    with pytest.raises(LookupError):
        ledger.replay_decision(rec.decision_id, workspace_id=TENANT_B, feature_cutoff=t)


def test_replay_requires_an_explicit_workspace(tenant_a_snapshot) -> None:
    """DENY: an unscoped replay must not fall back to the victim's workspace."""
    repo, sha = tenant_a_snapshot
    ledger = DecisionLedger(opt_repository=repo)
    with pytest.raises(ValueError):
        ledger.replay_decision("dec-anything", workspace_id=None)


def test_decision_create_request_rejects_an_empty_body() -> None:
    """A decision must not be constructible from defaults.

    POST /decisions with {} previously produced a complete, plausible decision
    record -- facilities, objective value, travel times, coverage, artifact
    hashes -- and wrote it to the immutable ledger with no real lineage.
    """
    import pydantic

    from services.api.routers.observatory import DecisionCreateRequest

    with pytest.raises(pydantic.ValidationError) as exc:
        DecisionCreateRequest()

    missing = {err["loc"][0] for err in exc.value.errors() if err["type"] == "missing"}
    for required in (
        "network_version",
        "dataset_version",
        "feature_snapshot_hash",
        "selected_action",
        "opened_facilities",
        "objective_value",
        "expected_travel_seconds",
        "p95_travel_seconds",
        "coverage_basis_points",
        "graph_version",
        "osrm_bundle_hash",
        "solver_version",
    ):
        assert required in missing, f"{required} must be required, not defaulted"


def test_decision_create_rejects_partial_lineage() -> None:
    """F-005 regression: a nearly-complete payload is still refused.

    The original defect was defaults, so a test that only checks the empty body
    would pass even if a single field silently regained one.
    """
    import pydantic

    from services.api.routers.observatory import DecisionCreateRequest

    complete = dict(
        network_version="1.1",
        dataset_version="1.0.0",
        feature_snapshot_hash="a" * 64,
        selected_action="OPEN_FACILITIES",
        opened_facilities=["fac:01"],
        objective_value=1,
        expected_travel_seconds=1,
        p95_travel_seconds=1,
        coverage_basis_points=10000,
        graph_version="1.1",
        osrm_bundle_hash="b" * 64,
        solver_version="ortools-cp-sat",
    )
    assert DecisionCreateRequest(**complete) is not None  # control

    for omitted in complete:
        partial = {k: v for k, v in complete.items() if k != omitted}
        with pytest.raises(pydantic.ValidationError):
            DecisionCreateRequest(**partial)
