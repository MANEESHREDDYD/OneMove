"""F-023: the rate limiter is shared across API instances and bounded in storage.

These tests need no database. The double below does not record calls and replay
canned answers -- it INTERPRETS the SQL the limiter emits: it parses the conflict
target, checks the update is an increment of the stored value rather than an
assignment of a value the application computed, and then actually applies the
upsert to an in-memory table keyed by the four bucket dimensions.

That matters because the defects being fixed are invisible to a recording mock.
A limiter that dropped a dimension from the conflict target, or that read a count
and wrote back count+1 in two statements, would satisfy any assertion of the form
"execute was called once with some SQL". Here it fails: the interpreter refuses
statements that are not the single atomic upsert, and the shared table makes
over-admission observable as a wrong number.
"""

from __future__ import annotations

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api.core.middleware import RequestIdMiddleware
from services.api.core.ratelimit import (
    ACTIVE_OPTIMIZATION_JOBS_SQL,
    PRUNE_SQL,
    DistributedRateLimiter,
    EndpointClass,
    PostgresRateLimitStore,
    RateLimitKey,
    StoreUnavailable,
    build_increment_sql,
    classify_endpoint,
    network_principal,
    principal_dimensions,
    rate_limit_metrics,
    unverified_claims,
)

# ---------------------------------------------------------------------------
# The interpreting double
# ---------------------------------------------------------------------------

_CONFLICT_TARGET = re.compile(r"ON CONFLICT\s*\(([^)]*)\)", re.IGNORECASE)
_DO_UPDATE = re.compile(r"DO UPDATE SET\s+request_count\s*=\s*(.+?)\s+RETURNING", re.IGNORECASE | re.DOTALL)
_RETURNING = re.compile(r"RETURNING\s+(.+)$", re.IGNORECASE | re.DOTALL)

REQUIRED_DIMENSIONS = ("workspace_id", "user_id", "endpoint_class", "window_start")

# The documented per-row parameter order in ratelimit.py. A reordering here is a
# mis-keyed bucket in production, so it is pinned rather than inferred.
PARAMS_PER_ROW = 6


class SqlContractError(BaseException):
    """The emitted SQL is not the atomic upsert this design depends on.

    Deliberately a BaseException. PostgresRateLimitStore turns any Exception into
    StoreUnavailable -- correct in production, but here it would disguise "the
    limiter emitted the wrong SQL" as "the database was down" and let a
    regression pass as a handled outage. This has to escape that handler.
    """


def _returning_terms(clause: str) -> list[str]:
    """Reduce a RETURNING list to the column each term actually yields.

    A term is only credited as the underlying column when it IS that column.
    `request_count` counts; `0 AS request_count` does not, because the value it
    returns did not come from the row. Aliases on genuine expressions (the
    retry_after arithmetic) are credited under their alias.
    """
    terms: list[str] = []
    depth = 0
    current = ""
    for char in clause:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            terms.append(current)
            current = ""
        else:
            current += char
    terms.append(current)

    names: list[str] = []
    for raw in terms:
        term = raw.strip()
        if not term:
            continue
        alias_split = re.split(r"\s+AS\s+", term, flags=re.IGNORECASE)
        if len(alias_split) == 2:
            expression, alias = alias_split[0].strip(), alias_split[1].strip()
            # An alias over a constant is not the column it is named after.
            names.append(alias if not re.fullmatch(r"[-+]?\d+", expression) else f"<constant:{alias}>")
        else:
            names.append(term.split(".")[-1])
    return names


