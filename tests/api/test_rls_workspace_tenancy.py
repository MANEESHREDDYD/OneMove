"""Workspace tenancy and temporal correctness, proven against a real Postgres.

These tests talk to Postgres directly rather than through PostgREST, because
what is under test is the row-level security decision itself: which rows a
session may see, and which rows the temporal CHECK constraints will accept.

A session is simulated the way Supabase does it at runtime -- ``SET LOCAL ROLE
authenticated`` plus a ``request.jwt.claims`` setting that ``auth.uid()`` reads.
Every test runs inside a transaction that is rolled back, so the suite leaves no
rows behind and can run against a shared database.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

psycopg = pytest.importorskip("psycopg", reason="psycopg is required for tenancy proofs")

ENV_FILE = os.environ.get("ZONEPILOT_ENV_FILE", "C:/Users/md200/OneDrive/Desktop/OneMove/OneMove.env")


def _pooler_dsn_from_env_file() -> str | None:
    """Derive the session-pooler DSN from a local Supabase env file.

    The direct ``db.<ref>.supabase.co`` host in that file is IPv6-only and is
    unreachable from most CI runners, so the pooler host is used instead.
    """

    try:
        raw = open(ENV_FILE, encoding="utf-8", errors="replace").read()
    except OSError:
        return None

    from urllib.parse import quote

    for line in raw.splitlines():
        if "postgresql://" not in line:
            continue
        url = line.strip()[line.strip().index("postgresql://") :]
        body = url[len("postgresql://") :]
        try:
            creds, hostpart = body.rsplit("@", 1)  # last @: the password contains one
            _user, pwd = creds.split(":", 1)
            ref = hostpart.split(":")[0].split(".")[1]
        except (IndexError, ValueError):
            return None
        return (
            f"postgresql://postgres.{ref}:{quote(pwd, safe='')}"
            "@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require"
        )
    return None


def _dsn() -> str | None:
    for key in ("ZONEPILOT_TEST_DB_URL", "ZONEPILOT_DB_URL", "DIRECT_URL", "DATABASE_URL"):
        value = os.environ.get(key)
        if value and value.startswith("postgres"):
            return value
    return _pooler_dsn_from_env_file()


DSN = _dsn()


def _reachable(dsn: str | None) -> bool:
    if not dsn:
        return False
    try:
        with psycopg.connect(dsn, connect_timeout=15) as conn, conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.workspaces')")
            return cur.fetchone()[0] is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _reachable(DSN),
    reason="No reachable Postgres with the tenancy migration applied",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn():
    connection = psycopg.connect(DSN, connect_timeout=30)
    connection.autocommit = False
    try:
        yield connection
    finally:
        # Nothing this suite does is ever committed.
        connection.rollback()
        connection.close()


class Fixture:
    """Two workspaces and one user per role, seeded inside the transaction."""

    def __init__(self, cur):
        self.cur = cur
        self.workspace_a = str(uuid.uuid4())
        self.workspace_b = str(uuid.uuid4())
        suffix = uuid.uuid4().hex[:10]

        cur.execute(
            "INSERT INTO workspaces (id, slug, name) VALUES (%s, %s, %s), (%s, %s, %s)",
            (
                self.workspace_a,
                f"ws-a-{suffix}",
                "Workspace A",
                self.workspace_b,
                f"ws-b-{suffix}",
                "Workspace B",
            ),
        )

        self.users: dict[str, str] = {}
        for label, workspace, role in (
            ("a_owner", self.workspace_a, "OWNER"),
            ("a_admin", self.workspace_a, "ADMIN"),
            ("a_researcher", self.workspace_a, "RESEARCHER"),
            ("a_viewer", self.workspace_a, "VIEWER"),
            ("a_integration", self.workspace_a, "INTEGRATION_USER"),
            ("a_collector", self.workspace_a, "COLLECTOR"),
            ("b_owner", self.workspace_b, "OWNER"),
            ("outsider", None, None),
        ):
            user_id = self._make_user(label, suffix)
            self.users[label] = user_id
            if workspace is not None:
                cur.execute(
                    "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (%s, %s, %s)",
                    (workspace, user_id, role),
                )

    def _make_user(self, label: str, suffix: str) -> str:
        user_id = str(uuid.uuid4())
        self.cur.execute(
            """
            INSERT INTO auth.users (id, instance_id, aud, role, email)
            VALUES (%s, '00000000-0000-0000-0000-000000000000', 'authenticated',
                    'authenticated', %s)
            """,
            (user_id, f"{label}-{suffix}@tenancy.test"),
        )
        return user_id

    def as_user(self, label: str) -> None:
        """Adopt the session identity of a seeded user."""

        self.cur.execute("SET LOCAL ROLE authenticated")
        self.cur.execute(
            "SELECT set_config('request.jwt.claims', %s, true)",
            (json.dumps({"sub": self.users[label], "role": "authenticated"}),),
        )

    def as_service(self) -> None:
        """Drop back to the privileged identity used for seeding."""

        self.cur.execute("RESET ROLE")
        self.cur.execute("SELECT set_config('request.jwt.claims', NULL, true)")


@pytest.fixture()
def fx(conn):
    with conn.cursor() as cur:
        yield Fixture(cur)


# ---------------------------------------------------------------------------
# Observation row helper
# ---------------------------------------------------------------------------

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


def weather_row(workspace_id: str, **overrides):
    """A valid nowcast row. Overrides let a test violate exactly one rule."""

    row = {
        "workspace_id": workspace_id,
        "zone_id": "BGLR-1",
        "provider": "open-meteo",
        "provider_version": "v1",
        "event_time": NOW - timedelta(minutes=10),
        "issued_at": NOW - timedelta(minutes=5),
        "valid_at": NOW,
        "retrieved_at": NOW,
        "information_available_at": NOW,
        "evidence_class": "PROVIDER_ESTIMATED",
        "dataset_version": "2026.08.18",
        "temperature": 27.5,
        "precipitation": 0.0,
        "observed_at": NOW,
    }
    row.update(overrides)
    return row


def insert_weather(cur, row) -> None:
    columns = ", ".join(row)
    placeholders = ", ".join(["%s"] * len(row))
    cur.execute(
        f"INSERT INTO weather_observations ({columns}) VALUES ({placeholders})",
        tuple(row.values()),
    )


# ---------------------------------------------------------------------------
# Migration shape
# ---------------------------------------------------------------------------


def test_temporal_contract_columns_exist(conn):
    expected = {
        "workspace_id",
        "zone_id",
        "provider",
        "provider_version",
        "event_time",
        "issued_at",
        "valid_at",
        "retrieved_at",
        "information_available_at",
        "evidence_class",
        "dataset_version",
        "run_id",
    }
    with conn.cursor() as cur:
        for table in ("weather_observations", "traffic_observations"):
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table,),
            )
            present = {r[0] for r in cur.fetchall()}
            assert expected <= present, f"{table} is missing {sorted(expected - present)}"


def test_point_in_time_and_identity_indexes_exist(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename IN ('weather_observations', 'traffic_observations')"
        )
        names = {r[0] for r in cur.fetchall()}
    assert {
        "weather_observation_identity",
        "traffic_observation_identity",
        "weather_point_in_time",
        "traffic_point_in_time",
    } <= names


def test_no_constraint_forbids_forecasts(conn):
    """Guard the semantics: nothing may tie valid_at back to availability."""

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
            WHERE conrelid IN ('weather_observations'::regclass,
                               'traffic_observations'::regclass)
              AND contype = 'c'
            """
        )
        definitions = cur.fetchall()

    for name, definition in definitions:
        normalized = definition.replace(" ", "")
        assert "valid_at<=information_available_at" not in normalized, (
            f"{name} would reject every forecast: {definition}"
        )
        assert "information_available_at>=valid_at" not in normalized, (
            f"{name} would reject every forecast: {definition}"
        )


