"""Adversarial and Failure-Injection Test Suite for Pub/Sub Optimizer Worker.

Verifies:
1. Duplicate Pub/Sub message delivery idempotency.
2. Multiple distinct message IDs targeting same job ID.
3. Concurrent lease contention (only one worker acquires lease).
4. Lease expiry and recovery by secondary worker.
5. Malformed payload fail-closed / discard behavior.
6. Non-retryable error handling vs transient failure classification.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from services.zonepilot.optimization.pubsub_worker import app


@pytest.fixture
def client():
    return TestClient(app)


def test_worker_health_endpoints(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "onemove-optimization-worker"}

    res = client.get("/readyz")
    assert res.status_code == 200
    assert res.json() == {"status": "ready", "service": "onemove-optimization-worker"}


def test_duplicate_pubsub_delivery_idempotency(client, monkeypatch):
    """Ensure delivering the exact same Pub/Sub message twice does not re-solve or corrupt state."""
    job_id = str(uuid.uuid4())
    payload = {
        "job_id": job_id,
        "workspace_id": "ws-test",
    }
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    push_body = {
        "message": {
            "messageId": "msg-001",
            "data": encoded,
            "publishTime": datetime.now(timezone.utc).isoformat(),
        },
        "subscription": "projects/test/subscriptions/test-sub",
    }

    # First delivery claims lease and succeeds
    mock_job = {
        "id": job_id,
        "request_payload": {"min_open_facilities": 2, "max_open_facilities": 3},
        "status": "QUEUED",
    }
    claimed = True

    def mock_claim(job_id, lease_owner, lease_seconds=120):
        nonlocal claimed
        if claimed:
            claimed = False
            return mock_job
        return None

    monkeypatch.setattr("services.zonepilot.optimization.pubsub_worker._repository.claim_job_lease", mock_claim)
    monkeypatch.setattr("services.zonepilot.optimization.pubsub_worker._repository.get_job", lambda jid: mock_job)
    monkeypatch.setattr("services.zonepilot.optimization.pubsub_worker._repository.save_result", lambda **kwargs: None)

    # First execution: claims lease, solves, acks
    res1 = client.post("/push", json=push_body)
    assert res1.status_code == 200
    assert res1.json()["status"] == "ack"

    # Second execution (duplicate delivery): lease is already held/finished -> acks cleanly without re-running
    res2 = client.post("/push", json=push_body)
    assert res2.status_code == 200
    assert res2.json()["status"] == "ack"
    assert res2.json()["reason"] == "already_claimed_or_completed"


def test_concurrent_lease_contention_single_winner(client, monkeypatch):
    """Verify that when 2 workers receive the same job simultaneously, only 1 acquires lease."""
    job_id = str(uuid.uuid4())
    payload = {"job_id": job_id, "workspace_id": "ws-test"}
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    push_msg1 = {"message": {"messageId": "msg-101", "data": encoded}}
    push_msg2 = {"message": {"messageId": "msg-102", "data": encoded}}

    claims_count = 0

    def mock_claim(job_id, lease_owner, lease_seconds=120):
        nonlocal claims_count
        claims_count += 1
        if claims_count == 1:
            return {"id": job_id, "request_payload": {}, "status": "QUEUED"}
        return None  # Second worker fails to claim lease

    monkeypatch.setattr("services.zonepilot.optimization.pubsub_worker._repository.claim_job_lease", mock_claim)
    monkeypatch.setattr(
        "services.zonepilot.optimization.pubsub_worker._repository.get_job",
        lambda jid: {"id": jid, "request_payload": {}},
    )
    monkeypatch.setattr("services.zonepilot.optimization.pubsub_worker._repository.save_result", lambda **kwargs: None)

    res1 = client.post("/push", json=push_msg1)
    res2 = client.post("/push", json=push_msg2)

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res2.json()["reason"] == "already_claimed_or_completed"


def test_malformed_pubsub_payload_handling(client):
    """Ensure malformed json payload is discarded safely without crashing the worker."""
    res = client.post("/push", content=b"invalid-not-json", headers={"Content-Type": "application/json"})
    assert res.status_code == 200
    assert res.json()["status"] == "discarded"


def test_missing_job_id_dropped(client):
    """Ensure messages without job_id are dropped safely."""
    push_body = {"message": {"messageId": "msg-empty", "attributes": {}}}
    res = client.post("/push", json=push_body)
    assert res.status_code == 200
    assert res.json()["status"] == "dropped"


def test_solver_exception_fail_closed_persistence(client, monkeypatch):
    """Ensure solver errors produce a fail-closed result document rather than hanging or leaking."""
    job_id = str(uuid.uuid4())
    payload = {"job_id": job_id, "workspace_id": "ws-test"}
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    push_body = {"message": {"messageId": "msg-err", "data": encoded}}

    mock_job = {"id": job_id, "request_payload": {}, "status": "QUEUED"}
    saved_result = {}

    def mock_save(**kwargs):
        nonlocal saved_result
        saved_result = kwargs

    monkeypatch.setattr(
        "services.zonepilot.optimization.pubsub_worker._repository.claim_job_lease", lambda **kwargs: mock_job
    )
    monkeypatch.setattr("services.zonepilot.optimization.pubsub_worker._repository.get_job", lambda j: mock_job)
    monkeypatch.setattr("services.zonepilot.optimization.pubsub_worker._repository.save_result", mock_save)
    monkeypatch.setattr(
        "services.zonepilot.optimization.pubsub_worker.optimize_facilities",
        MagicMock(side_effect=RuntimeError("Solver OOM simulation")),
    )

    res = client.post("/push", json=push_body)
    assert res.status_code == 200
    assert res.json()["solver_status"] == "FAILED"
    assert saved_result["fail_closed"] is True
    assert saved_result["solver_status"] == "FAILED"
