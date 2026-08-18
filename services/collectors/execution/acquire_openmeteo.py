"""Entry point the private execution plane calls to acquire one Open-Meteo cycle.

    python -m services.collectors.execution.acquire_openmeteo --environment staging

Reads ``EXECUTION_DATABASE_URL`` from the environment. Writes a run row, the raw
artifact registration, and one immutable temporal record per (pilot cell, valid
hour) for the current provider forecast cycle. Emits a run manifest on stdout as
JSON so the caller can archive it.

Safe to run repeatedly. Inside one provider cycle a re-run inserts zero rows and
reports ``SKIPPED_NO_CHANGE``; when the provider issues a new cycle, the new
issue is appended beside the old one and neither overwrites the other.
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from datetime import timezone
from typing import Any

from services.collectors.execution import openmeteo_forecast as om
from services.collectors.execution.run_state import RunStatus
from services.collectors.execution.store import ExecutionStore, ExecutionStoreError, connect, dumps, utc_now

MANIFEST_SCHEMA_VERSION = "1.0.0"
LOCK_NAME = f"acquire:{om.PROVIDER}:{om.DATASET_ID}"


def _runner_id() -> str:
    workflow_run = os.environ.get("GITHUB_RUN_ID")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    if workflow_run:
        return f"gha:{os.environ.get('GITHUB_REPOSITORY', 'unknown')}:{workflow_run}:{attempt}"
    return f"local:{socket.gethostname()}:{os.getpid()}"


def _iso(value: Any) -> Any:
    if hasattr(value, "astimezone"):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", default=os.environ.get("EXECUTION_ENVIRONMENT", "local"),
                        choices=["staging", "production", "local"])
    parser.add_argument("--model", default=om.DEFAULT_MODEL, choices=sorted(om.MODEL_META_IDS))
    parser.add_argument("--forecast-days", type=int, default=2)
    parser.add_argument("--lease-seconds", type=int, default=900)
    parser.add_argument("--manifest-out", default=None, help="Also write the manifest to this path.")
    return parser


def run(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    runner_id = _runner_id()
    started_at = utc_now()
    public_code_sha = os.environ.get("ZONEPILOT_PUBLIC_CODE_SHA") or os.environ.get("GITHUB_SHA")
    if public_code_sha is not None and len(public_code_sha) != 40:
        public_code_sha = None

    # Ask the provider what it has issued *before* touching the database, so a
    # cycle that has not advanced never even opens a run against a live lease.
    result = om.acquire(model=args.model, forecast_days=args.forecast_days)
    issue = result.issue

    with connect() as connection:
        store = ExecutionStore(connection)

        lease = store.acquire_lease(LOCK_NAME, runner_id, lease_seconds=args.lease_seconds)
        if lease is None:
            manifest = _manifest(
                run_id=None, status=RunStatus.SKIPPED_NO_CHANGE, args=args, result=result,
                started_at=started_at, inserted=0, deduplicated=0,
                public_code_sha=public_code_sha,
                note="another runner holds a live lease on this dataset",
            )
            return 0, manifest

        run_id = None
        try:
            run_id = store.open_run(
                provider=om.PROVIDER,
                dataset_id=om.DATASET_ID,
                dataset_version=om.DATASET_VERSION,
                provider_version=result.provider_version,
                logical_interval=issue.logical_interval,
                request_fingerprint=result.request_fingerprint,
                runner_id=runner_id,
                environment=args.environment,
                public_code_sha=public_code_sha,
                workflow_repository=os.environ.get("GITHUB_REPOSITORY"),
                workflow_run_id=os.environ.get("GITHUB_RUN_ID"),
                workflow_run_attempt=int(os.environ.get("GITHUB_RUN_ATTEMPT", "0")) or None,
                metadata={
                    "model": issue.model,
                    "update_interval_seconds": issue.update_interval_seconds,
                    "temporal_resolution_seconds": issue.temporal_resolution_seconds,
                    "model_meta_sha256": issue.meta_hash,
                    "pilot_cells": len({record.zone_id for record in result.records}),
                    "provider_grid_points": len(result.grid_points),
                },
            )
            store.transition_run(run_id, RunStatus.PENDING, RunStatus.RUNNING)

            store.register_artifact(
                run_id=run_id,
                artifact_hash=result.artifact_hash,
                provider=om.PROVIDER,
                provider_version=result.provider_version,
                dataset_id=om.DATASET_ID,
                dataset_version=om.DATASET_VERSION,
                layer="RAW",
                media_type="application/json",
                byte_size=len(result.raw_payload),
                record_count=len(result.records),
                uri=f"provider+https://api.open-meteo.com/v1/forecast#{result.request_fingerprint}",
                request_fingerprint=result.request_fingerprint,
                issued_at=issue.issued_at,
                information_available_at=issue.information_available_at,
                retrieved_at=result.retrieved_at,
                evidence_class=om.EVIDENCE_CLASS.value,
            )

            units = om.feature_units()
            unit_set = om.unit_set_id(units)
            store.ensure_unit_set(unit_set, units)

            inserted, deduplicated = store.insert_feature_records(
                result.records,
                provider=om.PROVIDER,
                provider_version=result.provider_version,
                run_id=run_id,
                artifact_hash=result.artifact_hash,
                request_fingerprint=result.request_fingerprint,
                unit_set_id=unit_set,
            )

            store.record_checkpoint(
                run_id=run_id,
                provider=om.PROVIDER,
                dataset_id=om.DATASET_ID,
                sequence_no=0,
                checkpoint_key=issue.logical_interval,
                cursor_value={
                    "issued_at": _iso(issue.issued_at),
                    "inserted": inserted,
                    "deduplicated": deduplicated,
                },
                status=RunStatus.SUCCESS,
                records_written=inserted,
            )

            # Nothing new means the provider has not re-issued since the last run.
            # That is a healthy outcome, not a failure, and it is not SUCCESS either.
            terminal = RunStatus.SUCCESS if inserted > 0 else RunStatus.SKIPPED_NO_CHANGE
            store.transition_run(
                run_id, RunStatus.RUNNING, terminal,
                records_written=inserted, records_deduplicated=deduplicated,
            )

            store.set_provider_state(
                om.PROVIDER, om.DATASET_ID, "last_issued_at",
                {"issued_at": _iso(issue.issued_at), "model": issue.model, "records": inserted},
                run_id=run_id,
            )

            summary = store.dataset_summary(om.DATASET_ID)
            manifest = _manifest(
                run_id=run_id, status=terminal, args=args, result=result,
                started_at=started_at, inserted=inserted, deduplicated=deduplicated,
                public_code_sha=public_code_sha, dataset_summary=summary,
            )
            return 0, manifest

        except Exception as error:  # noqa: BLE001 - every failure must close the run out
            status = getattr(error, "status", RunStatus.FAILED)
            code = getattr(error, "code", "EXECUTOR_EXCEPTION")
            if run_id is not None:
                try:
                    store.transition_run(
                        run_id, RunStatus.RUNNING, status,
                        failure_code=code, failure_message=f"{type(error).__name__}: {error}"[:512],
                    )
                except ExecutionStoreError:
                    pass
            manifest = _manifest(
                run_id=run_id, status=status, args=args, result=result,
                started_at=started_at, inserted=0, deduplicated=0,
                public_code_sha=public_code_sha,
                failure={"code": code, "safe_message": f"{type(error).__name__}: {error}"[:512]},
            )
            return 1, manifest
        finally:
            store.release_lease(lease)


def _manifest(
    *,
    run_id: str | None,
    status: RunStatus,
    args: argparse.Namespace,
    result: om.AcquisitionResult,
    started_at: Any,
    inserted: int,
    deduplicated: int,
    public_code_sha: str | None,
    dataset_summary: dict[str, Any] | None = None,
    failure: dict[str, str] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    valid_from, valid_to = result.valid_at_range
    finished_at = utc_now()
    issue = result.issue

    manifest: dict[str, Any] = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": run_id or "unclaimed",
        "status": "succeeded" if not status.is_failure else "failed",
        "run_state": status.value,
        "environment": args.environment,
        "generated_at": _iso(finished_at),
        "public_source": {
            "repository": "MANEESHREDDYD/OneMove",
            "code_sha": public_code_sha or "0" * 40,
        },
        "execution": {
            "workflow_repository": os.environ.get("GITHUB_REPOSITORY", "local"),
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID", "local"),
            "workflow_run_attempt": int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
            "started_at": _iso(started_at),
            "finished_at": _iso(finished_at),
            "scheduled_interval": {
                "start": _iso(issue.issued_at),
                "end": _iso(result.retrieved_at),
            },
        },
        "reconciliation": {
            "expected_interval_count": 1,
            "completed_interval_count": 0 if status.is_failure else 1,
            "missed_intervals": [],
            "predecessor_manifest_sha256": None,
        },
        "datasets": [
            {
                "dataset_id": om.DATASET_ID,
                "dataset_version": om.DATASET_VERSION,
                "layer": "SILVER",
                "schema_version": "1.0.0",
                "source": om.FORECAST_URL,
                "source_version": f"{issue.model}@{_iso(issue.issued_at)}",
                "provider": om.PROVIDER,
                "provider_version": result.provider_version,
                "evidence_class": om.EVIDENCE_CLASS.value,
                "issued_at": _iso(issue.issued_at),
                "information_available_at": _iso(issue.information_available_at),
                "retrieved_at": _iso(result.retrieved_at),
                "time_range": {"start": _iso(valid_from), "end": _iso(valid_to)},
                "information_availability_range": {
                    "start": _iso(issue.information_available_at),
                    "end": _iso(result.retrieved_at),
                },
                "record_count": inserted,
                "records_deduplicated": deduplicated,
                "input_hashes": sorted({result.artifact_hash, issue.meta_hash}),
                "request_fingerprint": result.request_fingerprint,
                "artifact": {
                    "uri": f"pg://zonepilot_temporal.feature_records?run_id={run_id or 'none'}",
                    "sha256": result.artifact_hash,
                    "bytes": len(result.raw_payload),
                    "content_type": "application/json",
                },
                "retention_days": int(os.environ.get("DERIVED_ARTIFACT_RETENTION_DAYS", "365")),
            }
        ],
        "failure": failure,
    }
    if note:
        manifest["note"] = note
    if dataset_summary:
        manifest["dataset_state"] = {key: _iso(value) for key, value in dataset_summary.items()}
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        exit_code, manifest = run(args)
    except om.AcquisitionError as error:
        print(f"acquisition failed [{error.code}]: {error}", file=sys.stderr)
        return 1
    except ExecutionStoreError as error:
        print(f"execution store unavailable: {error}", file=sys.stderr)
        return 2

    rendered = dumps(manifest)
    print(rendered)
    if args.manifest_out:
        with open(args.manifest_out, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