class FakeDatabase:
    """An in-memory stand-in for the rate_limit_buckets table.

    One instance represents ONE database. Handing it to two limiters is what
    models two API instances sharing a store.
    """

    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now
        # (workspace_id, user_id, endpoint_class, window_start) -> [count, expires_at]
        self.rows: dict[tuple[str, str, str, float], list[float]] = {}
        self.statements: list[str] = []
        self.optimization_jobs: dict[str, int] = {}
        self.available = True
        self.upsert_calls = 0

    # -- helpers the tests use
    def advance(self, seconds: float) -> None:
        self.now += seconds

    def window_start(self, window_seconds: int) -> float:
        """Mirror of public.rate_limit_window_start: floor(epoch/w)*w."""
        return (self.now // window_seconds) * window_seconds

    def count_for(self, workspace_id: str, user_id: str, endpoint_class: str) -> int:
        return sum(
            int(value[0])
            for key, value in self.rows.items()
            if key[0] == workspace_id and key[1] == user_id and key[2] == endpoint_class
        )

    # -- statement dispatch
    def execute(self, sql: str, params) -> list[tuple]:
        if not self.available:
            raise RuntimeError("connection refused: rate limit store is down")
        self.statements.append(sql)
        normalised = " ".join(sql.split())
        if normalised.upper().startswith("INSERT INTO PUBLIC.RATE_LIMIT_BUCKETS"):
            return self._upsert(normalised, list(params or []))
        if normalised.startswith("SELECT public.prune_rate_limit_buckets"):
            return self._prune(list(params or []))
        if normalised == " ".join(ACTIVE_OPTIMIZATION_JOBS_SQL.split()):
            return [(self.optimization_jobs.get(params[0], 0),)]
        # Anything else is a regression. A read-then-write limiter would land
        # here with a bare SELECT of request_count, or with a separate UPDATE.
        raise SqlContractError(
            "the limiter must enforce with one atomic upsert; refusing unexpected statement: " + normalised[:160]
        )

    # -- the interpreter
    def _upsert(self, sql: str, params: list) -> list[tuple]:
        self.upsert_calls += 1

        # 1. It must be ONE statement. Two statements is a read-then-write race.
        if ";" in sql.rstrip(";"):
            raise SqlContractError("enforcement must be a single statement, found a statement separator")

        # 2. The conflict target must carry every bucket dimension. Dropping one
        #    silently merges distinct callers into one bucket (or splits one
        #    caller across many), which is a quota bug in either direction.
        target = _CONFLICT_TARGET.search(sql)
        if not target:
            raise SqlContractError("no ON CONFLICT target: this is an INSERT, not an upsert")
        columns = tuple(c.strip() for c in target.group(1).split(","))
        missing = [d for d in REQUIRED_DIMENSIONS if d not in columns]
        if missing:
            raise SqlContractError(f"conflict target is missing bucket dimensions: {missing}")

        # 3. The update must derive the new count FROM THE STORED ROW. An
        #    assignment of a plain parameter would mean the application read the
        #    count, added one in Python, and wrote it back -- the exact race that
        #    lets two instances both admit the same last slot.
        update = _DO_UPDATE.search(sql)
        if not update:
            raise SqlContractError("no DO UPDATE SET request_count: the upsert does not increment")
        expression = update.group(1)
        if "b.request_count" not in expression:
            raise SqlContractError(f"increment must read the stored count, got: {expression}")
        if "%s" in expression:
            raise SqlContractError(f"increment must not take the count from a parameter, got: {expression}")

        # 4. It must hand the new count back, or the caller has to read again.
        returning = _RETURNING.search(sql)
        if not returning:
            raise SqlContractError("the upsert must RETURN the post-increment count")
        returning_terms = _returning_terms(returning.group(1))
        if "request_count" not in returning_terms:
            # `0 AS request_count` or any other computed stand-in is not the
            # stored count, and would let the limiter decide on a fiction.
            raise SqlContractError(f"RETURNING must hand back the stored request_count column, got: {returning_terms}")
        if "retry_after_seconds" not in returning_terms:
            raise SqlContractError("RETURNING must hand back a retry_after, or the 429 cannot say when")

        # 5. Parameter arity and order.
        row_count = sql.count("make_interval")
        if row_count < 1:
            raise SqlContractError("no VALUES rows found")
        if len(params) != row_count * PARAMS_PER_ROW:
            raise SqlContractError(
                f"expected {row_count * PARAMS_PER_ROW} parameters for {row_count} buckets, got {len(params)}"
            )

        out: list[tuple] = []
        for index in range(row_count):
            chunk = params[index * PARAMS_PER_ROW : (index + 1) * PARAMS_PER_ROW]
            workspace_id, user_id, endpoint_class, w_start, w_expiry_base, w_expiry_offset = chunk
            for name, value in (
                ("workspace_id", workspace_id),
                ("user_id", user_id),
                ("endpoint_class", endpoint_class),
            ):
                if not isinstance(value, str) or not value:
                    raise SqlContractError(f"parameter {index}:{name} is not a non-empty string: {value!r}")
            if not (w_start == w_expiry_base == w_expiry_offset):
                raise SqlContractError(
                    "the three window parameters in a row must be the same width; "
                    f"got {w_start}, {w_expiry_base}, {w_expiry_offset}"
                )
            window_seconds = int(w_start)

            start = self.window_start(window_seconds)
            key = (workspace_id, user_id, endpoint_class, start)
            if key in self.rows:
                self.rows[key][0] += 1
            else:
                self.rows[key] = [1.0, start + window_seconds]
            count, expires_at = self.rows[key]
            retry_after = max(1, int(expires_at - self.now) + 1)
            available = {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "endpoint_class": endpoint_class,
                "request_count": int(count),
                "retry_after_seconds": retry_after,
            }
            out.append(tuple(available[term] for term in returning_terms))
        return out

    def _prune(self, params: list) -> list[tuple]:
        batch = int(params[0])
        doomed = [key for key, value in self.rows.items() if value[1] <= self.now][:batch]
        for key in doomed:
            del self.rows[key]
        return [(len(doomed),)]


class FakeCursor:
    def __init__(self, database: FakeDatabase) -> None:
        self._db = database
        self._rows: list[tuple] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *exc_info) -> bool:
        return False

    def execute(self, sql, params=None) -> None:
        self._rows = self._db.execute(sql, params)

    def fetchall(self) -> list[tuple]:
        return self._rows


