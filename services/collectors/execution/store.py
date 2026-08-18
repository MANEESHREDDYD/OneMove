"""Postgres gateway for the R0 execution plane.

Connects with ``EXECUTION_DATABASE_URL``, which must be the dedicated
least-privilege collector login. The DSN is read from the environment, never
logged, and never echoed back in an error message.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from services.collectors.execution.run_state import RunStatus, assert_transition

EXEC_SCHEMA = "zonepilot_exec"
TEMPORAL_SCHEMA = "zonepilot_temporal"
DEFAULT_LEASE_SECONDS = 900


class ExecutionStoreError(RuntimeError):
    """A storage failure whose message never contains the connection string."""


def _dsn() -> str:
    dsn = os.environ.get("EXECUTION_DATABASE_URL", "").strip()
    if not dsn:
        raise ExecutionStoreError("EXECUTION_DATABASE_URL is not set; refusing to run without a target")
    return dsn


@contextmanager
def connect(*, autocommit: bool = False):
    """Open a collector connection. Failures never reveal the DSN."""

    try:
        connection = psycopg.connect(_dsn(), autocommit=autocommit, connect_timeout=30)
    except psycopg.Error as error:
        raise ExecutionStoreError(f"could not connect to the execution database: {type(error).__name__}") from None
    try:
        yield connection
    finally:
        connection.close()


@dataclass
class LeaseHandle:
    lock_name: str
    lease_holder: str
    fence_token: int


class ExecutionStore:
    """Thin, explicit SQL surface. No ORM, no implicit writes."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    # -- leases ------------------------------------------------------------

    def acquire_lease(
        self,
        lock_name: str,
        lease_holder: str,
        *,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        run_id: str | None = None,
    ) -> LeaseHandle | None:
        """Claim a lease, or return ``None`` when a live holder already owns it."""

        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {EXEC_SCHEMA}.acquire_scheduler_lock(%s, %s, %s, %s)",
                (lock_name, lease_holder, lease_seconds, run_id),
            )
            row = cursor.fetchone()
        self._connection.commit()
        if row is None or row[0] is None:
            return None
        return LeaseHandle(lock_name=lock_name, lease_holder=lease_holder, fence_token=int(row[0]))

    def release_lease(self, lease: LeaseHandle) -> bool:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {EXEC_SCHEMA}.release_scheduler_lock(%s, %s, %s)",
                (lease.lock_name, lease.lease_holder, lease.fence_token),
            )
            row = cursor.fetchone()
        self._connection.commit()
        return bool(row and row[0])

    # -- runs --------------------------------------------------------------

    def open_run(
        self,
        *,
        provider: str,
        dataset_id: str,
        dataset_version: str,
        provider_version: str,
        logical_interval: str,
        request_fingerprint: str,
        runner_id: str,
        environment: str,
        public_code_sha: str | None = None,
        workflow_repository: str | None = None,
        workflow_run_id: str | None = None,
        workflow_run_attempt: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {EXEC_SCHEMA}.collection_runs (
                    provider, dataset_id, dataset_version, provider_version,
                    logical_interval, request_fingerprint, status, runner_id, environment,
                    public_code_sha, workflow_repository, workflow_run_id, workflow_run_attempt,
                    heartbeat_at, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, 'PENDING', %s, %s, %s, %s, %s, %s, now(), %s
                )
                RETURNING run_id
                """,
                (
                    provider,
                    dataset_id,
                    dataset_version,
                    provider_version,
                    logical_interval,
                    request_fingerprint,
                    runner_id,
                    environment,
                    public_code_sha,
                    workflow_repository,
                    workflow_run_id,
                    workflow_run_attempt,
                    Jsonb(metadata or {}),
                ),
            )
            run_id = str(cursor.fetchone()[0])
        self._connection.commit()
        return run_id

    def transition_run(
        self,
        run_id: str,
        current: RunStatus,
        target: RunStatus,
        *,
        records_written: int | None = None,
        records_deduplicated: int | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Move a run along the state machine, validated client side and in the database."""

        assert_transition(current, target)

        assignments = ["status = %s", "heartbeat_at = now()"]
        values: list[Any] = [target.value]
        if target.is_terminal:
            assignments.append("finished_at = now()")
        if records_written is not None:
            assignments.append("records_written = %s")
            values.append(records_written)
        if records_deduplicated is not None:
            assignments.append("records_deduplicated = %s")
            values.append(records_deduplicated)
        if failure_code is not None:
            assignments.append("failure_code = %s")
            values.append(failure_code)
        if failure_message is not None:
            assignments.append("failure_message = %s")
            values.append(failure_message[:512])
        if metadata is not None:
            assignments.append("metadata = metadata || %s")
            values.append(Jsonb(metadata))
        values.extend([run_id, current.value])

        with self._connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {EXEC_SCHEMA}.collection_runs SET {', '.join(assignments)} WHERE run_id = %s AND status = %s",
                values,
            )
            if cursor.rowcount != 1:
                raise ExecutionStoreError(
                    f"run {run_id} was not in state {current.value}; refusing to force {target.value}"
                )
        self._connection.commit()

    # -- checkpoints -------------------------------------------------------

    def record_checkpoint(
        self,
        *,
        run_id: str,
        provider: str,
        dataset_id: str,
        sequence_no: int,
        checkpoint_key: str,
        cursor_value: dict[str, Any],
        status: RunStatus,
        records_written: int,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {EXEC_SCHEMA}.collection_checkpoints (
                    run_id, provider, dataset_id, sequence_no, checkpoint_key,
                    cursor_value, status, records_written
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, sequence_no) DO NOTHING
                """,
                (
                    run_id,
                    provider,
                    dataset_id,
                    sequence_no,
                    checkpoint_key,
                    Jsonb(cursor_value),
                    status.value,
                    records_written,
                ),
            )
        self._connection.commit()

    # -- provider cursors --------------------------------------------------

    def get_provider_state(self, provider: str, dataset_id: str, state_key: str) -> Any:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"SELECT state_value FROM {EXEC_SCHEMA}.provider_states "
                "WHERE provider = %s AND dataset_id = %s AND state_key = %s",
                (provider, dataset_id, state_key),
            )
            row = cursor.fetchone()
        return None if row is None else row[0]

    def set_provider_state(
        self, provider: str, dataset_id: str, state_key: str, state_value: Any, run_id: str | None = None
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {EXEC_SCHEMA}.provider_states
                       (provider, dataset_id, state_key, state_value, updated_at, updated_by_run_id)
                VALUES (%s, %s, %s, %s, now(), %s)
                ON CONFLICT (provider, dataset_id, state_key) DO UPDATE
                   SET state_value = excluded.state_value,
                       updated_at = excluded.updated_at,
                       updated_by_run_id = excluded.updated_by_run_id
                """,
                (provider, dataset_id, state_key, Jsonb(state_value), run_id),
            )
        self._connection.commit()

    # -- artifacts ---------------------------------------------------------

    def register_artifact(
        self,
        *,
        run_id: str,
        artifact_hash: str,
        provider: str,
        provider_version: str,
        dataset_id: str,
        dataset_version: str,
        layer: str,
        media_type: str,
        byte_size: int,
        record_count: int,
        issued_at: datetime,
        information_available_at: datetime,
        retrieved_at: datetime,
        evidence_class: str,
        uri: str | None = None,
        request_fingerprint: str | None = None,
    ) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {EXEC_SCHEMA}.artifact_registry (
                    run_id, artifact_hash, provider, provider_version, dataset_id, dataset_version,
                    layer, media_type, byte_size, record_count, uri, request_fingerprint,
                    issued_at, information_available_at, retrieved_at, evidence_class
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id, artifact_hash, layer) DO NOTHING
                """,
                (
                    run_id,
                    artifact_hash,
                    provider,
                    provider_version,
                    dataset_id,
                    dataset_version,
                    layer,
                    media_type,
                    byte_size,
                    record_count,
                    uri,
                    request_fingerprint,
                    issued_at,
                    information_available_at,
                    retrieved_at,
                    evidence_class,
                ),
            )
        self._connection.commit()

    # -- temporal records --------------------------------------------------

    def ensure_unit_set(self, unit_set_id: str, units: dict[str, str]) -> None:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {TEMPORAL_SCHEMA}.feature_unit_sets (unit_set_id, units) "
                "VALUES (%s, %s) ON CONFLICT (unit_set_id) DO NOTHING",
                (unit_set_id, Jsonb(units)),
            )
        self._connection.commit()

    def insert_feature_records(
        self,
        records: Sequence[Any],
        *,
        provider: str,
        provider_version: str,
        run_id: str,
        artifact_hash: str,
        request_fingerprint: str,
        unit_set_id: str,
        batch_size: int = 500,
    ) -> tuple[int, int]:
        """Append records. Returns ``(inserted, already_present)``.

        ``ON CONFLICT DO NOTHING`` is what makes a re-run idempotent: an issue
        already stored for a cell and valid time is left exactly as it was.
        """

        statement = f"""
            INSERT INTO {TEMPORAL_SCHEMA}.feature_records (
                record_id, dataset_id, dataset_version, schema_name, schema_version,
                entity_id, zone_id,
                event_time, issued_at, information_available_at, valid_at, retrieved_at,
                provider, provider_version, source, source_version, evidence_class,
                features, feature_unit_set_id,
                run_id, artifact_hash, request_fingerprint
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT DO NOTHING
        """

        inserted = 0
        attempted = 0
        rows = [
            (
                record.record_id,
                record.dataset_id,
                record.dataset_version,
                record.schema_name,
                record.schema_version,
                record.entity_id,
                record.zone_id,
                record.event_time,
                record.issued_at,
                record.information_available_at,
                record.valid_at,
                record.retrieved_at,
                provider,
                provider_version,
                record.source,
                record.source_version,
                record.evidence_class.value,
                Jsonb(record.features),
                unit_set_id,
                run_id,
                artifact_hash,
                request_fingerprint,
            )
            for record in records
        ]

        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            with self._connection.cursor() as cursor:
                cursor.executemany(statement, batch)
                inserted += max(cursor.rowcount, 0)
            attempted += len(batch)
            self._connection.commit()

        return inserted, attempted - inserted

    # -- read-side proof ---------------------------------------------------

    def count_records(self, dataset_id: str, issued_at: datetime | None = None) -> int:
        with self._connection.cursor() as cursor:
            if issued_at is None:
                cursor.execute(
                    f"SELECT count(*) FROM {TEMPORAL_SCHEMA}.feature_records WHERE dataset_id = %s",
                    (dataset_id,),
                )
            else:
                cursor.execute(
                    f"SELECT count(*) FROM {TEMPORAL_SCHEMA}.feature_records WHERE dataset_id = %s AND issued_at = %s",
                    (dataset_id, issued_at),
                )
            return int(cursor.fetchone()[0])

    def dataset_summary(self, dataset_id: str) -> dict[str, Any]:
        with self._connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT count(*)                        AS records,
                       count(DISTINCT zone_id)         AS zones,
                       count(DISTINCT issued_at)       AS forecast_issues,
                       min(valid_at)                   AS valid_from,
                       max(valid_at)                   AS valid_to,
                       min(information_available_at)   AS available_from,
                       max(information_available_at)   AS available_to
                  FROM {TEMPORAL_SCHEMA}.feature_records
                 WHERE dataset_id = %s
                """,
                (dataset_id,),
            )
            row = cursor.fetchone()
        keys = (
            "records",
            "zones",
            "forecast_issues",
            "valid_from",
            "valid_to",
            "available_from",
            "available_to",
        )
        return dict(zip(keys, row, strict=True))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def json_safe(value: Any) -> Any:
    """Render datetimes for JSON without dragging in a serializer dependency."""

    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def dumps(value: Any) -> str:
    return json.dumps(json_safe(value), sort_keys=True, separators=(",", ":"))


def chunked(items: Iterable[Any], size: int) -> Iterable[list[Any]]:
    batch: list[Any] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
