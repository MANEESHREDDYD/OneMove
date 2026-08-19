"""PostgreSQL Repository for durable Optimization Jobs and Results."""

from __future__ import annotations

import json
import uuid
from typing import Any

import psycopg
from psycopg.rows import dict_row

from services.common.db_dsn import get_database_dsn


def _is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


class OptimizationRepository:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or get_database_dsn()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=15)

    def create_job(
        self,
        *,
        requested_by: str,
        workspace_id: str,
        idempotency_key: str,
        request_fingerprint: str,
        request_payload: dict[str, Any],
        graph_version: str | None = None,
        dataset_version: str | None = None,
        matrix_id: str | None = None,
        assumption_version: str | None = None,
        solver_version: str | None = None,
        code_sha: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, requested_by, workspace_id, idempotency_key, request_fingerprint,
                           status, solver_status, fail_closed, created_at, started_at, finished_at
                    FROM public.optimization_jobs
                    WHERE requested_by = %s::uuid AND idempotency_key = %s
                    """,
                    (requested_by, idempotency_key),
                )
                existing = cur.fetchone()
                if existing:
                    if existing["request_fingerprint"] != request_fingerprint:
                        raise ValueError(
                            f"Idempotency key {idempotency_key} was already used with a different request fingerprint"
                        )
                    return existing

                job_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO public.optimization_jobs (
                        id, requested_by, workspace_id, idempotency_key, request_fingerprint,
                        request_payload, graph_version, dataset_version, matrix_id,
                        assumption_version, solver_version, code_sha, status
                    ) VALUES (
                        %s::uuid, %s::uuid, %s, %s, %s,
                        %s::jsonb, %s, %s, %s,
                        %s, %s, %s, 'QUEUED'
                    )
                    RETURNING id, requested_by, workspace_id, idempotency_key, request_fingerprint,
                              status, solver_status, fail_closed, created_at, started_at, finished_at
                    """,
                    (
                        job_id,
                        requested_by,
                        workspace_id,
                        idempotency_key,
                        request_fingerprint,
                        json.dumps(request_payload),
                        graph_version,
                        dataset_version,
                        matrix_id,
                        assumption_version,
                        solver_version,
                        code_sha,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
            return row

    def get_job(self, job_id: str, workspace_id: str | None = None) -> dict[str, Any] | None:
        if not _is_valid_uuid(job_id):
            return None

        with self._connect() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT j.id, j.requested_by, j.workspace_id, j.idempotency_key, j.request_fingerprint,
                           j.request_payload, j.graph_version, j.dataset_version, j.matrix_id,
                           j.assumption_version, j.solver_version, j.code_sha, j.status, j.solver_status,
                           j.fail_closed, j.failure_code, j.failure_message, j.created_at, j.started_at,
                           j.finished_at, j.queue_wait_ms, j.run_duration_ms,
                           r.result_document, r.pareto_document
                    FROM public.optimization_jobs j
                    LEFT JOIN public.optimization_results r ON r.job_id = j.id
                    WHERE j.id = %s::uuid
                """
                params: list[Any] = [job_id]
                if workspace_id:
                    query += " AND j.workspace_id = %s"
                    params.append(workspace_id)

                cur.execute(query, params)
                return cur.fetchone()

    def list_jobs(self, workspace_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, requested_by, workspace_id, idempotency_key, request_fingerprint,
                           status, solver_status, fail_closed, created_at, started_at, finished_at
                    FROM public.optimization_jobs
                    WHERE workspace_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (workspace_id, limit),
                )
                return cur.fetchall()

    def claim_job_lease(self, job_id: str, lease_owner: str, lease_seconds: int = 120) -> dict[str, Any] | None:
        """Atomically claim execution lease on a QUEUED or expired RUNNING job."""
        if not _is_valid_uuid(job_id):
            return None
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.optimization_jobs
                    SET status = 'RUNNING',
                        started_at = COALESCE(started_at, now()),
                        lease_owner = %s,
                        lease_expires_at = now() + (%s || ' seconds')::interval,
                        attempt_count = attempt_count + 1,
                        updated_at = now()
                    WHERE id = %s::uuid
                      AND (
                        status = 'QUEUED'
                        OR (status = 'RUNNING' AND (lease_expires_at IS NULL OR lease_expires_at < now()))
                      )
                    RETURNING id, requested_by, workspace_id, idempotency_key, request_fingerprint,
                              request_payload, graph_version, dataset_version, matrix_id,
                              assumption_version, solver_version, code_sha, status, solver_status,
                              attempt_count, lease_owner, lease_expires_at
                    """,
                    (lease_owner, str(lease_seconds), job_id),
                )
                row = cur.fetchone()
            conn.commit()
            return row

    def update_job_running(self, job_id: str, lease_owner: str, lease_seconds: int = 120) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.optimization_jobs
                    SET status = 'RUNNING',
                        started_at = now(),
                        lease_owner = %s,
                        lease_expires_at = now() + (%s || ' seconds')::interval,
                        attempt_count = attempt_count + 1,
                        updated_at = now()
                    WHERE id = %s::uuid
                    """,
                    (lease_owner, str(lease_seconds), job_id),
                )
            conn.commit()

    def save_result(
        self,
        *,
        job_id: str,
        result_document: dict[str, Any],
        pareto_document: dict[str, Any] | None,
        problem_fingerprint: str,
        solver_status: str,
        action: str,
        fail_closed: bool,
        code_sha: str = "c7e24e8d378db6a2f19048993bb3803e76f125c2",
        graph_version: str = "1.1",
        assumption_version: str = "r1-proxy-1.0.0",
        solver_version: str = "ortools-cp-sat",
        scenario_evidence_classes: list[str] | None = None,
        run_duration_ms: int = 0,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                status = "SUCCESS" if not fail_closed and solver_status == "OPTIMAL" else "FAILED"
                cur.execute(
                    """
                    UPDATE public.optimization_jobs
                    SET status = %s,
                        solver_status = %s,
                        fail_closed = %s,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        finished_at = now(),
                        run_duration_ms = %s,
                        updated_at = now()
                    WHERE id = %s::uuid
                    """,
                    (status, solver_status, fail_closed, run_duration_ms, job_id),
                )
                cur.execute(
                    """
                    INSERT INTO public.optimization_results (
                        job_id, result_document, pareto_document, problem_fingerprint,
                        solver_status, action, fail_closed, graph_version,
                        assumption_version, solver_version, scenario_evidence_classes,
                        solver_wall_time_seconds
                    ) VALUES (
                        %s::uuid, %s::jsonb, %s::jsonb, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s
                    )
                    ON CONFLICT (job_id) DO UPDATE SET
                        result_document = EXCLUDED.result_document,
                        solver_status = EXCLUDED.solver_status,
                        action = EXCLUDED.action,
                        fail_closed = EXCLUDED.fail_closed
                    """,
                    (
                        job_id,
                        json.dumps(result_document, default=str),
                        json.dumps(pareto_document, default=str) if pareto_document else None,
                        problem_fingerprint,
                        solver_status,
                        action,
                        fail_closed,
                        graph_version,
                        assumption_version,
                        solver_version,
                        scenario_evidence_classes or ["PUBLIC_GEOGRAPHIC"],
                        round(run_duration_ms / 1000.0, 4),
                    ),
                )
            conn.commit()