class FakeConnection:
    def __init__(self, database: FakeDatabase) -> None:
        self._db = database

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *exc_info) -> bool:
        return False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self._db)


def FakeStore(database: FakeDatabase) -> PostgresRateLimitStore:
    """The REAL store, talking to the interpreting database.

    This is deliberately not a reimplementation of the store. Driving
    PostgresRateLimitStore through a connection double puts its own parameter
    marshalling and result mapping under test -- the parts where a swapped
    argument silently mis-keys every bucket, and where a changed RETURNING list
    silently feeds the limiter the wrong number.
    """
    return PostgresRateLimitStore(connection_factory=lambda: FakeConnection(database))


@pytest.fixture
def database() -> FakeDatabase:
    return FakeDatabase()


@pytest.fixture
def limiter(database: FakeDatabase) -> DistributedRateLimiter:
    return DistributedRateLimiter(store=FakeStore(database))


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in list(os_environ_names()):
        monkeypatch.delenv(name, raising=False)
    # One request per window makes the boundary unambiguous in most tests.
    monkeypatch.setenv("ZONEPILOT_RATE_LIMIT_NETWORK_MULTIPLIER", "1")


def os_environ_names():
    import os

    return [n for n in os.environ if n.startswith("ZONEPILOT_")]


# ---------------------------------------------------------------------------
# 1. The statement itself
# ---------------------------------------------------------------------------


def test_enforcement_is_one_atomic_upsert_that_returns_the_new_count() -> None:
    sql = " ".join(build_increment_sql(1).split())

    assert sql.upper().startswith("INSERT INTO PUBLIC.RATE_LIMIT_BUCKETS")
    assert "ON CONFLICT (workspace_id, user_id, endpoint_class, window_start)" in sql
    assert "DO UPDATE SET request_count = LEAST(b.request_count + 1" in sql
    assert "RETURNING" in sql
    # One statement, so there is no window between deciding and recording.
    assert ";" not in sql


def test_conflict_target_names_all_four_dimensions() -> None:
    target = _CONFLICT_TARGET.search(build_increment_sql(1))
    assert target is not None
    columns = [c.strip() for c in target.group(1).split(",")]
    assert columns == list(REQUIRED_DIMENSIONS)


def test_every_bucket_for_a_request_travels_in_one_statement() -> None:
    # Multi-row upsert: the network bucket and the identity bucket are charged
    # by the same statement, so they cannot disagree about which window it is.
    assert build_increment_sql(3).count("make_interval") == 3


def test_the_double_rejects_a_dropped_conflict_dimension(database: FakeDatabase) -> None:
    """Proof the interpreter has teeth: mutate the SQL, watch the test fail."""
    good = build_increment_sql(1)
    params = ["ws", "user", "READ", 60, 60, 60]
    database.execute(good, params)  # baseline: accepted

    broken = good.replace(
        "ON CONFLICT (workspace_id, user_id, endpoint_class, window_start)",
        "ON CONFLICT (user_id, endpoint_class, window_start)",
    )
    with pytest.raises(SqlContractError, match="missing bucket dimensions"):
        database.execute(broken, params)


def test_the_double_rejects_a_read_then_write_regression(database: FakeDatabase) -> None:
    # An application-computed count is the read-then-write bug in disguise.
    regressed = build_increment_sql(1).replace(
        "DO UPDATE SET request_count = LEAST(b.request_count + 1, 2147483000)",
        "DO UPDATE SET request_count = %s",
    )
    with pytest.raises(SqlContractError):
        database.execute(regressed, ["ws", "user", "READ", 60, 60, 60])

    # And a genuine two-statement limiter never reaches the upsert branch at all.
    with pytest.raises(SqlContractError, match="one atomic upsert"):
        database.execute(
            "SELECT request_count FROM public.rate_limit_buckets WHERE user_id = %s",
            ["user"],
        )


def test_the_double_rejects_an_upsert_that_does_not_return_the_count(database: FakeDatabase) -> None:
    good = build_increment_sql(1)
    params = ["ws", "user", "READ", 60, 60, 60]

    # No RETURNING at all: the caller would have to read the count back.
    silent = good[: good.index("RETURNING")] + "RETURNING workspace_id"
    with pytest.raises(SqlContractError):
        database.execute(silent, params)

    # A constant dressed up as the count. This is the subtle one: the shape is
    # right, the column name is right, and the value is a fiction.
    faked = good.replace(
        "RETURNING workspace_id, user_id, endpoint_class, request_count,",
        "RETURNING workspace_id, user_id, endpoint_class, 0 AS request_count,",
    )
    with pytest.raises(SqlContractError, match="stored request_count column"):
        database.execute(faked, params)