# ---------------------------------------------------------------------------
# Temporal invariants
# ---------------------------------------------------------------------------


def test_valid_future_forecast_is_accepted(fx):
    """The headline case: issued now, valid six hours from now.

    valid_at is far in the future relative to information_available_at. This is
    a legitimate forecast and must be storable, otherwise the platform cannot
    record the thing it exists to produce.
    """

    insert_weather(
        fx.cur,
        weather_row(
            fx.workspace_a,
            event_time=NOW - timedelta(hours=1),
            issued_at=NOW,
            information_available_at=NOW,
            retrieved_at=NOW,
            valid_at=NOW + timedelta(hours=6),
        ),
    )
    fx.cur.execute(
        "SELECT valid_at > information_available_at FROM weather_observations WHERE workspace_id = %s",
        (fx.workspace_a,),
    )
    assert fx.cur.fetchone()[0] is True


def test_nowcast_is_accepted(fx):
    insert_weather(fx.cur, weather_row(fx.workspace_a))
    fx.cur.execute("SELECT count(*) FROM weather_observations WHERE workspace_id = %s", (fx.workspace_a,))
    assert fx.cur.fetchone()[0] == 1


@pytest.mark.parametrize(
    ("label", "overrides"),
    [
        (
            "known before the event happened",
            {"event_time": NOW, "information_available_at": NOW - timedelta(hours=1)},
        ),
        (
            "known before the provider issued it",
            {"issued_at": NOW, "information_available_at": NOW - timedelta(minutes=1)},
        ),
        (
            "known before it was retrieved",
            {"retrieved_at": NOW - timedelta(hours=1), "information_available_at": NOW},
        ),
        (
            "retrieved before it was issued",
            {"issued_at": NOW, "retrieved_at": NOW - timedelta(minutes=30)},
        ),
    ],
)
def test_leaking_row_is_rejected(fx, label, overrides):
    """Every row that claims knowledge it could not have had must be refused."""

    base = {"event_time": NOW - timedelta(hours=2), "issued_at": NOW - timedelta(hours=1)}
    base.update(overrides)
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_weather(fx.cur, weather_row(fx.workspace_a, **base))


