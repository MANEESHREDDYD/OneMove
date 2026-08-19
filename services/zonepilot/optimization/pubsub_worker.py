"""OneMove Optimization Worker Daemon.

Listens for optimization job notifications or polls durable QUEUED jobs,
claims leases, invokes Google OR-Tools CP-SAT deterministic facility placement,
and persists immutable results.
"""

from __future__ import annotations

import http.server
import json
import logging
import os
import signal
import sys
import threading
import time
import uuid
from typing import Any

from services.zonepilot.optimization.contracts import OptimizationProblem
from services.zonepilot.optimization.repository import OptimizationRepository
from services.zonepilot.optimization.solver import optimize_facilities
from services.zonepilot.release import current_release_sha

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [OneMoveWorker] %(message)s",
)
logger = logging.getLogger("onemove.worker")


class _HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "live", "service": "onemove-worker"}).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        pass


def _start_health_server(port: int = 8080) -> None:
    try:
        server = http.server.HTTPServer(("0.0.0.0", port), _HealthHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        logger.info(f"Health check listener active on port {port}")
    except Exception as exc:
        logger.warning(f"Could not bind health server on port {port}: {exc}")



class OptimizationWorker:
    def __init__(
        self,
        repository: OptimizationRepository | None = None,
        worker_id: str | None = None,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self.repository = repository or OptimizationRepository()
        self.worker_id = worker_id or f"worker-{uuid.uuid4()}"
        self.poll_interval_seconds = poll_interval_seconds
        self._running = True

    def stop(self) -> None:
        self._running = False

    def process_job(self, job: dict[str, Any]) -> bool:
        job_id = str(job["id"])
        workspace_id = job.get("workspace_id")
        logger.info(f"Processing optimization job: {job_id} for workspace: {workspace_id}")

        # Claim lease
        try:
            self.repository.update_job_running(job_id, lease_owner=self.worker_id, lease_seconds=180)
        except Exception as exc:
            logger.error(f"Failed to claim lease on job {job_id}: {exc}")
            return False

        start_time = time.perf_counter()
        effective_code_sha = job.get("code_sha") or current_release_sha()
        payload = job.get("request_payload") or {}

        try:
            problem = OptimizationProblem.model_validate(payload)
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
            logger.info(f"Successfully solved job {job_id} in {run_ms}ms (status={result.status.value})")
            return True
        except Exception as exc:
            run_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Solver error on job {job_id}: {exc}")
            closed_doc = {
                "status": "SOLVER_ERROR",
                "action": "NONE",
                "fail_closed": True,
                "message": str(exc),
            }
            self.repository.save_result(
                job_id=job_id,
                result_document=closed_doc,
                pareto_document=None,
                problem_fingerprint=job.get("request_fingerprint", "unknown"),
                solver_status="SOLVER_ERROR",
                action="NONE",
                fail_closed=True,
                code_sha=effective_code_sha,
                run_duration_ms=run_ms,
            )
            return False

    def run_poll_loop(self, max_iterations: int | None = None) -> None:
        logger.info(f"Starting OneMove Optimization Worker (ID: {self.worker_id})")
        iterations = 0
        while self._running:
            if max_iterations is not None and iterations >= max_iterations:
                break
            iterations += 1
            # Check for queued jobs
            try:
                with self.repository._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT id, requested_by, workspace_id, idempotency_key, request_fingerprint,
                                   request_payload, code_sha
                            FROM public.optimization_jobs
                            WHERE status = 'QUEUED'
                               OR (status = 'RUNNING' AND lease_expires_at < now())
                            ORDER BY created_at ASC
                            LIMIT 1
                            FOR UPDATE SKIP LOCKED
                            """
                        )
                        job = cur.fetchone()
                if job:
                    self.process_job(job)
                else:
                    time.sleep(self.poll_interval_seconds)
            except Exception as exc:
                logger.error(f"Error during worker poll cycle: {exc}")
                time.sleep(self.poll_interval_seconds)


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    _start_health_server(port)
    worker = OptimizationWorker()

    def _sig_handler(sig: int, frame: Any) -> None:
        logger.info("Received termination signal, shutting down worker...")
        worker.stop()

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    worker.run_poll_loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
