"""Optimization Service coordinating durable job execution and OR-Tools solver invocation."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

from services.zonepilot.optimization.contracts import (
    OptimizationProblem,
)
from services.zonepilot.optimization.r1_catalog import default_data_root
from services.zonepilot.optimization.repository import OptimizationRepository
from services.zonepilot.optimization.solver import optimize_facilities


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
        code_sha: str = "c7e24e8d378db6a2f19048993bb3803e76f125c2",
    ) -> dict[str, Any]:
        """Submit a deterministic optimization problem, persist to Postgres, and solve."""
        payload = custom_payload or (problem.model_dump() if problem else {})
        req_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        req_fp = hashlib.sha256(req_bytes).hexdigest()

        graph_ver = problem.scenarios[0].travel_matrix.graph_version if (problem and problem.scenarios) else "1.1"
        dataset_ver = "1.0.0"
        matrix_id = problem.scenarios[0].travel_matrix.matrix_id if (problem and problem.scenarios) else "r1-table"
        assumption_ver = problem.objective_weights.assumption_version if problem else "r1-proxy-1.0.0"

        # 1. Idempotently create or retrieve job
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
            code_sha=code_sha,
        )

        job_id = str(job["id"])
        # If job already terminal, return it
        if job["status"] in {"SUCCESS", "FAILED"}:
            return self.repository.get_job(job_id, workspace_id) or job

        # 2. Mark job RUNNING
        worker_id = f"worker-{uuid.uuid4()}"
        self.repository.update_job_running(job_id, lease_owner=worker_id)

        # 3. Solve if problem provided
        start_time = time.perf_counter()
        if problem is not None:
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
                    code_sha=code_sha,
                    run_duration_ms=run_ms,
                )
            except Exception as exc:
                run_ms = int((time.perf_counter() - start_time) * 1000)
                closed_doc = {
                    "problem_id": problem.problem_id,
                    "status": "SOLVER_ERROR",
                    "action": "NONE",
                    "fail_closed": True,
                    "message": str(exc),
                }
                self.repository.save_result(
                    job_id=job_id,
                    result_document=closed_doc,
                    pareto_document=None,
                    problem_fingerprint=req_fp,
                    solver_status="SOLVER_ERROR",
                    action="NONE",
                    fail_closed=True,
                    code_sha=code_sha,
                    run_duration_ms=run_ms,
                )

        return self.repository.get_job(job_id, workspace_id) or job

    def get_optimization(self, job_id: str, workspace_id: str | None = None) -> dict[str, Any] | None:
        """Fetch verbatim job state and stored result from PostgreSQL."""
        return self.repository.get_job(job_id, workspace_id)
