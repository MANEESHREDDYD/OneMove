"""Triage legacy NULL-workspace optimization problem snapshots.

Context: optimization_problem_snapshots.workspace_id was nullable, and the RLS
policy exposed NULL-workspace rows to every tenant. Before the column can be
made NOT NULL, every existing NULL row must be classified. Ownership is never
guessed: a row is only backfillable when a single workspace is provably
associated with it.

Evidence used, in order of strength:
  1. decision_records.feature_snapshot_hash -> the workspace that froze a
     decision on this exact snapshot content.
  2. optimization_results.problem_fingerprint -> optimization_jobs.workspace_id,
     the workspace whose job produced the snapshot.

Classifications:
  PROVEN_OWNER         exactly one workspace is evidenced. Backfillable.
  AMBIGUOUS            more than one distinct workspace is evidenced. Quarantine.
  ORPHANED_TEST        no evidence, and the content is recognisably test data.
  LEGACY_PRE_TENANCY   no evidence, predates tenancy enforcement. Quarantine.

Writes SNAPSHOT_TRIAGE.json. Read-only: this script never mutates the database.

Usage:
    DATABASE_URL=... python scripts/incident/triage_null_workspace_snapshots.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# Snapshots created at or before this instant predate workspace enforcement.
TENANCY_ENFORCED_FROM = datetime(2026, 8, 17, 0, 0, 0, tzinfo=timezone.utc)

TEST_MARKERS = ("ws-isolation-", "isolation-test", "ws-blr-01", "test", "pytest", "fixture")

QUERY = """
WITH null_snaps AS (
    SELECT snapshot_id, snapshot_sha256, metadata, created_at
    FROM public.optimization_problem_snapshots
    WHERE workspace_id IS NULL
)
SELECT
    s.snapshot_id,
    s.snapshot_sha256,
    s.created_at,
    s.metadata,
    (
        SELECT array_agg(DISTINCT d.workspace_id)
        FROM public.decision_records d
        WHERE d.feature_snapshot_hash = s.snapshot_sha256
    ) AS decision_workspaces,
    (
        SELECT array_agg(DISTINCT d.decision_id)
        FROM public.decision_records d
        WHERE d.feature_snapshot_hash = s.snapshot_sha256
    ) AS decision_ids,
    (
        SELECT array_agg(DISTINCT j.workspace_id)
        FROM public.optimization_results r
        JOIN public.optimization_jobs j ON j.id = r.job_id
        WHERE r.problem_fingerprint = s.snapshot_sha256
    ) AS job_workspaces,
    (
        SELECT array_agg(DISTINCT r.job_id::text)
        FROM public.optimization_results r
        WHERE r.problem_fingerprint = s.snapshot_sha256
    ) AS job_ids,
    (
        SELECT array_agg(DISTINCT j.requested_by::text)
        FROM public.optimization_results r
        JOIN public.optimization_jobs j ON j.id = r.job_id
        WHERE r.problem_fingerprint = s.snapshot_sha256
    ) AS requested_by
FROM null_snaps s
ORDER BY s.created_at;
"""


def _clean(values) -> list[str]:
    return sorted({str(v) for v in (values or []) if v is not None and str(v).strip()})


def classify(row: dict) -> tuple[str, list[str], str]:
    decision_ws = _clean(row.get("decision_workspaces"))
    job_ws = _clean(row.get("job_workspaces"))
    candidates = sorted(set(decision_ws) | set(job_ws))

    if len(candidates) == 1:
        source = "decision_records" if decision_ws else "optimization_jobs"
        return "PROVEN_OWNER", candidates, f"Exactly one workspace evidenced via {source}."
    if len(candidates) > 1:
        return "AMBIGUOUS", candidates, f"{len(candidates)} distinct workspaces reference this snapshot content."

    blob = json.dumps(row.get("metadata") or {}, default=str).lower()
    if any(marker in blob for marker in TEST_MARKERS):
        return "ORPHANED_TEST", [], "No workspace evidence; metadata carries test markers."

    created = row.get("created_at")
    if created is not None and created <= TENANCY_ENFORCED_FROM:
        return "LEGACY_PRE_TENANCY", [], f"No workspace evidence; created before {TENANCY_ENFORCED_FROM.date()}."
    return "AMBIGUOUS", [], "No workspace evidence and no test markers; ownership cannot be established."


def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        print("DATABASE_URL is required (use the rotated credential).", file=sys.stderr)
        return 2

    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute(QUERY)
            rows = cur.fetchall()

    entries = []
    for row in rows:
        classification, candidates, rationale = classify(row)
        metadata = row.get("metadata") or {}
        entries.append(
            {
                "snapshot_id": row["snapshot_id"],
                "snapshot_sha256": row["snapshot_sha256"],
                "created_at": str(row["created_at"]),
                "optimization_job_ids": _clean(row.get("job_ids")),
                "decision_ids": _clean(row.get("decision_ids")),
                "requested_by": _clean(row.get("requested_by")),
                "evidence_ids": metadata.get("evidence_ids") or [],
                "dataset_version": metadata.get("dataset_version"),
                "code_sha": metadata.get("code_sha"),
                "candidate_workspaces": candidates,
                "classification": classification,
                "rationale": rationale,
                "backfillable": classification == "PROVEN_OWNER",
            }
        )

    counts: dict[str, int] = {}
    for e in entries:
        counts[e["classification"]] = counts.get(e["classification"], 0) + 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "finding": "P0-AUTH-SNAPSHOT-001 / NULL SNAPSHOT INCIDENT",
        "active_null_workspace_snapshots": len(entries),
        "counts_by_classification": counts,
        "backfillable_count": sum(1 for e in entries if e["backfillable"]),
        "requires_manual_decision": sum(1 for e in entries if not e["backfillable"]),
        "migration_precondition_met": len(entries) == 0,
        "snapshots": entries,
    }

    out = Path("SNAPSHOT_TRIAGE.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"ACTIVE_NULL_WORKSPACE_SNAPSHOTS = {len(entries)}")
    for name, count in sorted(counts.items()):
        print(f"  {name}: {count}")
    print(f"wrote {out}")
    print("Only PROVEN_OWNER rows may be backfilled. Everything else must be quarantined or removed deliberately.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