@pytest.mark.parametrize("evidence_class", ["TEST_ONLY", "STAGING_DO_NOT_USE"])
def test_non_authoritative_evidence_is_rejected(fx, evidence_class):
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_weather(fx.cur, weather_row(fx.workspace_a, evidence_class=evidence_class))


def test_authoritative_evidence_classes_are_accepted(fx):
    accepted = [
        "OBSERVED",
        "PUBLIC_OFFICIAL",
        "PUBLIC_GEOGRAPHIC",
        "PROVIDER_ESTIMATED",
        "DERIVED",
        "SIMULATED",
        "ASSUMPTION",
    ]
    for index, evidence_class in enumerate(accepted):
        insert_weather(
            fx.cur,
            weather_row(fx.workspace_a, evidence_class=evidence_class, zone_id=f"BGLR-{index}"),
        )
    fx.cur.execute("SELECT count(*) FROM weather_observations WHERE workspace_id = %s", (fx.workspace_a,))
    assert fx.cur.fetchone()[0] == len(accepted)


def test_provider_rerun_is_idempotent(fx):
    """A repeated acquisition of the same payload must not duplicate a row."""

    row = weather_row(fx.workspace_a)
    insert_weather(fx.cur, row)

    # Same observation, fetched again an hour later.
    repeat = weather_row(
        fx.workspace_a,
        retrieved_at=NOW + timedelta(hours=1),
        information_available_at=NOW + timedelta(hours=1),
    )
    columns = ", ".join(repeat)
    placeholders = ", ".join(["%s"] * len(repeat))
    fx.cur.execute(
        f"INSERT INTO weather_observations ({columns}) VALUES ({placeholders}) "
        "ON CONFLICT (workspace_id, provider, zone_id, event_time, valid_at, issued_at) "
        "DO NOTHING",
        tuple(repeat.values()),
    )

    fx.cur.execute("SELECT count(*) FROM weather_observations WHERE workspace_id = %s", (fx.workspace_a,))
    assert fx.cur.fetchone()[0] == 1


def test_duplicate_identity_without_upsert_raises(fx):
    insert_weather(fx.cur, weather_row(fx.workspace_a))
    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_weather(fx.cur, weather_row(fx.workspace_a))