def test_parameter_order_is_workspace_user_class_then_window(database: FakeDatabase) -> None:
    """The production store must bind parameters in the documented order.

    Driven through PostgresRateLimitStore rather than hand-built, because the
    bug this guards against lives in that marshalling: swapping two arguments
    mis-keys every bucket in a way that is perfectly self-consistent and
    therefore invisible to a quota count.
    """
    FakeStore(database).increment([RateLimitKey("ws-1", "user-1", EndpointClass.WRITE)], [60])

    (key,) = database.rows
    assert key[0] == "ws-1", "position 1 is workspace_id"
    assert key[1] == "user-1", "position 2 is user_id"
    assert key[2] == "WRITE", "position 3 is endpoint_class"
    assert key[3] == database.window_start(60), "position 4 is the window width"

    # And a swapped binding is rejected outright rather than mis-keyed.
    with pytest.raises(SqlContractError, match="is not a non-empty string"):
        database.execute(build_increment_sql(1), ["ws-1", "user-1", 60, "WRITE", 60, 60])


def test_the_store_maps_returned_rows_back_to_the_key_that_asked(database: FakeDatabase) -> None:
    """A swapped binding must not still produce a self-consistent answer."""
    counts = FakeStore(database).increment(
        [
            RateLimitKey("ws-1", "user-1", EndpointClass.READ),
            RateLimitKey("ws-2", "user-2", EndpointClass.READ),
        ],
        [60, 60],
    )

    assert counts[("ws-1", "user-1", "READ")][0] == 1
    assert counts[("ws-2", "user-2", "READ")][0] == 1
    assert ("user-1", "ws-1", "READ") not in counts, "workspace and user must not be transposed"


# ---------------------------------------------------------------------------
# 2. The headline property: instances share one quota
# ---------------------------------------------------------------------------


def test_two_limiter_instances_sharing_one_store_observe_one_quota(database, monkeypatch) -> None:
    """The regression test for the original defect.

    Two DistributedRateLimiter objects are two API processes. Before F-023 each
    kept its own dict and each granted the full quota; a limit of 4 admitted 8.
    """
    monkeypatch.setenv("ZONEPILOT_AUTH_RATE_LIMIT_PER_MINUTE", "4")
    store = FakeStore(database)
    instances = [DistributedRateLimiter(store=store), DistributedRateLimiter(store=store)]

    admitted = 0
    for i in range(12):
        decision = instances[i % 2].check(  # round-robin, like a load balancer
            endpoint_class=EndpointClass.AUTH,
            workspace_id="ws-1",
            user_id="user-1",
            network_id="ip:aaa",
        )
        admitted += decision.allowed

    assert admitted == 4, "the shared quota was multiplied by the instance count"


def test_ten_instances_still_observe_one_quota(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "10")
    store = FakeStore(database)
    instances = [DistributedRateLimiter(store=store) for _ in range(10)]  # max_instance_count

    admitted = sum(
        instances[i % 10]
        .check(
            endpoint_class=EndpointClass.READ,
            workspace_id="ws-1",
            user_id="user-1",
            network_id="ip:aaa",
        )
        .allowed
        for i in range(200)
    )

    assert admitted == 10


# ---------------------------------------------------------------------------
# 3. The key really is four-dimensional
# ---------------------------------------------------------------------------


def test_each_dimension_separates_buckets(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("ZONEPILOT_WRITE_RATE_LIMIT_PER_MINUTE", "1")
    # Hold the source address constant and give it plenty of headroom, so that
    # what separates these buckets is provably the identity dimensions and not
    # the network bucket doing the work.
    monkeypatch.setenv("ZONEPILOT_RATE_LIMIT_NETWORK_MULTIPLIER", "100")
    store = FakeStore(database)

    def spend(workspace_id: str, user_id: str, endpoint_class: EndpointClass) -> bool:
        return (
            DistributedRateLimiter(store=store, clock=lambda: database.now)
            .check(
                endpoint_class=endpoint_class,
                workspace_id=workspace_id,
                user_id=user_id,
                network_id="ip:constant",
            )
            .allowed
        )

    assert spend("ws-1", "user-1", EndpointClass.READ) is True
    assert spend("ws-1", "user-1", EndpointClass.READ) is False, "same key must share a bucket"

    # workspace_id
    assert spend("ws-2", "user-1", EndpointClass.READ) is True
    # user_id
    assert spend("ws-1", "user-2", EndpointClass.READ) is True
    # endpoint_class
    assert spend("ws-1", "user-1", EndpointClass.WRITE) is True

    # time_bucket: the fourth dimension. A new window is a new row.
    database.advance(61)
    assert spend("ws-1", "user-1", EndpointClass.READ) is True


def test_window_start_is_derived_from_the_database_clock(database, monkeypatch) -> None:
    """Ten instances with skewed clocks must still agree on the bucket."""
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "5")
    store = FakeStore(database)

    database.now = 1_000_030.0  # mid-window
    for _ in range(5):
        DistributedRateLimiter(store=store).check(
            endpoint_class=EndpointClass.READ, workspace_id="ws", user_id="u", network_id="ip:a"
        )
    starts = {key[3] for key in database.rows}
    assert len(starts) == 1, "one window, one row -- no per-instance window offsets"

    denied = DistributedRateLimiter(store=store).check(
        endpoint_class=EndpointClass.READ, workspace_id="ws", user_id="u", network_id="ip:a"
    )
    assert denied.allowed is False


