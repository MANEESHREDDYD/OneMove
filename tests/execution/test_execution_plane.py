"""Invariants of the R0 execution/data plane.

These run without a database on purpose: CI has no Postgres, and the properties
worth defending here are contract properties, not query results. The live
behaviour (concurrent lock claims, real acquisition, idempotent re-runs) is
exercised against the project database during execution and recorded in the run
manifests; what these tests protect is that the *contract* cannot silently drift
away from what was proven.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from services.collectors.execution.evidence import (
    canonical_json,
    record_id_for,
    request_fingerprint,
)
from services.collectors.execution.run_state import (
    ALLOWED_TRANSITIONS,
    IllegalTransition,
    RunStatus,
    assert_transition,
    status_for_http_error,
)
from services.temporal.contracts import EvidenceClass

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
PLANE_SQL = (MIGRATIONS / "20260817001000_r0_execution_plane.sql").read_text(encoding="utf-8")
VERSIONS_SQL = (MIGRATIONS / "20260817001100_r0_dataset_versions.sql").read_text(encoding="utf-8")
ALL_SQL = PLANE_SQL + "\n" + VERSIONS_SQL


# --------------------------------------------------------------------------
# Run state machine
# --------------------------------------------------------------------------

EXPECTED_STATES = {
    "PENDING",
    "RUNNING",
    "SUCCESS",
    "PARTIAL",
    "FAILED",
    "DEGRADED",
    "SKIPPED_NO_CHANGE",
    "AUTH_REQUIRED",
    "RATE_LIMITED",
}


def test_run_status_is_exactly_the_agreed_state_set():
    assert {status.value for status in RunStatus} == EXPECTED_STATES


def test_sql_enum_mirrors_the_python_state_machine():
    """A state that exists in one layer but not the other is a silent data bug."""
    block = PLANE_SQL.split("CREATE TYPE zonepilot_exec.run_status AS ENUM", 1)[1]
    block = block.split(");", 1)[0]
    sql_states = set(re.findall(r"'([A-Z_]+)'", block))
    assert sql_states == EXPECTED_STATES


def test_terminal_states_have_no_outgoing_transitions():
    """Retries must create a new run row, never rewrite a finished one's history."""
    for status, targets in ALLOWED_TRANSITIONS.items():
        if status.is_terminal:
            assert targets == frozenset(), f"{status.value} must be a dead end"
        else:
            assert targets, f"{status.value} must be able to progress"


def test_only_pending_and_running_are_non_terminal():
    non_terminal = {s for s in RunStatus if not s.is_terminal}
    assert non_terminal == {RunStatus.PENDING, RunStatus.RUNNING}


def test_illegal_transition_is_refused():
    with pytest.raises(IllegalTransition):
        assert_transition(RunStatus.SUCCESS, RunStatus.RUNNING)
    with pytest.raises(IllegalTransition):
        assert_transition(RunStatus.PENDING, RunStatus.SUCCESS)
    assert_transition(RunStatus.RUNNING, RunStatus.SUCCESS)


@pytest.mark.parametrize(
    "code,expected",
    [
        (401, RunStatus.AUTH_REQUIRED),
        (403, RunStatus.AUTH_REQUIRED),
        (429, RunStatus.RATE_LIMITED),
        (500, RunStatus.FAILED),
        (404, RunStatus.FAILED),
    ],
)
def test_provider_http_failures_map_onto_the_state_machine(code, expected):
    assert status_for_http_error(code) is expected


# --------------------------------------------------------------------------
# Scheduler lease semantics
# --------------------------------------------------------------------------


def test_scheduler_locks_carries_real_lease_columns():
    block = ALL_SQL.split("CREATE TABLE IF NOT EXISTS zonepilot_exec.scheduler_locks", 1)[1]
    block = block.split("COMMENT ON TABLE", 1)[0]
    for column in ("lease_holder", "acquired_at", "expires_at", "fence_token"):
        assert column in block, f"scheduler_locks must record {column}"
    # lock_name is the primary key: that unique constraint is what makes a
    # double-claim structurally impossible rather than merely unlikely.
    assert "PRIMARY KEY" in block
    assert "expires_at > acquired_at" in block


def test_lock_acquisition_only_takes_over_a_dead_lease():
    """The WHERE on the upsert is the whole mutual-exclusion argument."""
    fn = ALL_SQL.split("FUNCTION zonepilot_exec.acquire_scheduler_lock", 1)[1]
    fn = fn.split("$$;", 1)[0]
    assert "ON CONFLICT (lock_name) DO UPDATE" in fn
    assert "released_at IS NOT NULL" in fn
    assert "expires_at <= now()" in fn
    # A reclaim must advance the fence so a resurrected zombie holder is detectable.
    assert "fence_token" in fn and "+ 1" in fn


def test_release_is_fenced_to_the_current_holder_and_token():
    fn = ALL_SQL.split("FUNCTION zonepilot_exec.release_scheduler_lock", 1)[1]
    fn = fn.split("$$;", 1)[0]
    assert "lease_holder = p_lease_holder" in fn
    assert "fence_token = p_fence_token" in fn


