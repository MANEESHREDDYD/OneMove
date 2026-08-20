"""Local optimization worker for the demo environment.

The deployed path is outbox -> dispatcher -> Pub/Sub -> Cloud Run worker -> CP-SAT.
There is no Pub/Sub locally, so a submitted job stays QUEUED forever and the demo
cannot complete.

This runner performs exactly what the deployed worker performs: it claims the job
lease, reconstructs the problem from the frozen job payload, runs the real CP-SAT
solver, and persists the result through the same repository with the same fencing.
Only the Pub/Sub TRANSPORT is absent. The solve, the lineage and the stored result
are genuine -- nothing here fabricates an outcome.

Usage:
    python scripts/demo/local_worker.py --once
    python scripts/demo/local_worker.py            # poll until interrupted
"""

from __future__ import annotations

import argparse
import logging
import time
import uuid

from services.zonepilot.optimization.pubsub_worker import _reconstruct_problem_from_payload
from services.zonepilot.optimization.repository import OptimizationRepository
from services.zonepilot.optimization.service import OptimizationService
from services.zonepilot.release import current_release_sha

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("demo.local_worker")

WORKER_ID = f"local-demo-worker-{uuid.uuid4().hex[:8]}"


def claim_and_solve_one(repository: OptimizationRepository, service: OptimizationService) -> bool:
    """Claim one QUEUED job and solve it. Returns True when a job was processed."""
    with repository._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, request_payload
                FROM public.optimization_jobs
                WHERE status = 'QUEUED'
                ORDER BY created_at ASC
                LIMIT 1
                """
            )
            row = cur.fetchone()

    if not row:
        return False

    job_id = str(row["id"])
    lease = repository.claim_job_lease(job_id=job_id, lease_owner=WORKER_ID, lease_seconds=420)
    if not lease:
        logger.info("Job %s already claimed by another worker; skipping.", job_id)
        return True

    logger.info("Claimed job %s; reconstructing problem and solving.", job_id)
    payload = row["request_payload"] or {}
    problem = _reconstruct_problem_from_payload(payload if isinstance(payload, dict) else {})

    result = service.run_solver_for_job(job_id, problem, code_sha=current_release_sha())
    logger.info(
        "Job %s finished: status=%s solver_status=%s",
        job_id,
        result.get("status"),
        result.get("solver_status"),
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="process at most one job then exit")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()

    repository = OptimizationRepository()
    service = OptimizationService(repository=repository)

    logger.info("Local demo worker %s starting.", WORKER_ID)
    while True:
        try:
            processed = claim_and_solve_one(repository, service)
        except Exception:
            logger.exception("Local worker iteration failed")
            processed = False

        if args.once:
            return 0 if processed else 1
        if not processed:
            time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
