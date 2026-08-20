"""Optimization Service coordinating durable job submission and asynchronous Pub/Sub dispatch."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import time
import uuid
from typing import Any

from services.zonepilot.optimization.contracts import (
    OptimizationProblem,
)
from services.zonepilot.optimization.r1_catalog import default_data_root
from services.zonepilot.optimization.repository import OptimizationRepository
from services.zonepilot.optimization.solver import optimize_facilities
from services.zonepilot.release import current_release_sha

logger = logging.getLogger("onemove.optimization.service")


def _resolve_solver_version() -> str:
    """Report the solver version actually installed, not a literal.

    Recording "ortools-cp-sat" told a replay nothing about which solver produced a
    result. The installed distribution version is real provenance and changes when
    the solver changes (F-011).
    """
    try:
        from importlib.metadata import version

        return f"ortools-cp-sat-{version('ortools')}"
    except Exception:
        # Provenance we cannot establish is reported as such, never guessed.
        return "ortools-cp-sat-UNKNOWN_VERSION"


SOLVER_VERSION = _resolve_solver_version()


class OptimizationService:
    def __init__(
        self,
        repository: OptimizationRepository | None = None,
        data_root: Any | None = None,
    ) -> None:
        self.repository = repository or OptimizationRepository()
        self.data_root = data_root or default_data_root()

    def submit_optimization(
        self,
        *,
        requested_by: str,
        workspace_id: str,
        idempotency_key: str,
        problem: OptimizationProblem | None = None,
        custom_payload: dict[str, Any] | None = None,
        code_sha: str | None = None,
    ) -> dict[str, Any]:
        """Submit an optimization job to PostgreSQL in QUEUED state and dispatch to Pub/Sub.

        The API process MUST NOT invoke CP-SAT synchronously; the solver is executed
        exclusively by the asynchronous worker process.
        """
        effective_code_sha = code_sha or current_release_sha()
        payload = custom_payload or (problem.model_dump() if problem else {})
        req_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        req_fp = hashlib.sha256(req_bytes).hexdigest()

        graph_ver = problem.scenarios[0].travel_matrix.graph_version if (problem and problem.scenarios) else "1.1"
        dataset_ver = "1.0.0"
        matrix_id = problem.scenarios[0].travel_matrix.matrix_id if (problem and problem.scenarios) else "r1-table"
        assumption_ver = problem.objective_weights.assumption_version if problem else "r1-proxy-1.0.0"

        # 1. Idempotently create or retrieve job in QUEUED state
        job = self.repository.create_job(
            requested_by=requested_by,
            workspace_id=workspace_id,
            idempotency_key=idempotency_key,
            request_fingerprint=req_fp,
            request_payload=payload,
            graph_version=graph_ver,
            dataset_version=dataset_ver,
            matrix_id=matrix_id,
            assumption_version=assumption_ver,
            solver_version="ortools-cp-sat",
            code_sha=effective_code_sha,
        )

        job_id = str(job["id"])

        # 2. Return QUEUED job immediately (HTTP 202 Accepted) without blocking API request on external Pub/Sub
        dispatch_status = "QUEUED_PENDING_DISPATCH"
        if os.environ.get("SYNC_OUTBOX_DISPATCH", "false").lower() in {"1", "true"}:
            try:
                dispatched_count = self.dispatch_outbox_events(limit=5)
                if dispatched_count > 0:
                    dispatch_status = "QUEUED_DISPATCHED"
            except Exception as dispatch_err:
                logger.debug(f"Outbox dispatch deferred to background dispatcher: {dispatch_err}")

        result_job = dict(self.repository.get_job(job_id, workspace_id) or job)
        result_job["dispatch_status"] = dispatch_status
        return result_job

    def dispatch_outbox_events(self, limit: int = 10, lease_seconds: int = 60) -> int:
        """Claim and publish pending outbox events to Google Cloud Pub/Sub.

        Claiming and publishing are strictly ordered: the claim transaction commits
        before any publish happens, and every finalize carries the fencing token
        issued at claim time. A dispatcher whose lease expired and was stolen sees
        a False return and leaves the row alone (AUDIT-3 / F-008, F-009).
        """
        lease_owner = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        pending_events = self.repository.claim_pending_outbox_events(
            limit=limit, owner=lease_owner, lease_seconds=lease_seconds
        )
        if not pending_events:
            return 0

        topic_name = os.environ.get("PUBSUB_TOPIC_OPTIMIZATIONS")
        gcp_project = os.environ.get("GCP_PROJECT_ID")
        env = os.environ.get("ENVIRONMENT", "").lower()

        if env in {"staging", "production"} and (not topic_name or not gcp_project):
            raise RuntimeError(
                f"Missing required cloud configuration in {env} environment: GCP_PROJECT_ID and PUBSUB_TOPIC_OPTIMIZATIONS must be set."
            )

        if not topic_name or not gcp_project:
            logger.debug("Pub/Sub configuration not set in local environment; outbox events will remain queued.")
            return 0

        dispatched_count = 0

        for event in pending_events:
            event_id = str(event["event_id"])
            attempts = int(event.get("attempt_count", event.get("attempts", 0)))
            fencing_token = str(event.get("fencing_token") or "")

            # Per-event isolation. Payload decoding used to sit outside the try
            # below, so a single malformed row raised out of the whole loop and
            # abandoned every sibling this dispatcher had already CLAIMED --
            # each one holding a lease and a burned attempt, publishable by
            # nobody until the lease expired. One poison event must not take a
            # batch with it.
            try:
                raw = event["payload"]
                payload = raw if isinstance(raw, dict) else json.loads(raw)
                job_id = str(event["aggregate_id"])
                workspace_id = str(event["workspace_id"])
            except (TypeError, ValueError, KeyError) as decode_err:
                logger.error(
                    "OUTBOX_POISON_PAYLOAD",
                    extra={
                        "event": "OUTBOX_POISON_PAYLOAD",
                        "event_id": event_id,
                        "attempts": attempts,
                        "error": str(decode_err),
                    },
                )
                # Release the lease so the row is not stranded, and let the normal
                # attempt ceiling dead-letter it rather than retrying forever.
                self.repository.mark_outbox_failed(
                    event_id,
                    f"POISON_PAYLOAD: {decode_err}",
                    fencing_token=fencing_token,
                    lease_owner=lease_owner,
                    backoff_seconds=600,
                )
                continue

            # Rows the claim transaction dead-lettered are returned for
            # observability only. They hold no lease and must not be published.
            if str(event.get("status")) == "DEAD":
                logger.error(
                    f"Outbox event {event_id} for job {job_id} dead-lettered after {attempts} attempts; not publishing."
                )
                continue

            try:
                from google.cloud import pubsub_v1

                publisher = pubsub_v1.PublisherClient()
                topic_path = publisher.topic_path(gcp_project, topic_name)
                msg_bytes = json.dumps(payload).encode("utf-8")
                future = publisher.publish(topic_path, msg_bytes, job_id=job_id, workspace_id=workspace_id)
                msg_id = future.result(timeout=10) if hasattr(future, "result") else str(future)
                finalized = self.repository.mark_outbox_published(
                    event_id,
                    fencing_token=fencing_token,
                    lease_owner=lease_owner,
                    pubsub_message_id=str(msg_id),
                )
                if not finalized:
                    # Published, but the lease was lost before we could record it.
                    # The new holder will publish again; the worker is idempotent.
                    # Never mutate the row - it belongs to another dispatcher now.
                    logger.error(
                        f"LOST_LEASE finalizing outbox event {event_id} (job {job_id}); "
                        f"published as {msg_id} but the row was re-claimed. Possible duplicate delivery."
                    )
                    continue
                dispatched_count += 1
                logger.info(f"Outbox event {event_id} for job {job_id} published to Pub/Sub msg {msg_id}")
            except Exception as pub_err:
                backoff = min(600, 10 * (2**attempts))
                released = self.repository.mark_outbox_failed(
                    event_id,
                    str(pub_err),
                    fencing_token=fencing_token,
                    lease_owner=lease_owner,
                    backoff_seconds=backoff,
                )
                if not released:
                    logger.error(f"LOST_LEASE releasing outbox event {event_id}; leaving it to the new holder.")
                    continue
                logger.warning(
                    f"Outbox publish attempt {attempts} failed for event {event_id}: {pub_err}. Backoff: {backoff}s"
                )

        return dispatched_count

    def run_solver_for_job(
        self,
        job_id: str,
        problem: OptimizationProblem,
        code_sha: str | None = None,
    ) -> dict[str, Any]:
        """Execute CP-SAT solver explicitly (for offline / test / worker runner only)."""
        effective_code_sha = code_sha or current_release_sha()
        start_time = time.perf_counter()

        # Resolve the owning tenant from the authoritative job row rather than trusting
        # a caller-supplied value. Snapshots must never be persisted unscoped
        # (P0-AUTH-SNAPSHOT-001).
        job_row = self.repository.get_job_system(job_id)
        if not job_row:
            raise LookupError(f"Optimization job {job_id} not found; cannot resolve owning workspace")
        job_workspace_id = str(job_row["workspace_id"] or "").strip()
        # Lineage comes from the frozen job context. A solver failure may still be
        # recorded, but it must reference the REAL context it was solving -- a
        # placeholder like "UNKNOWN"/"UNVERSIONED" is invented provenance and is
        # exactly what F-011 exists to forbid. If the job row lacks lineage, that is
        # a data defect upstream, so fail closed rather than paper over it.
        job_graph_version = str(job_row.get("graph_version") or "").strip()
        job_assumption_version = str(job_row.get("assumption_version") or "").strip()
        missing_lineage = [
            name
            for name, value in (
                ("graph_version", job_graph_version),
                ("assumption_version", job_assumption_version),
            )
            if not value
        ]
        if missing_lineage:
            raise ValueError(
                f"Optimization job {job_id} is missing frozen lineage: {', '.join(missing_lineage)}. "
                "Refusing to persist a result with invented provenance."
            )
        if not job_workspace_id:
            raise ValueError(f"Optimization job {job_id} has no workspace_id; refusing to persist a global snapshot")

        try:
            from services.zonepilot.optimization.contracts import create_problem_snapshot

            manifest_path = self.data_root / "private" / "official" / "manifests" / "gold_manifest.json"
            matrix_sha = ""
            gold_sha = ""
            if manifest_path.is_file():
                try:
                    m_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
                    matrix_sha = m_doc.get("osrm_bundle_sha256") or m_doc.get("osrm_table_sha256") or ""
                    gold_sha = m_doc.get("gold_h3_table_sha256") or ""
                except Exception:
                    pass

            graph_ver = problem.scenarios[0].travel_matrix.graph_version if problem.scenarios else "1.1"
            matrix_id = problem.scenarios[0].travel_matrix.matrix_id if problem.scenarios else "r1-table"
            evidence_ids = (
                f"ev-gold-network-{graph_ver}",
                f"ev-osrm-{matrix_id}",
                f"ev-opt-job-{job_id}",
            )

            snapshot = create_problem_snapshot(
                problem,
                code_sha=effective_code_sha,
                dataset_version="1.0.0",
                matrix_sha256=matrix_sha,
                gold_manifest_sha256=gold_sha,
                evidence_ids=evidence_ids,
            )
            # The snapshot is the authoritative frozen assumption reference. If it
            # carries none, the result cannot claim one.
            snapshot_assumption_version = str(getattr(snapshot, "assumption_version", "") or "").strip()
            if not snapshot_assumption_version:
                snapshot_assumption_version = job_assumption_version

            self.repository.save_problem_snapshot(snapshot, workspace_id=job_workspace_id)

            result = optimize_facilities(problem)
            run_ms = int((time.perf_counter() - start_time) * 1000)

            result_doc = result.model_dump()
            result_doc["evidence_ids"] = list(evidence_ids)
            result_doc["problem_snapshot_id"] = snapshot.problem_snapshot_id
            result_doc["problem_snapshot_sha256"] = snapshot.problem_snapshot_sha256
            result_doc["dataset_version"] = "1.0.0"
            result_doc["network_version"] = graph_ver
            result_doc["solver_version"] = SOLVER_VERSION

            self.repository.save_result(
                job_id=job_id,
                result_document=result_doc,
                pareto_document=None,
                problem_fingerprint=snapshot.problem_snapshot_sha256,
                solver_status=result.status.value,
                action=result.action.value,
                fail_closed=result.fail_closed,
                code_sha=effective_code_sha,
                graph_version=graph_ver,
                assumption_version=snapshot_assumption_version,
                solver_version=SOLVER_VERSION,
                run_duration_ms=run_ms,
            )
        except Exception as exc:
            run_ms = int((time.perf_counter() - start_time) * 1000)
            closed_doc = {
                "problem_id": problem.problem_id,
                "status": "SOLVER_ERROR",
                "action": "NONE",
                "fail_closed": True,
                "error_message": str(exc),
            }
            self.repository.save_result(
                job_id=job_id,
                result_document=closed_doc,
                pareto_document=None,
                problem_fingerprint=f"err-{job_id}",
                solver_status="FAILED",
                action="NONE",
                fail_closed=True,
                code_sha=effective_code_sha,
                graph_version=job_graph_version,
                assumption_version=job_assumption_version,
                solver_version=SOLVER_VERSION,
                run_duration_ms=run_ms,
            )
        return self.repository.get_job_system(job_id) or {}

    def get_optimization(self, job_id: str, workspace_id: str) -> dict[str, Any] | None:
        """Fetch verbatim job state and stored result from PostgreSQL."""
        return self.repository.get_job(job_id, workspace_id)
