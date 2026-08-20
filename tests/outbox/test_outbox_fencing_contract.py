"""F-008 / F-009: outbox claim protocol and lease fencing.

The previous implementation ran SELECT ... FOR UPDATE SKIP LOCKED inside a
connection context manager that commits and closes on exit, releasing every row
lock before the publish and leaving rows PENDING. Two dispatchers therefore
published the same event.

These tests assert the SQL contract statically plus the dispatcher's lost-lease
handling, so they run without a database.
"""

from __future__ import annotations

import inspect
import re

from services.zonepilot.optimization import repository as repo_module
from services.zonepilot.optimization import service as service_module

REPO_SRC = inspect.getsource(repo_module)
SERVICE_SRC = inspect.getsource(service_module.OptimizationService.dispatch_outbox_events)


def test_claim_transitions_rows_out_of_pending() -> None:
    """State, not a transient lock, must exclude a concurrent dispatcher."""
    claim = inspect.getsource(repo_module.OptimizationRepository.claim_pending_outbox_events)
    assert "FOR UPDATE SKIP LOCKED" in claim
    assert "UPDATE public.optimization_outbox" in claim
    assert "'CLAIMED'" in claim, "claim must move rows to CLAIMED in the same transaction"
    assert "gen_random_uuid()" in claim, "each claim must mint a fresh fencing token"
    assert "lease_expires_at" in claim


def test_claim_returns_the_fencing_token() -> None:
    claim = inspect.getsource(repo_module.OptimizationRepository.claim_pending_outbox_events)
    returning = claim[claim.index("RETURNING") :]
    assert "fencing_token" in returning
    assert "lease_owner" in returning


def test_expired_leases_are_reclaimable() -> None:
    predicate = repo_module.OptimizationRepository.OUTBOX_CLAIMABLE_PREDICATE
    assert "status = 'PENDING'" in predicate
    assert "status = 'CLAIMED'" in predicate and "lease_expires_at < now()" in predicate


def test_exhausted_events_are_dead_lettered_not_republished() -> None:
    claim = inspect.getsource(repo_module.OptimizationRepository.claim_pending_outbox_events)
    assert "'DEAD'" in claim and "max_attempts" in claim
    # The dispatcher must skip them rather than publish.
    assert 'if str(event.get("status")) == "DEAD"' in SERVICE_SRC
    assert "not publishing" in SERVICE_SRC


def test_finalizers_are_gated_on_the_fencing_predicate() -> None:
    """A dispatcher that lost its lease must not be able to mutate the row."""
    for name in ("mark_outbox_published", "mark_outbox_failed"):
        src = inspect.getsource(getattr(repo_module.OptimizationRepository, name))
        where = src[src.index("WHERE event_id") :]
        assert "status = 'CLAIMED'" in where, f"{name} must require the row to still be CLAIMED"
        assert "fencing_token = %s" in where, f"{name} must match the fencing token"
        assert "lease_owner = %s" in where, f"{name} must match the lease owner"
        assert re.search(r"return\s+updated\s*>\s*0", src), f"{name} must report whether it won"


def test_dispatcher_stops_on_lost_lease() -> None:
    """Zero rows updated means another dispatcher owns the row now."""
    assert "if not finalized:" in SERVICE_SRC
    assert "LOST_LEASE" in SERVICE_SRC
    # After a lost lease the loop must continue, never fall through to more writes.
    assert SERVICE_SRC.count("continue") >= 2


def test_each_dispatcher_run_uses_a_distinct_lease_owner() -> None:
    assert "socket.gethostname()" in SERVICE_SRC and "uuid.uuid4()" in SERVICE_SRC


def test_claim_commits_before_publishing() -> None:
    """Publishing must happen strictly after the claim transaction commits."""
    claim_at = SERVICE_SRC.index("claim_pending_outbox_events")
    publish_at = SERVICE_SRC.index("publisher.publish")
    assert claim_at < publish_at
    claim_src = inspect.getsource(repo_module.OptimizationRepository.claim_pending_outbox_events)
    assert "conn.commit()" in claim_src