def test_point_in_time_query_hides_later_information(fx):
    """A decision at D must not see a row that only became known after D."""

    insert_weather(
        fx.cur,
        weather_row(
            fx.workspace_a,
            zone_id="Z",
            event_time=NOW - timedelta(hours=3),
            issued_at=NOW - timedelta(hours=2),
            retrieved_at=NOW - timedelta(hours=2),
            information_available_at=NOW - timedelta(hours=2),
            valid_at=NOW - timedelta(hours=2),
        ),
    )
    insert_weather(
        fx.cur,
        weather_row(
            fx.workspace_a,
            zone_id="Z",
            issued_at=NOW + timedelta(hours=1),
            information_available_at=NOW + timedelta(hours=1),
            retrieved_at=NOW + timedelta(hours=1),
            valid_at=NOW + timedelta(hours=2),
        ),
    )
    fx.cur.execute(
        "SELECT count(*) FROM weather_observations "
        "WHERE workspace_id = %s AND zone_id = 'Z' AND information_available_at <= %s",
        (fx.workspace_a, NOW),
    )
    assert fx.cur.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Tenancy isolation
# ---------------------------------------------------------------------------


def test_member_reads_own_workspace(fx):
    insert_weather(fx.cur, weather_row(fx.workspace_a))
    fx.as_user("a_researcher")
    fx.cur.execute("SELECT count(*) FROM weather_observations")
    assert fx.cur.fetchone()[0] == 1


def test_member_cannot_read_other_workspace(fx):
    insert_weather(fx.cur, weather_row(fx.workspace_b))
    fx.as_user("a_researcher")

    # Unfiltered: workspace B's row must simply not exist for this session.
    fx.cur.execute("SELECT count(*) FROM weather_observations")
    assert fx.cur.fetchone()[0] == 0

    # And naming workspace B explicitly must not reveal it either.
    fx.cur.execute("SELECT count(*) FROM weather_observations WHERE workspace_id = %s", (fx.workspace_b,))
    assert fx.cur.fetchone()[0] == 0


def test_workspace_forgery_reveals_nothing(fx):
    """Naming another workspace id is not a capability."""

    insert_weather(fx.cur, weather_row(fx.workspace_b))
    fx.as_user("a_owner")
    fx.cur.execute("SELECT count(*) FROM workspaces WHERE id = %s", (fx.workspace_b,))
    assert fx.cur.fetchone()[0] == 0
    fx.cur.execute("SELECT public.zonepilot_current_workspace_role(%s)", (fx.workspace_b,))
    assert fx.cur.fetchone()[0] is None


def test_outsider_sees_nothing(fx):
    insert_weather(fx.cur, weather_row(fx.workspace_a))
    fx.as_user("outsider")
    fx.cur.execute("SELECT count(*) FROM weather_observations")
    assert fx.cur.fetchone()[0] == 0
    fx.cur.execute("SELECT count(*) FROM workspaces")
    assert fx.cur.fetchone()[0] == 0


def test_member_sees_only_own_workspace_in_directory(fx):
    fx.as_user("a_viewer")
    fx.cur.execute("SELECT id FROM workspaces")
    assert [r[0] for r in fx.cur.fetchall()] == [uuid.UUID(fx.workspace_a)]


# ---------------------------------------------------------------------------
# Role separation
# ---------------------------------------------------------------------------


def test_viewer_cannot_write_evidence(fx):
    fx.as_user("a_viewer")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        insert_weather(fx.cur, weather_row(fx.workspace_a))


def test_researcher_cannot_write_evidence(fx):
    fx.as_user("a_researcher")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        insert_weather(fx.cur, weather_row(fx.workspace_a))


def test_owner_cannot_write_evidence_directly(fx):
    """Evidence is append-only for sessions; even OWNER may not hand-write it."""

    fx.as_user("a_owner")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        insert_weather(fx.cur, weather_row(fx.workspace_a))


def test_viewer_cannot_administer_membership(fx):
    fx.as_user("a_viewer")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        fx.cur.execute(
            "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (%s, %s, %s)",
            (fx.workspace_a, fx.users["outsider"], "VIEWER"),
        )


def test_researcher_cannot_administer_membership(fx):
    fx.as_user("a_researcher")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        fx.cur.execute(
            "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (%s, %s, %s)",
            (fx.workspace_a, fx.users["outsider"], "VIEWER"),
        )