# ---------------------------------------------------------------------------
# 4. Bounded storage
# ---------------------------------------------------------------------------


def test_expired_buckets_are_pruned_so_the_table_cannot_grow_without_limit(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "1000")
    monkeypatch.setenv("ZONEPILOT_RATE_LIMIT_PRUNE_INTERVAL_SECONDS", "1")
    limiter = DistributedRateLimiter(store=FakeStore(database), clock=lambda: database.now)

    peak = 0
    for window in range(50):
        for caller in range(20):
            limiter.check(
                endpoint_class=EndpointClass.READ,
                workspace_id="ws",
                user_id=f"user-{window}-{caller}",  # a fresh identity every time
                network_id=f"ip:{window}-{caller}",
            )
        peak = max(peak, len(database.rows))
        database.advance(61)

    limiter.check(endpoint_class=EndpointClass.READ, workspace_id="ws", user_id="final", network_id="ip:final")

    # 1000 distinct identities were seen. Retention is bounded by the window, not
    # by how many callers have ever appeared: at most two windows are live.
    assert len(database.rows) <= 2 * 20 * 2 + 2
    assert peak <= 2 * 20 * 2 + 2, f"working set grew to {peak}"


def test_a_source_address_over_budget_stops_generating_rows(database, monkeypatch) -> None:
    """The row-growth bound for a hostile caller.

    A caller can put anything in a token claim, so the identity dimensions are
    caller-selectable and could otherwise mint one row per request. The network
    bucket is not selectable, and once it is exhausted the limiter stops issuing
    writes at all.
    """
    monkeypatch.setenv("ZONEPILOT_WRITE_RATE_LIMIT_PER_MINUTE", "3")
    limiter = DistributedRateLimiter(store=FakeStore(database))

    for attempt in range(500):
        limiter.check(
            endpoint_class=EndpointClass.WRITE,
            workspace_id=f"forged-ws-{attempt}",
            user_id=f"forged-user-{attempt}",  # a new identity on every request
            network_id="ip:attacker",
        )

    assert database.upsert_calls < 10, f"attacker drove {database.upsert_calls} writes"
    assert len(database.rows) < 10, f"attacker created {len(database.rows)} rows from one address"


def test_the_deny_cache_is_bounded(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_WRITE_RATE_LIMIT_PER_MINUTE", "1")
    limiter = DistributedRateLimiter(store=FakeStore(database))
    limiter._deny_cache.max_entries = 64

    for attempt in range(5000):
        for _ in range(3):
            limiter.check(
                endpoint_class=EndpointClass.WRITE,
                workspace_id="ws",
                user_id=f"u{attempt}",
                network_id=f"ip:{attempt}",
            )

    assert len(limiter._deny_cache._denied_until) <= 64


def test_the_deny_cache_does_not_leak_across_endpoint_classes(database, monkeypatch) -> None:
    """Regression: a long-window budget must not blanket-ban an address.

    The deny cache was first keyed on the source address alone. Exhausting the
    DAILY assistant budget then short-circuited that address on every other
    class -- plain reads included -- for the rest of the day, on the strength of
    a budget that never governed them.
    """
    monkeypatch.setenv("ZONEPILOT_ASSISTANT_RATE_LIMIT_PER_MINUTE", "100")
    monkeypatch.setenv("ZONEPILOT_ASSISTANT_RATE_LIMIT_PER_DAY", "1")
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "10")
    limiter = DistributedRateLimiter(store=FakeStore(database), clock=lambda: database.now)

    def ask(endpoint_class: EndpointClass) -> bool:
        return limiter.check(endpoint_class=endpoint_class, workspace_id="ws", user_id="u", network_id="ip:a").allowed

    assert ask(EndpointClass.ASSISTANT) is True
    assert ask(EndpointClass.ASSISTANT) is False, "the daily assistant budget is spent"

    # The same address must still be able to read.
    assert ask(EndpointClass.READ) is True
    assert ask(EndpointClass.READ) is True


def test_the_deny_cache_can_only_refuse_never_admit(database, monkeypatch) -> None:
    """It is per-process state, so it must be incapable of over-admitting."""
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "2")
    store = FakeStore(database)
    warm, cold = DistributedRateLimiter(store=store), DistributedRateLimiter(store=store)

    for _ in range(2):
        assert warm.check(endpoint_class=EndpointClass.READ, workspace_id="ws", user_id="u", network_id="ip:a").allowed

    # `cold` has an empty deny cache and has never seen this caller. It must
    # still refuse, because the authoritative count lives in the store.
    assert (
        cold.check(endpoint_class=EndpointClass.READ, workspace_id="ws", user_id="u", network_id="ip:a").allowed
        is False
    )


# ---------------------------------------------------------------------------
# 5. Extra quotas
# ---------------------------------------------------------------------------


