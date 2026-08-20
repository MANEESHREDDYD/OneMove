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
        self._explicit_dsn = dsn

    @property
    def dsn(self) -> str:
        """Resolve the DSN lazily, at connection time rather than construction.

        Repositories used to call get_database_dsn() in __init__. Routers build
        them at module scope, so importing the API package required database
        configuration to already be present: an unset DATABASE_URL made the
        process unimportable, took liveness down with it, and turned 18 test
        modules into collection errors instead of clean skips (F-024).
        """
        return self._explicit_dsn or get_database_dsn()

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

                # Atomically enqueue transactional outbox event
                outbox_payload = {
                    "job_id": job_id,
                    "workspace_id": workspace_id,
                    "idempotency_key": idempotency_key,
                    "graph_version": graph_version,
                    "dataset_version": dataset_version,
                }
                cur.execute(
                    """
                    INSERT INTO public.optimization_outbox (
                        aggregate_id, workspace_id, event_type, payload, status
                    ) VALUES (
                        %s::uuid, %s, 'OPTIMIZATION_SUBMITTED', %s::jsonb, 'PENDING'
                    )
                    """,
                    (job_id, workspace_id, json.dumps(outbox_payload)),
                )
            conn.commit()
            return row

    def get_job(self, job_id: str, workspace_id: str) -> dict[str, Any] | None:
        """Fetch a job, strictly scoped to the owning workspace.

        The backend uses an owner-role DSN, so RLS is not in force here and this
        predicate is the only tenant-isolation control. Use get_job_system() for
        the worker/dispatcher paths that must resolve a job before its owning
        workspace is known.
        """
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("get_job requires a non-empty workspace_id")
        return self._get_job_row(job_id, workspace_id)

    def get_job_system(self, job_id: str) -> dict[str, Any] | None:
        """Privileged, deliberately unscoped job lookup for system services.

        Only the Pub/Sub worker and the solver runner may use this: both are
        invoked with a job id and must discover the owning workspace from the
        authoritative row rather than trusting a caller-supplied value. It is
        named distinctly so an unscoped read can never happen by accident, and
        so the static tenancy contract test can tell the two apart.
        """
        return self._get_job_row(job_id, None)

    def _get_job_row(self, job_id: str, workspace_id: str | None) -> dict[str, Any] | None:
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
                # Two explicit statements rather than a conditionally appended
                # predicate: the tenant-scoped and privileged system reads must be
                # distinguishable by inspection, never by a runtime branch.
                if workspace_id is None:
                    cur.execute(query, [job_id])
                else:
                    cur.execute(query + " AND j.workspace_id = %s", [job_id, workspace_id])
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
        code_sha: str,
        graph_version: str,
        assumption_version: str,
        solver_version: str,
        scenario_evidence_classes: list[str] | None = None,
        run_duration_ms: int = 0,
    ) -> None:
        """Persist a solver result together with its execution lineage.

        Every lineage field is REQUIRED. These previously carried literal defaults
        -- a hard-coded code_sha, graph_version "1.1", assumption_version
        "r1-proxy-1.0.0", solver_version "ortools-cp-sat" -- so a result recorded
        without them claimed provenance it never had, and replay compared against
        a build that may never have produced it (F-011).

        The persistence layer does not know the execution context and must never
        guess it. The caller supplies real lineage or the write fails closed.
        """
        missing = [
            name
            for name, value in (
                ("code_sha", code_sha),
                ("graph_version", graph_version),
                ("assumption_version", assumption_version),
                ("solver_version", solver_version),
            )
            if not value or not str(value).strip()
        ]
        if missing:
            raise ValueError(f"save_result requires authoritative lineage; missing or empty: {', '.join(missing)}")

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

    # ------------------------------------------------------------------
    # Transactional outbox: durable claim protocol with lease fencing
    # ------------------------------------------------------------------
    #
    # AUDIT-3: the previous implementation ran SELECT ... FOR UPDATE SKIP LOCKED
    # inside `with self._connect()`, which commits and closes the connection on
    # block exit. Every row lock was released before the caller published, and
    # the rows were left status='PENDING', so two dispatcher instances published
    # the same events. The protocol below is two-phase:
    #
    #   claim()    -> ONE transaction: lock candidate rows, flip them to
    #                 'CLAIMED' with (lease_owner, lease_expires_at,
    #                 fencing_token), commit. Publishing happens strictly after
    #                 this transaction has committed.
    #   finalize() -> every terminal transition is gated on the fencing
    #                 predicate (status='CLAIMED' AND fencing_token = :token
    #                 AND lease_owner = :owner). Zero rows updated means the
    #                 lease expired and was stolen by another dispatcher: the
    #                 caller MUST NOT mutate the event any further.

    OUTBOX_CLAIMABLE_PREDICATE = """
        (status = 'PENDING' AND next_attempt_at <= now())
        OR (status = 'CLAIMED' AND lease_expires_at IS NOT NULL AND lease_expires_at < now())
    """

    def claim_pending_outbox_events(
        self,
        limit: int = 10,
        owner: str | None = None,
        lease_seconds: int = 60,
    ) -> list[dict[str, Any]]:
        """Atomically lease a batch of outbox events for exactly-one-publisher delivery.

        Runs entirely inside a single transaction: candidate rows are locked with
        FOR UPDATE SKIP LOCKED and updated to 'CLAIMED' in the same statement, so
        the row state (not a transient lock) is what excludes a concurrent
        dispatcher. Two dispatchers running this concurrently receive strictly
        disjoint sets.

        A row whose attempt_count has already reached max_attempts is moved to
        'DEAD' rather than re-leased; such rows are returned with status='DEAD'
        so the caller can observe the dead-lettering, and must not be published.

        Returns rows including ``fencing_token``, which the caller must hand back
        to :meth:`mark_outbox_published` / :meth:`mark_outbox_failed`.
        """
        lease_owner = owner or "unknown-dispatcher"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    WITH claimable AS (
                        SELECT event_id
                        FROM public.optimization_outbox
                        WHERE {self.OUTBOX_CLAIMABLE_PREDICATE}
                        ORDER BY created_at ASC
                        LIMIT %s
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE public.optimization_outbox AS o
                    SET status = CASE
                            WHEN o.attempt_count >= o.max_attempts THEN 'DEAD'
                            ELSE 'CLAIMED'
                        END,
                        attempt_count = CASE
                            WHEN o.attempt_count >= o.max_attempts THEN o.attempt_count
                            ELSE o.attempt_count + 1
                        END,
                        attempts = CASE
                            WHEN o.attempt_count >= o.max_attempts THEN o.attempt_count
                            ELSE o.attempt_count + 1
                        END,
                        lease_owner = CASE
                            WHEN o.attempt_count >= o.max_attempts THEN NULL
                            ELSE %s
                        END,
                        lease_expires_at = CASE
                            WHEN o.attempt_count >= o.max_attempts THEN NULL
                            ELSE now() + (%s || ' seconds')::interval
                        END,
                        fencing_token = CASE
                            WHEN o.attempt_count >= o.max_attempts THEN NULL
                            ELSE gen_random_uuid()
                        END,
                        last_error = CASE
                            WHEN o.attempt_count >= o.max_attempts
                                THEN 'dead-lettered: attempt_count reached max_attempts'
                            ELSE o.last_error
                        END,
                        updated_at = now()
                    FROM claimable c
                    WHERE o.event_id = c.event_id
                    RETURNING o.event_id, o.aggregate_id, o.workspace_id, o.event_type, o.payload,
                              o.status, o.attempt_count, o.attempts, o.max_attempts,
                              o.fencing_token, o.lease_owner, o.lease_expires_at
                    """,
                    (limit, lease_owner, str(lease_seconds)),
                )
                rows = cur.fetchall()
            conn.commit()
            return rows

    def mark_outbox_published(
        self,
        event_id: str,
        fencing_token: str | None = None,
        lease_owner: str | None = None,
        pubsub_message_id: str | None = None,
    ) -> bool:
        """Finalize a published outbox event under its fencing token.

        Returns True when the row was transitioned to 'PUBLISHED'. Returns False
        when the fencing predicate did not match, which means this dispatcher
        lost its lease (it expired and another instance re-claimed the row).
        On False the caller MUST NOT mutate the event any further - not even to
        record a failure - because the row now belongs to the new lease holder.
        """
        if not _is_valid_uuid(event_id) or not fencing_token or not _is_valid_uuid(str(fencing_token)):
            return False
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.optimization_outbox
                    SET status = 'PUBLISHED',
                        published_at = now(),
                        pubsub_message_id = %s,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        last_error = NULL,
                        updated_at = now()
                    WHERE event_id = %s::uuid
                      AND status = 'CLAIMED'
                      AND fencing_token = %s::uuid
                      AND lease_owner = %s
                    """,
                    (pubsub_message_id, event_id, str(fencing_token), lease_owner),
                )
                updated = cur.rowcount
            conn.commit()
            return updated > 0

    def mark_outbox_failed(
        self,
        event_id: str,
        error_message: str,
        fencing_token: str | None = None,
        lease_owner: str | None = None,
        backoff_seconds: int = 10,
    ) -> bool:
        """Release a failed delivery attempt under the same fencing predicate.

        The attempt counter was already incremented at claim time, so this only
        schedules the retry backoff and drops the lease. A row that has reached
        max_attempts is dead-lettered to 'DEAD' (never 'FAILED', which is
        reserved for non-retryable poison events).

        Returns False if the lease was lost; the caller must leave the row alone.
        """
        if not _is_valid_uuid(event_id) or not fencing_token or not _is_valid_uuid(str(fencing_token)):
            return False
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.optimization_outbox
                    SET last_error = %s,
                        next_attempt_at = now() + (%s || ' seconds')::interval,
                        status = CASE WHEN attempt_count >= max_attempts THEN 'DEAD' ELSE 'PENDING' END,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        fencing_token = NULL,
                        updated_at = now()
                    WHERE event_id = %s::uuid
                      AND status = 'CLAIMED'
                      AND fencing_token = %s::uuid
                      AND lease_owner = %s
                    """,
                    (
                        (error_message or "")[:500],
                        str(backoff_seconds),
                        event_id,
                        str(fencing_token),
                        lease_owner,
                    ),
                )
                updated = cur.rowcount
            conn.commit()
            return updated > 0

    def get_outbox_event(self, event_id: str) -> dict[str, Any] | None:
        """Fetch a single outbox event row (operational inspection and tests)."""
        if not _is_valid_uuid(event_id):
            return None
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT event_id, aggregate_id, workspace_id, event_type, payload, status,
                           attempt_count, attempts, max_attempts, fencing_token, lease_owner,
                           lease_expires_at, next_attempt_at, published_at, pubsub_message_id,
                           last_error, created_at, updated_at
                    FROM public.optimization_outbox
                    WHERE event_id = %s::uuid
                    """,
                    (event_id,),
                )
                return cur.fetchone()

    def get_oldest_pending_outbox_age_seconds(self) -> float:
        """Return the age in seconds of the oldest undelivered outbox event for monitoring SLOs.

        'CLAIMED' counts as undelivered: a leased-but-unpublished event is still
        backlog, and excluding it would mask a dispatcher that claims and stalls.
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COALESCE(EXTRACT(EPOCH FROM (now() - MIN(created_at))), 0.0) as age_seconds
                    FROM public.optimization_outbox
                    WHERE status IN ('PENDING', 'CLAIMED')
                    """
                )
                row = cur.fetchone()
                return float(row["age_seconds"]) if row else 0.0

    def save_problem_snapshot(self, snapshot: Any, workspace_id: str) -> None:
        """Persist an immutable, workspace-scoped problem snapshot to PostgreSQL.

        workspace_id is mandatory: a snapshot with no owning tenant would be
        readable by every tenant (P0-AUTH-SNAPSHOT-001). Fail closed instead.
        """
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("save_problem_snapshot requires a non-empty workspace_id; global snapshots are forbidden")
        snap_dict = snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else snapshot
        snap_id = snap_dict["problem_snapshot_id"]
        snap_sha = snap_dict["problem_snapshot_sha256"]
        problem_json = snap_dict["problem"]
        metadata = {
            "code_sha": snap_dict.get("code_sha"),
            "dataset_version": snap_dict.get("dataset_version"),
            "graph_version": snap_dict.get("graph_version"),
            "assumption_version": snap_dict.get("assumption_version"),
            "solver_version": snap_dict.get("solver_version"),
            "matrix_sha256": snap_dict.get("matrix_sha256"),
            "gold_manifest_sha256": snap_dict.get("gold_manifest_sha256"),
            "evidence_ids": snap_dict.get("evidence_ids"),
            "created_at": snap_dict.get("created_at"),
            "temporal_cutoff": snap_dict.get("temporal_cutoff"),
        }

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.optimization_problem_snapshots (
                        snapshot_id, snapshot_sha256, workspace_id, problem_json, metadata, created_at
                    ) VALUES (
                        %s, %s, %s, %s::jsonb, %s::jsonb, now()
                    )
                    ON CONFLICT (snapshot_id) DO NOTHING
                    """,
                    (
                        snap_id,
                        snap_sha,
                        workspace_id,
                        json.dumps(problem_json, default=str),
                        json.dumps(metadata, default=str),
                    ),
                )
            conn.commit()

    def get_problem_snapshot(self, snapshot_id_or_hash: str, workspace_id: str) -> dict[str, Any] | None:
        """Fetch an immutable problem snapshot, strictly scoped to the requesting workspace.

        This repository connects with an owner-role DSN, so PostgreSQL RLS is NOT in
        force on this path; this WHERE clause is the only tenant-isolation control.
        The workspace predicate is therefore mandatory and non-optional
        (P0-AUTH-SNAPSHOT-001). Rows with a NULL workspace_id never match, so legacy
        unscoped snapshots are unreadable rather than globally readable.
        """
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("get_problem_snapshot requires a non-empty workspace_id")

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT snapshot_id, snapshot_sha256, workspace_id, problem_json, metadata, created_at
                    FROM public.optimization_problem_snapshots
                    WHERE (snapshot_id = %s OR snapshot_sha256 = %s)
                      AND workspace_id IS NOT NULL
                      AND workspace_id = %s
                    LIMIT 1
                    """,
                    (snapshot_id_or_hash, snapshot_id_or_hash, workspace_id),
                )
                row = cur.fetchone()
                if not row:
                    return None

                res = {
                    "problem_snapshot_id": row["snapshot_id"],
                    "problem_snapshot_sha256": row["snapshot_sha256"],
                    "workspace_id": row["workspace_id"],
                    "problem": row["problem_json"]
                    if isinstance(row["problem_json"], dict)
                    else json.loads(row["problem_json"]),
                    "created_at": str(row["created_at"]),
                }
                meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"])
                res.update(meta)
                return res