def test_researcher_cannot_rename_workspace(fx):
    fx.as_user("a_researcher")
    fx.cur.execute("UPDATE workspaces SET name = 'seized' WHERE id = %s", (fx.workspace_a,))
    assert fx.cur.rowcount == 0


def test_admin_may_administer_membership(fx):
    fx.as_user("a_admin")
    fx.cur.execute(
        "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (%s, %s, %s)",
        (fx.workspace_a, fx.users["outsider"], "VIEWER"),
    )
    assert fx.cur.rowcount == 1


def test_admin_cannot_administer_other_workspace(fx):
    fx.as_user("a_admin")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        fx.cur.execute(
            "INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (%s, %s, %s)",
            (fx.workspace_b, fx.users["outsider"], "OWNER"),
        )


def test_researcher_cannot_read_member_directory(fx):
    """A non-admin member sees its own row and nobody else's."""

    fx.as_user("a_researcher")
    fx.cur.execute("SELECT user_id FROM workspace_members")
    visible = {str(r[0]) for r in fx.cur.fetchall()}
    assert visible == {fx.users["a_researcher"]}


def test_admin_reads_member_directory(fx):
    fx.as_user("a_admin")
    fx.cur.execute("SELECT count(*) FROM workspace_members WHERE workspace_id = %s", (fx.workspace_a,))
    assert fx.cur.fetchone()[0] == 6


# ---------------------------------------------------------------------------
# COLLECTOR is a scoped, write-only acquisition identity
# ---------------------------------------------------------------------------


def test_collector_may_append_to_own_workspace(fx):
    fx.as_user("a_collector")
    insert_weather(fx.cur, weather_row(fx.workspace_a))
    assert fx.cur.rowcount == 1


def test_collector_cannot_append_to_other_workspace(fx):
    fx.as_user("a_collector")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        insert_weather(fx.cur, weather_row(fx.workspace_b))


def test_collector_cannot_read_the_corpus(fx):
    insert_weather(fx.cur, weather_row(fx.workspace_a))
    fx.as_user("a_collector")
    fx.cur.execute("SELECT count(*) FROM weather_observations")
    assert fx.cur.fetchone()[0] == 0


def test_collector_cannot_read_member_directory(fx):
    fx.as_user("a_collector")
    fx.cur.execute("SELECT user_id FROM workspace_members")
    visible = {str(r[0]) for r in fx.cur.fetchall()}
    assert visible == {fx.users["a_collector"]}


def test_collector_still_cannot_write_a_leaking_row(fx):
    """Tenancy does not exempt the acquisition identity from temporal rules."""

    fx.as_user("a_collector")
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_weather(
            fx.cur,
            weather_row(
                fx.workspace_a,
                issued_at=NOW,
                information_available_at=NOW - timedelta(hours=1),
            ),
        )


def test_collector_still_cannot_write_test_only_evidence(fx):
    fx.as_user("a_collector")
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_weather(fx.cur, weather_row(fx.workspace_a, evidence_class="TEST_ONLY"))


# ---------------------------------------------------------------------------
# The recursion class 00003_fix_rls_recursion.sql had to repair once
# ---------------------------------------------------------------------------


def test_membership_policies_do_not_recurse(fx):
    """The membership policy calls a function that reads the same table.

    If that function were not SECURITY DEFINER the policy would re-enter itself
    and Postgres would raise "infinite recursion detected in policy". Selecting
    under an authenticated session is the whole assertion.
    """

    fx.as_user("a_owner")
    fx.cur.execute("SELECT count(*) FROM workspace_members")
    assert fx.cur.fetchone()[0] == 6
    fx.cur.execute("SELECT count(*) FROM workspaces")
    assert fx.cur.fetchone()[0] == 1


def test_membership_function_cannot_enumerate_other_users(fx):
    """The resolver takes no user argument, so it cannot be aimed elsewhere."""

    with fx.cur.connection.cursor() as probe:
        probe.execute(
            """
            SELECT count(*) FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public'
              AND p.proname LIKE 'zonepilot_current%'
              AND pg_get_function_identity_arguments(p.oid) LIKE '%user%'
            """
        )
        assert probe.fetchone()[0] == 0
