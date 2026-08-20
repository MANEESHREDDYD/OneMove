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

from services.zonepilot.optimization import pubsub_worker as pubsub_worker_module
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


# --- F-022: worker lease fencing -------------------------------------------


def test_worker_lease_outlives_the_pubsub_ack_deadline() -> None:
    """A lease shorter than the ack deadline lets a redelivery run a second solve."""
    from services.zonepilot.optimization import pubsub_worker

    assert pubsub_worker.JOB_LEASE_SECONDS > pubsub_worker.PUBSUB_ACK_DEADLINE_SECONDS


def test_result_writes_are_fenced_on_the_worker_lease() -> None:
    """A worker whose lease was reclaimed must not overwrite the result."""
    save = inspect.getsource(repo_module.OptimizationRepository.save_result)
    assert "lease_owner" in inspect.signature(repo_module.OptimizationRepository.save_result).parameters
    assert "lease_owner = %s::text" in save, "the job update must match the holder's lease"
    assert "return False" in save, "a lost lease must report failure rather than writing"

    worker = inspect.getsource(pubsub_worker_module.process_pubsub_push)
    assert worker.count("lease_owner=worker_id") >= 2, "both result paths must pass the fence"


def test_save_result_reports_whether_it_won() -> None:
    sig = inspect.signature(repo_module.OptimizationRepository.save_result)
    assert sig.return_annotation in (bool, "bool")


# --- Certifier residuals: poison payload and lost-lease reporting ---------------


def test_poison_payload_cannot_abort_the_batch() -> None:
    """One malformed event must not strand its already-claimed siblings.

    Payload decoding used to sit outside the try, so a single bad row raised out
    of the whole loop leaving every sibling leased with a burned attempt and
    publishable by nobody until the lease expired.
    """
    dispatch = inspect.getsource(service_module.OptimizationService.dispatch_outbox_events)
    body = dispatch[dispatch.index("for event in pending_events:") :]

    decode_at = body.index("json.loads")
    first_try = body.index("try:")
    assert first_try < decode_at, "payload decoding must be inside a per-event try"

    assert "OUTBOX_POISON_PAYLOAD" in body
    # The bad event must release its lease rather than being abandoned mid-lease.
    poison = body[body.index("OUTBOX_POISON_PAYLOAD") :]
    assert "mark_outbox_failed" in poison
    assert "continue" in poison, "the loop must carry on to the remaining events"


def test_lost_lease_is_not_reported_as_success() -> None:
    """A discarded duplicate solve must be visible to monitoring."""
    worker = inspect.getsource(pubsub_worker_module.process_pubsub_push)

    assert "persisted = _repository.save_result" in worker, "the fence result must be inspected"
    assert "WORKER_RESULT_FENCE_REJECTED" in worker
    assert "DUPLICATE_SOLVE_DISCARDED" in worker

    rejected = worker[worker.index("if not persisted:") :]
    success_at = worker.index("solved successfully")
    assert worker.index("if not persisted:") < success_at, "the fence check must precede the success log"
    assert "result_persisted" in rejected
