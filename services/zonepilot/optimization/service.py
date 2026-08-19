"""Optimization Service coordinating durable job submission and asynchronous Pub/Sub dispatch."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

from services.zonepilot.optimization.contracts import (
    OptimizationProblem,
)
from services.zonepilot.optimization.r1_catalog import default_data_root
from services.zonepilot.optimization.repository import OptimizationRepository
from services.zonepilot.optimization.solver import optimize_facilities
from services.zonepilot.release import current_release_sha

logger = logging.getLogger("onemove.optimization.service")


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

        # 2. Dispatch message to GCP Pub/Sub topic asynchronously
        topic_name = os.environ.get("PUBSUB_TOPIC_OPTIMIZATIONS", "zonepilot-opt-jobs-staging")
        gcp_project = os.environ.get("GCP_PROJECT_ID", "zonepilot-stg-9a4285")
        try:
            from google.cloud import pubsub_v1

            publisher = pubsub_v1.PublisherClient()
            topic_path = publisher.topic_path(gcp_project, topic_name)
            msg_payload = json.dumps(
                {"job_id": job_id, "workspace_id": workspace_id, "idempotency_key": idempotency_key}
            ).encode("utf-8")
            publisher.publish(topic_path, msg_payload, job_id=job_id, workspace_id=workspace_id)
            logger.info(f"Published optimization job {job_id} to Pub/Sub topic {topic_name}")
        except Exception as pub_err:
            # In local test or offline environments where GCP credentials are not active, log dispatch
            logger.debug(f"Pub/Sub publishing skipped or mocked: {pub_err}")

        # Return QUEUED job immediately (HTTP 202 Accepted)
        return self.repository.get_job(job_id, workspace_id) or job

    def run_solver_for_job(
        self,
        job_id: str,
        problem: OptimizationProblem,
        code_sha: str | None = None,
    ) -> dict[str, Any]:
        """Execute CP-SAT solver explicitly (for offline / test / worker runner only)."""
        effective_code_sha = code_sha or current_release_sha()
        start_time = time.perf_counter()
        try:
            result = optimize_facilities(problem)
            run_ms = int((time.perf_counter() - start_time) * 1000)
            self.repository.save_result(
                job_id=job_id,
                result_document=result.model_dump(),
                pareto_document=None,
                problem_fingerprint=result.problem_fingerprint,
                solver_status=result.status.value,
                action=result.action.value,
                fail_closed=result.fail_closed,
                code_sha=effective_code_sha,
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
                run_duration_ms=run_ms,
            )
        return self.repository.get_job(job_id) or {}

    def get_optimization(self, job_id: str, workspace_id: str | None = None) -> dict[str, Any] | None:
        """Fetch verbatim job state and stored result from PostgreSQL."""
        return self.repository.get_job(job_id, workspace_id)