def test_concurrent_optimization_jobs_are_capped_per_workspace(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_MAX_CONCURRENT_OPTIMIZATIONS_PER_WORKSPACE", "2")
    limiter = DistributedRateLimiter(store=FakeStore(database))

    database.optimization_jobs["ws-1"] = 1
    assert limiter.check_optimization_concurrency("ws-1").allowed is True

    database.optimization_jobs["ws-1"] = 2
    decision = limiter.check_optimization_concurrency("ws-1")
    assert decision.allowed is False
    assert decision.retry_after_seconds > 0
    assert "concurrent" in decision.reason

    # Another workspace is unaffected: the cap is per tenant, not global.
    assert limiter.check_optimization_concurrency("ws-2").allowed is True


def test_assistant_requests_are_charged_to_a_daily_budget_as_well(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_ASSISTANT_RATE_LIMIT_PER_MINUTE", "100")
    monkeypatch.setenv("ZONEPILOT_ASSISTANT_RATE_LIMIT_PER_DAY", "3")
    limiter = DistributedRateLimiter(store=FakeStore(database), clock=lambda: database.now)

    def ask() -> bool:
        return limiter.check(
            endpoint_class=EndpointClass.ASSISTANT,
            workspace_id="ws",
            user_id="u",
            network_id="ip:a",
        ).allowed

    assert [ask() for _ in range(3)] == [True, True, True]
    assert ask() is False, "the daily budget must bite even inside the per-minute allowance"

    # A new minute does not refill a daily budget.
    database.advance(120)
    assert ask() is False

    database.advance(86_400)
    assert ask() is True


def test_assistant_tool_invocations_have_their_own_budget(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_ASSISTANT_TOOL_LIMIT_PER_DAY", "5")
    limiter = DistributedRateLimiter(store=FakeStore(database))

    # One request can fan out into several tool calls; the fan-out is what costs.
    assert limiter.consume_assistant_tool_invocations(workspace_id="ws", user_id="u", count=4).allowed is True
    decision = limiter.consume_assistant_tool_invocations(workspace_id="ws", user_id="u", count=3)
    assert decision.allowed is False
    assert decision.endpoint_class is EndpointClass.ASSISTANT_TOOL_DAILY

    # And it is a separate budget from the assistant request budget.
    assert (
        limiter.check(endpoint_class=EndpointClass.ASSISTANT, workspace_id="ws", user_id="u", network_id="ip:a").allowed
        is True
    )


# ---------------------------------------------------------------------------
# 6. Store outage
# ---------------------------------------------------------------------------


def test_store_outage_never_silently_disables_the_limiter(database, monkeypatch) -> None:
    limiter = DistributedRateLimiter(store=FakeStore(database))
    before = rate_limit_metrics.snapshot().get(("store_unavailable", "READ"), 0)

    database.available = False
    decision = limiter.check(endpoint_class=EndpointClass.READ, workspace_id="ws", user_id="u", network_id="ip:a")

    assert decision.store_unavailable is True
    assert decision.allowed is False, "fail closed"
    after = rate_limit_metrics.snapshot().get(("store_unavailable", "READ"), 0)
    assert after > before, "an outage must be loud on /metrics"


def test_fail_open_is_opt_in_and_still_loud(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_RATE_LIMIT_FAIL_OPEN", "true")
    limiter = DistributedRateLimiter(store=FakeStore(database))
    before = rate_limit_metrics.snapshot().get(("fail_open_admitted", "READ"), 0)

    database.available = False
    decision = limiter.check(endpoint_class=EndpointClass.READ, workspace_id="ws", user_id="u", network_id="ip:a")

    assert decision.allowed is True
    assert decision.store_unavailable is True, "admitting unmetered must still be recorded as an outage"
    assert rate_limit_metrics.snapshot().get(("fail_open_admitted", "READ"), 0) > before


def test_a_bucket_the_store_forgot_to_answer_is_an_outage_not_an_allowance(database, monkeypatch) -> None:
    real = FakeStore(database)

    class ForgetfulStore(PostgresRateLimitStore):
        def increment(self, keys, windows):
            counts = real.increment(keys, windows)
            counts.pop(next(iter(counts)))  # drop one bucket's answer
            return counts

        def prune(self, batch_size):
            return real.prune(batch_size)

    limiter = DistributedRateLimiter(store=ForgetfulStore())
    decision = limiter.check(endpoint_class=EndpointClass.READ, workspace_id="ws", user_id="u", network_id="ip:a")

    assert decision.allowed is False
    assert decision.store_unavailable is True


def test_a_failed_prune_does_not_fail_the_request(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_RATE_LIMIT_PRUNE_INTERVAL_SECONDS", "1")

    real = FakeStore(database)

    class PruneFailsStore(PostgresRateLimitStore):
        def increment(self, keys, windows):
            return real.increment(keys, windows)

        def prune(self, batch_size):
            raise StoreUnavailable("prune blew up")

    limiter = DistributedRateLimiter(store=PruneFailsStore())
    assert (
        limiter.check(endpoint_class=EndpointClass.READ, workspace_id="ws", user_id="u", network_id="ip:a").allowed
        is True
    )


# ---------------------------------------------------------------------------
# 7. Classification and key material
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "method", "expected"),
    [
        ("/auth/login", "POST", EndpointClass.AUTH),
        ("/api/v1/admin/settings", "POST", EndpointClass.ADMIN),
        ("/api/v1/assistant/query", "POST", EndpointClass.ASSISTANT),
        ("/api/v1/optimizations", "POST", EndpointClass.OPTIMIZATION),
        ("/api/v1/scenarios", "POST", EndpointClass.OPTIMIZATION),
        ("/api/v1/zones", "GET", EndpointClass.READ),
        ("/api/v1/decisions", "POST", EndpointClass.WRITE),
    ],
)
def test_endpoint_classification(path, method, expected) -> None:
    assert classify_endpoint(path, method) is expected


@pytest.mark.parametrize(
    "path", ["/health", "/healthz", "/health/live", "/health/ready", "/ready", "/readyz", "/metrics"]
)
def test_probe_endpoints_are_never_rate_limited(path) -> None:
    # A limiter that can 429 or 503 a liveness probe turns a database blip into
    # an instance-kill loop and blocks the rollback that would fix it.
    assert classify_endpoint(path, "GET") is None


def test_forwarded_for_is_ignored_unless_the_operator_declares_proxy_hops(monkeypatch) -> None:
    spoofed = "203.0.113.9"
    monkeypatch.delenv("ZONEPILOT_TRUSTED_PROXY_HOPS", raising=False)
    assert network_principal("10.0.0.1", spoofed) == network_principal("10.0.0.1", "198.51.100.4")

    # Declared hops: the header becomes the key, so a real deployment behind a
    # load balancer limits real clients rather than the balancer.
    monkeypatch.setenv("ZONEPILOT_TRUSTED_PROXY_HOPS", "1")
    assert network_principal("10.0.0.1", spoofed) != network_principal("10.0.0.1", "198.51.100.4")


def test_unverified_claims_are_used_for_keying_only() -> None:
    import base64
    import json

    payload = base64.urlsafe_b64encode(json.dumps({"sub": "abc", "workspace_id": "ws"}).encode()).decode()
    token = f"header.{payload.rstrip('=')}.not-a-real-signature"

    claims = unverified_claims(f"Bearer {token}")
    assert claims["sub"] == "abc"

    # Garbage must degrade to "no claims", never raise: this runs on every
    # request, before authentication, and must not be a denial-of-service lever.
    assert unverified_claims("Bearer nonsense") == {}
    assert unverified_claims("Bearer a.b.c") == {}
    assert unverified_claims(None) == {}
    assert unverified_claims("Basic abc") == {}


def test_an_anonymous_request_uses_one_key_not_two(database) -> None:
    workspace_id, user_id, network_id = principal_dimensions(None, "10.0.0.5", None)
    assert user_id == network_id, "identity and network are the same caller when there is no token"

    DistributedRateLimiter(store=FakeStore(database)).check(
        endpoint_class=EndpointClass.READ,
        workspace_id=workspace_id,
        user_id=user_id,
        network_id=network_id,
    )
    # Emitting a duplicate key in one upsert is a Postgres cardinality error.
    assert len(database.rows) == 1


def test_a_caller_cannot_forge_a_network_bucket_key() -> None:
    _, user_id, network_id = principal_dimensions(
        _bearer({"sub": "ip:" + "0" * 24, "workspace_id": "ws"}), "10.0.0.5", None
    )
    assert user_id != network_id
    assert not user_id.startswith("ip:"), "a claim must never be able to impersonate a network bucket"


def _bearer(claims: dict) -> str:
    import base64
    import json

    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"Bearer header.{payload}.sig"


# ---------------------------------------------------------------------------
# 8. The wire contract
# ---------------------------------------------------------------------------


def _app(limiter_instance: DistributedRateLimiter, monkeypatch) -> TestClient:
    monkeypatch.setattr("services.api.core.middleware.limiter", limiter_instance)
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/api/v1/zones")
    def zones() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


def test_429_carries_retry_after_and_the_canonical_envelope(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "2")
    client = _app(DistributedRateLimiter(store=FakeStore(database)), monkeypatch)

    statuses = [client.get("/api/v1/zones").status_code for _ in range(4)]
    assert statuses == [200, 200, 429, 429], "the limiter must return 429, never 500"

    response = client.get("/api/v1/zones")
    assert response.status_code == 429

    # Retry-After, and it is a usable positive integer.
    assert int(response.headers["retry-after"]) >= 1

    # The canonical envelope from telemetry.py -- not a second error shape.
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert set(error) == {"code", "message", "retryable", "details", "request_id", "trace_id"}
    assert error["code"] == "RATE_LIMITED"
    assert error["retryable"] is True
    assert error["request_id"] not in ("", "unknown")
    assert error["trace_id"] not in ("", "unknown")
    assert error["request_id"] == response.headers["x-request-id"]
    assert error["trace_id"] == response.headers["x-trace-id"]
    assert error["details"]["endpoint_class"] == "READ"


def test_the_trace_id_survives_the_429_path(database, monkeypatch) -> None:
    """Regression: the old 429 branch called _record with the wrong arity.

    Every rate-limited request raised TypeError inside the middleware and was
    served as a 500 INTERNAL_ERROR with no Retry-After. The limiter's client
    contract was unreachable in production.
    """
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "1")
    client = _app(DistributedRateLimiter(store=FakeStore(database)), monkeypatch)
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"

    client.get("/api/v1/zones")
    response = client.get("/api/v1/zones", headers={"traceparent": traceparent})

    assert response.status_code == 429
    assert response.json()["error"]["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"


def test_store_outage_is_503_dependency_unavailable_not_a_silent_pass(database, monkeypatch) -> None:
    client = _app(DistributedRateLimiter(store=FakeStore(database)), monkeypatch)
    assert client.get("/api/v1/zones").status_code == 200

    database.available = False
    response = client.get("/api/v1/zones")

    assert response.status_code == 503, "an unreachable store must not mean unlimited traffic"
    body = response.json()["error"]
    assert body["code"] == "DEPENDENCY_UNAVAILABLE"
    assert body["retryable"] is True
    assert int(response.headers["retry-after"]) >= 1
    assert body["details"]["subsystem"] == "rate_limit_store"


def test_probes_still_answer_while_the_store_is_down(database, monkeypatch) -> None:
    client = _app(DistributedRateLimiter(store=FakeStore(database)), monkeypatch)
    database.available = False
    assert client.get("/health").status_code == 200


def test_disabling_the_limiter_is_explicit(database, monkeypatch) -> None:
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("ZONEPILOT_RATE_LIMIT_ENABLED", "false")
    client = _app(DistributedRateLimiter(store=FakeStore(database)), monkeypatch)

    assert [client.get("/api/v1/zones").status_code for _ in range(5)] == [200] * 5
    assert database.upsert_calls == 0


def test_the_limiter_cannot_admit_what_authorization_would_refuse(database, monkeypatch) -> None:
    """F-015/F-016 safety property.

    The limiter runs before authentication and authorization. It must be able to
    refuse a request early, and must never be able to let one through: it either
    returns a refusal itself or calls the next layer unchanged.
    """
    monkeypatch.setenv("ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE", "50")
    monkeypatch.setattr("services.api.core.middleware.limiter", DistributedRateLimiter(store=FakeStore(database)))

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    reached = []

    @app.get("/api/v1/zones")
    def zones():
        reached.append(1)
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="not a member")

    client = TestClient(app, raise_server_exceptions=False)

    # A forged token with an attractive-looking workspace claim changes only the
    # bucket key; the authorization outcome is untouched.
    response = client.get("/api/v1/zones", headers={"authorization": _bearer({"sub": "x", "workspace_id": "ws"})})
    assert response.status_code == 403
    assert reached == [1], "the limiter must not shadow the authorization decision"


def test_the_concurrency_cap_is_enforced_on_the_wire(database, monkeypatch) -> None:
    """Submitting an optimization while the workspace is saturated must 429."""
    monkeypatch.setenv("ZONEPILOT_MAX_CONCURRENT_OPTIMIZATIONS_PER_WORKSPACE", "2")
    monkeypatch.setenv("ZONEPILOT_EXPENSIVE_RATE_LIMIT_PER_MINUTE", "100")
    monkeypatch.setenv("ZONEPILOT_RATE_LIMIT_NETWORK_MULTIPLIER", "100")
    monkeypatch.setattr(
        "services.api.core.middleware.limiter",
        DistributedRateLimiter(store=FakeStore(database), clock=lambda: database.now),
    )

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    submitted = []

    @app.post("/api/v1/optimizations", status_code=202)
    def submit():
        submitted.append(1)
        return {"accepted": True}

    @app.get("/api/v1/optimizations")
    def listing():
        return {"jobs": []}

    client = TestClient(app, raise_server_exceptions=False)
    auth = {"authorization": _bearer({"sub": "u", "workspace_id": "ws-1"})}

    database.optimization_jobs["ws-1"] = 1
    assert client.post("/api/v1/optimizations", headers=auth).status_code == 202

    database.optimization_jobs["ws-1"] = 2
    response = client.post("/api/v1/optimizations", headers=auth)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert int(response.headers["retry-after"]) >= 1
    assert submitted == [1], "a capped submission must not reach the route"

    # Reading job status is not a submission and must stay available.
    assert client.get("/api/v1/optimizations", headers=auth).status_code == 200

    # And a different workspace is unaffected.
    other = {"authorization": _bearer({"sub": "u2", "workspace_id": "ws-2"})}
    assert client.post("/api/v1/optimizations", headers=other).status_code == 202


def test_limiter_metrics_are_exposed_on_the_registry() -> None:
    from services.api.core.telemetry import metrics

    rate_limit_metrics.increment("allowed", "READ")
    rendered = metrics.render_prometheus()

    assert "zonepilot_rate_limit_events_total" in rendered
    assert 'outcome="allowed"' in rendered