# --------------------------------------------------------------------------
# Tables with real consumers
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "table",
    [
        "collection_runs",
        "collection_checkpoints",
        "provider_states",
        "scheduler_locks",
        "artifact_registry",
        "dataset_versions",
    ],
)
def test_execution_plane_table_exists(table):
    assert f"CREATE TABLE IF NOT EXISTS zonepilot_exec.{table}" in ALL_SQL


def test_a_run_can_only_claim_a_declared_dataset_version():
    assert "collection_runs_dataset_version_fkey" in VERSIONS_SQL
    assert "REFERENCES zonepilot_exec.dataset_versions" in VERSIONS_SQL


# --------------------------------------------------------------------------
# Point-in-time correctness: the property R2 depends on
# --------------------------------------------------------------------------


def test_a_forecast_issue_is_versioned_not_overwritten():
    """issued_at is part of the natural key, so a new cycle appends beside the old."""
    assert "feature_records_forecast_version_unique" in PLANE_SQL
    unique = PLANE_SQL.split("feature_records_forecast_version_unique", 1)[1].split(")", 1)[0]
    for column in ("dataset_id", "provider", "provider_version", "zone_id", "valid_at", "issued_at"):
        assert column in unique, f"{column} must participate in the forecast identity"


def test_information_available_at_never_precedes_issue():
    assert "information_available_at >= issued_at" in PLANE_SQL
    assert "retrieved_at >= information_available_at" in PLANE_SQL


def test_stored_observations_are_immutable():
    """No UPDATE or DELETE path may rewrite an issued forecast in place."""
    assert "reject_feature_record_mutation" in PLANE_SQL


def test_collector_role_is_append_only_on_observations():
    grants = [
        line
        for line in ALL_SQL.splitlines()
        if "zonepilot_r0_collector" in line and line.strip().upper().startswith("GRANT")
    ]
    assert grants, "the collector must be granted something"
    for line in grants:
        assert "DELETE" not in line.upper(), f"collector must never hold DELETE: {line}"
        assert "TRUNCATE" not in line.upper(), f"collector must never hold TRUNCATE: {line}"
    observation_grant = next(line for line in grants if "zonepilot_temporal.feature_records" in line)
    assert "UPDATE" not in observation_grant.upper(), "observations are append-only"


def test_collector_role_cannot_escalate():
    block = PLANE_SQL.split("CREATE ROLE zonepilot_r0_collector", 1)[1].split("END", 1)[0]
    for attribute in ("NOSUPERUSER", "NOCREATEDB", "NOCREATEROLE", "NOBYPASSRLS", "NOREPLICATION"):
        assert attribute in block


# --------------------------------------------------------------------------
# Evidence addressing
# --------------------------------------------------------------------------


def test_evidence_class_is_the_canonical_taxonomy():
    assert EvidenceClass.PUBLIC_OFFICIAL.value == "PUBLIC_OFFICIAL"
    assert len(list(EvidenceClass)) == 9


def test_record_identity_is_stable_and_order_sensitive():
    a = record_id_for(["ds", "open-meteo", "8860145b41fffff", "2026-08-18T00:00:00Z"])
    b = record_id_for(["ds", "open-meteo", "8860145b41fffff", "2026-08-18T00:00:00Z"])
    c = record_id_for(["ds", "open-meteo", "8860145b41fffff", "2026-08-18T01:00:00Z"])
    assert a == b, "the same observation must derive the same id; this is what makes re-runs idempotent"
    assert a != c
    assert re.fullmatch(r"[0-9a-f]{64}", a)


def test_record_identity_refuses_blank_parts():
    with pytest.raises(ValueError):
        record_id_for(["ds", "", "cell"])
    with pytest.raises(ValueError):
        record_id_for([])


def test_request_fingerprint_is_canonical_across_key_order():
    one = request_fingerprint("GET", "https://api.open-meteo.com/v1/forecast", {"latitude": 12.9, "longitude": 77.6})
    two = request_fingerprint("get", "https://api.open-meteo.com/v1/forecast", {"longitude": 77.6, "latitude": 12.9})
    assert one == two


@pytest.mark.parametrize("secret", ["key", "apikey", "api_key", "token", "access_token", "password"])
def test_request_fingerprint_refuses_to_hash_credentials(secret):
    """A fingerprint is published in manifests, so it must never distinguish a key."""
    with pytest.raises(ValueError):
        request_fingerprint("GET", "https://example.invalid", {"latitude": 1, secret: "s3cret"})


def test_canonical_json_is_deterministic():
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


# --------------------------------------------------------------------------
# Pilot area
# --------------------------------------------------------------------------


def test_pilot_area_is_the_agreed_94_cells():
    from services.collectors.execution.pilot_area import (
        PILOT_BBOX,
        PILOT_CELL_COUNT,
        PILOT_H3_RESOLUTION,
        pilot_cells,
    )

    assert PILOT_BBOX == (77.58, 12.90, 77.65, 12.98)
    assert PILOT_H3_RESOLUTION == 8
    assert PILOT_CELL_COUNT == 94
    cells = pilot_cells()
    assert len(cells) == 94
    assert len(set(cells)) == 94
    assert list(cells) == sorted(cells), "cell order must be deterministic"
