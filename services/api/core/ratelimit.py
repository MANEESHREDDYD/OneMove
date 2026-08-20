"""F-023: distributed, bounded rate limiting backed by PostgreSQL.

WHAT WAS WRONG
    ``InMemoryRateLimiter`` in services/api/core/telemetry.py held its windows in
    a per-process dict and its own docstring called that out: "intentionally
    local to one API process". The API is deployed at max_instance_count = 10
    (infra/gcp/modules/cloud_run/main.tf:79), so every configured quota was
    multiplied by the number of live instances -- a 10/minute auth limit admitted
    100/minute in front of a load balancer. The same dict was never pruned, so a
    caller-supplied principal was enough to grow it without bound.

WHY POSTGRES
    Postgres is already a hard dependency of this service. A single
    ``INSERT ... ON CONFLICT DO UPDATE ... RETURNING`` locks the bucket row,
    increments it, and returns the post-increment count in one round trip. There
    is no window in which two instances can both read "9" and both admit. Redis
    would add a second stateful dependency and a second failure mode to buy a
    property this one already has.

THE TWO BUCKETS, AND WHY THERE ARE TWO
    This middleware runs BEFORE the authentication dependency, so it has no
    verified subject to key on. Keying purely on a token claim would be an
    evasion hole: claims are unverified at this point, so a caller could mint a
    fresh ``sub`` per request, get a fresh quota every time, and mint a fresh
    table row every time.

    So every request is charged to two buckets:

      * NETWORK  -- keyed on the source address. Not caller-selectable, so this
                    is the bucket that actually enforces anything, and the one
                    that bounds how many rows a hostile caller can create.
      * IDENTITY -- keyed on the claimed subject and workspace. Caller-selectable
                    and therefore only a fairness/attribution signal, never the
                    sole line of defence.

    When there is no token the two collapse to one key and one row is written.

    Claims are read here WITHOUT verification and are used ONLY to choose a
    counter key. No admission decision depends on them being genuine, because
    the network bucket is checked with the same statement.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import os
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "EndpointClass",
    "RateLimitDecision",
    "RateLimitKey",
    "RateLimitPolicy",
    "RateLimitStore",
    "PostgresRateLimitStore",
    "DistributedRateLimiter",
    "StoreUnavailable",
    "INCREMENT_SQL_TEMPLATE",
    "build_increment_sql",
    "classify_endpoint",
    "policy_for",
    "network_principal",
    "unverified_claims",
    "rate_limit_metrics",
    "limiter",
]

_LOG = logging.getLogger("zonepilot.ratelimit")

# Postgres INTEGER ceiling, minus headroom. A hostile caller that keeps sending
# after being denied still increments the bucket; the cap stops that from
# overflowing the column after ~2.1 billion requests in one window.
_COUNT_CEILING = 2_147_483_000


class EndpointClass(str, Enum):
    """The six endpoint classes, plus the long-window budget buckets.

    The value is written to ``rate_limit_buckets.endpoint_class`` and is
    constrained there by ``chk_rate_limit_endpoint_class``. Adding a member here
    without adding it to that CHECK will fail the write rather than silently
    stop limiting -- which is the intended direction to fail.
    """

    AUTH = "AUTH"
    READ = "READ"
    WRITE = "WRITE"
    OPTIMIZATION = "OPTIMIZATION"
    ASSISTANT = "ASSISTANT"
    ADMIN = "ADMIN"

    # Extra quotas. These are budgets rather than endpoint classes; they share
    # the table because they share the key shape.
    ASSISTANT_DAILY = "ASSISTANT_DAILY"
    ASSISTANT_TOOL_DAILY = "ASSISTANT_TOOL_DAILY"


@dataclass(frozen=True)
class RateLimitPolicy:
    """A budget: how many requests, over how wide a window.

    Window width is a total function of the endpoint class (see
    :data:`_DEFAULT_POLICIES`). That is what lets the bucket key stay four
    dimensions wide: because a class has exactly one width, two budgets can never
    land on the same ``(class, window_start)`` row with different meanings.
    """

    limit: int
    window_seconds: int

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("rate limit must admit at least one request")
        if self.window_seconds < 1:
            raise ValueError("rate limit window must be at least one second")


_MINUTE = 60
_DAY = 86_400

# (default limit, window width, env var that overrides the limit)
_DEFAULT_POLICIES: dict[EndpointClass, tuple[int, int, str]] = {
    EndpointClass.AUTH: (10, _MINUTE, "ZONEPILOT_AUTH_RATE_LIMIT_PER_MINUTE"),
    EndpointClass.READ: (120, _MINUTE, "ZONEPILOT_READ_RATE_LIMIT_PER_MINUTE"),
    EndpointClass.WRITE: (60, _MINUTE, "ZONEPILOT_WRITE_RATE_LIMIT_PER_MINUTE"),
    EndpointClass.OPTIMIZATION: (20, _MINUTE, "ZONEPILOT_EXPENSIVE_RATE_LIMIT_PER_MINUTE"),
    EndpointClass.ASSISTANT: (12, _MINUTE, "ZONEPILOT_ASSISTANT_RATE_LIMIT_PER_MINUTE"),
    EndpointClass.ADMIN: (30, _MINUTE, "ZONEPILOT_ADMIN_RATE_LIMIT_PER_MINUTE"),
    EndpointClass.ASSISTANT_DAILY: (500, _DAY, "ZONEPILOT_ASSISTANT_RATE_LIMIT_PER_DAY"),
    EndpointClass.ASSISTANT_TOOL_DAILY: (2000, _DAY, "ZONEPILOT_ASSISTANT_TOOL_LIMIT_PER_DAY"),
}


def _int_env(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except (AttributeError, ValueError):
        _LOG.warning("rate_limit_env_ignored", extra={"variable": name, "error_code": "INVALID_LIMIT"})
        return default
    if value < minimum:
        _LOG.warning("rate_limit_env_below_minimum", extra={"variable": name, "error_code": "INVALID_LIMIT"})
        return default
    return value


def _truthy_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def policy_for(endpoint_class: EndpointClass) -> RateLimitPolicy:
    """Resolve the live budget for a class, honouring env overrides."""
    default_limit, window_seconds, env_var = _DEFAULT_POLICIES[endpoint_class]
    return RateLimitPolicy(limit=_int_env(env_var, default_limit), window_seconds=window_seconds)


# --- endpoint classification -------------------------------------------------

# Never rate limited. Cloud Run's own liveness and readiness probes hit these; a
# limiter that can 429 or 503 a health check turns a database hiccup into an
# instance-kill loop and blocks the rollback that would fix it.
_UNLIMITED_PATHS = frozenset({"/health", "/healthz", "/health/live", "/health/ready", "/ready", "/readyz", "/metrics"})

_READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def classify_endpoint(path: str, method: str) -> EndpointClass | None:
    """Map a request onto its endpoint class, or None when it is never limited.

    Classification is on the raw path because this runs before routing, so the
    matched route template is not available yet.
    """
    normalised = path.rstrip("/") or "/"
    if normalised in _UNLIMITED_PATHS or path in _UNLIMITED_PATHS:
        return None

    lowered = normalised.lower()
    if "/auth" in lowered:
        return EndpointClass.AUTH
    if "/admin" in lowered:
        return EndpointClass.ADMIN
    if "/assistant" in lowered:
        return EndpointClass.ASSISTANT
    if any(segment in lowered for segment in ("/optimizations", "/optimizer", "/jobs", "/scenarios")):
        return EndpointClass.OPTIMIZATION
    if method.upper() in _READ_METHODS:
        return EndpointClass.READ
    return EndpointClass.WRITE


def companion_classes(endpoint_class: EndpointClass) -> tuple[EndpointClass, ...]:
    """Extra budgets charged alongside the primary class.

    An assistant call costs a per-minute burst slot AND a slice of the daily
    budget, because the thing being protected (model spend) is a daily quantity
    that a per-minute limit cannot express.
    """
    if endpoint_class is EndpointClass.ASSISTANT:
        return (EndpointClass.ASSISTANT_DAILY,)
    return ()


# --- key material ------------------------------------------------------------

NO_WORKSPACE = "-"
_NETWORK_PREFIX = "ip:"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def network_principal(client_host: str | None, forwarded_for: str | None = None) -> str:
    """Derive the non-forgeable network identity for a request.

    X-Forwarded-For is only consulted when the operator has declared how many
    proxy hops are in front of this service. Trusting it by default would hand a
    caller the ability to rewrite its own rate-limit key -- which is both a quota
    bypass and a way to mint unbounded table rows.

    On Cloud Run set ZONEPILOT_TRUSTED_PROXY_HOPS=1. With the default of 0 the
    socket peer is used, which behind a load balancer collapses traffic into one
    bucket: over-restrictive, but never permissive.
    """
    hops = _int_env("ZONEPILOT_TRUSTED_PROXY_HOPS", 0, minimum=0)
    if hops > 0 and forwarded_for:
        chain = [part.strip() for part in forwarded_for.split(",") if part.strip()]
        if len(chain) >= hops:
            # Count from the right: entries to the right were added by proxies we
            # trust, so the first one to their left is the furthest address we
            # can still believe.
            return _NETWORK_PREFIX + _digest(chain[-hops])
    return _NETWORK_PREFIX + _digest(client_host or "unknown")


def unverified_claims(authorization: str | None) -> dict[str, Any]:
    """Decode a bearer token's payload WITHOUT verifying its signature.

    Used only to pick a counter key. Nothing here is trusted: the network bucket
    is enforced with the same statement, so a forged claim buys a caller its own
    fairness bucket and no additional throughput. Never call this for anything
    that grants access -- signature verification lives in
    services/api/core/auth.py and is not duplicated here.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return {}
    token = authorization[7:].strip()
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    segment = parts[1]
    padding = "=" * (-len(segment) % 4)
    try:
        decoded = base64.urlsafe_b64decode(segment + padding)
        claims = json.loads(decoded)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return {}
    return claims if isinstance(claims, dict) else {}


def _bounded_identifier(value: Any, fallback: str) -> str:
    """Clamp a caller-supplied key fragment so it cannot bloat the index."""
    if not isinstance(value, str):
        return fallback
    stripped = value.strip()
    if not stripped:
        return fallback
    if len(stripped) > 64 or stripped.startswith(_NETWORK_PREFIX):
        # Over-long, or trying to impersonate a network bucket. Hash it: still a
        # stable per-caller key, but a fixed width we control.
        return _digest(stripped)
    return stripped


@dataclass(frozen=True)
class RateLimitKey:
    """The four bucket dimensions. Window start is derived in the database."""

    workspace_id: str
    user_id: str
    endpoint_class: EndpointClass

    @property
    def scope(self) -> str:
        return "network" if self.user_id.startswith(_NETWORK_PREFIX) else "identity"


@dataclass
class RateLimitDecision:
    allowed: bool
    endpoint_class: EndpointClass
    limit: int = 0
    remaining: int = 0
    retry_after_seconds: int = 1
    scope: str = "identity"
    store_unavailable: bool = False
    reason: str = ""


class StoreUnavailable(RuntimeError):
    """The bucket store could not be reached or could not answer."""


# --- the atomic statement ----------------------------------------------------
#
# ONE statement. It increments and returns the post-increment count in the same
# round trip, so there is no read-then-write window for two instances to race in.
#
# Parameter order per VALUES row -- asserted by tests/api/test_rate_limit_distributed.py
# so a reordering is a test failure rather than a silent mis-key:
#
#     1. workspace_id
#     2. user_id
#     3. endpoint_class
#     4. window_seconds   (window_start)
#     5. window_seconds   (expires_at base)
#     6. window_seconds   (expires_at offset)
#
# now() is the transaction timestamp and is evaluated once for the whole
# statement, so every row in a multi-row call lands in a consistent window, and
# the window boundary comes from the DATABASE clock -- ten API instances with
# skewed clocks still agree on which bucket a request belongs to.

_VALUES_ROW = (
    "(%s, %s, %s, "
    "public.rate_limit_window_start(now(), %s), "
    "1, "
    "public.rate_limit_window_start(now(), %s) + make_interval(secs => %s))"
)

INCREMENT_SQL_TEMPLATE = (
    "INSERT INTO public.rate_limit_buckets AS b "
    "(workspace_id, user_id, endpoint_class, window_start, request_count, expires_at) "
    "VALUES {values} "
    "ON CONFLICT (workspace_id, user_id, endpoint_class, window_start) "
    "DO UPDATE SET request_count = LEAST(b.request_count + 1, {ceiling}) "
    "RETURNING workspace_id, user_id, endpoint_class, request_count, "
    "GREATEST(1, CEIL(EXTRACT(EPOCH FROM (b.expires_at - now()))))::INTEGER AS retry_after_seconds"
)

PRUNE_SQL = "SELECT public.prune_rate_limit_buckets(now(), %s)"

ACTIVE_OPTIMIZATION_JOBS_SQL = (
    "SELECT count(*) FROM public.optimization_jobs WHERE workspace_id = %s AND status IN ('QUEUED', 'RUNNING')"
)


def build_increment_sql(row_count: int) -> str:
    """Render the atomic upsert for ``row_count`` buckets.

    Every bucket for a request goes into ONE statement, so the whole check is a
    single round trip and a single atomic unit.
    """
    if row_count < 1:
        raise ValueError("at least one bucket is required")
    values = ", ".join([_VALUES_ROW] * row_count)
    return INCREMENT_SQL_TEMPLATE.format(values=values, ceiling=_COUNT_CEILING)


# --- metrics -----------------------------------------------------------------


class RateLimitMetrics:
    """Counters for the limiter itself.

    ``store_unavailable`` and ``fail_open_admitted`` exist so a limiter that has
    stopped limiting is visible from the outside. A rate limiter that fails
    quietly is indistinguishable from one that is working.
    """

    _NAMES = (
        "allowed",
        "denied",
        "store_unavailable",
        "fail_closed_rejected",
        "fail_open_admitted",
        "deny_cache_short_circuit",
        "prune_rows_deleted",
    )

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, str], int] = {}

    def increment(self, name: str, endpoint_class: str = "all", amount: int = 1) -> None:
        with self._lock:
            key = (name, endpoint_class)
            self._counters[key] = self._counters.get(key, 0) + amount

    def snapshot(self) -> dict[tuple[str, str], int]:
        with self._lock:
            return dict(self._counters)

    def render_prometheus_lines(self) -> list[str]:
        lines = [
            "# HELP zonepilot_rate_limit_events_total Rate limiter outcomes.",
            "# TYPE zonepilot_rate_limit_events_total counter",
        ]
        for (name, endpoint_class), value in sorted(self.snapshot().items()):
            lines.append(
                f'zonepilot_rate_limit_events_total{{outcome="{name}",endpoint_class="{endpoint_class}"}} {value}'
            )
        return lines


rate_limit_metrics = RateLimitMetrics()


# --- stores ------------------------------------------------------------------


class RateLimitStore:
    """Bucket storage interface. Implementations must be atomic per bucket."""

    def increment(
        self, keys: Sequence[RateLimitKey], windows: Sequence[int]
    ) -> dict[tuple[str, str, str], tuple[int, int]]:
        raise NotImplementedError

    def prune(self, batch_size: int) -> int:
        raise NotImplementedError

    def active_optimization_jobs(self, workspace_id: str) -> int:
        raise NotImplementedError


class PostgresRateLimitStore(RateLimitStore):
    """The real store. One pooled connection, one statement per check."""

    def __init__(self, connection_factory=None) -> None:
        self._connection_factory = connection_factory
        self._pool = None
        self._pool_lock = threading.Lock()

    # -- connection handling
    def _pooled_connection(self):
        if self._connection_factory is not None:
            return self._connection_factory()
        return self._ensure_pool().connection()

    def _ensure_pool(self):
        if self._pool is not None:
            return self._pool
        with self._pool_lock:
            if self._pool is not None:
                return self._pool
            try:
                from psycopg_pool import ConnectionPool

                from services.common.db_dsn import get_database_dsn

                dsn = get_database_dsn()
                self._pool = ConnectionPool(
                    dsn,
                    min_size=_int_env("ZONEPILOT_RATE_LIMIT_POOL_MIN", 1, minimum=0),
                    max_size=_int_env("ZONEPILOT_RATE_LIMIT_POOL_MAX", 4),
                    timeout=float(_int_env("ZONEPILOT_RATE_LIMIT_POOL_TIMEOUT_SECONDS", 3)),
                    kwargs={"autocommit": True, "connect_timeout": 3},
                    open=True,
                )
            except Exception as exc:  # noqa: BLE001 - any failure here is "no store"
                raise StoreUnavailable(str(exc)) from exc
            return self._pool

    def _execute(self, sql: str, params: Sequence[Any], *, fetch: bool = True) -> list[tuple]:
        try:
            with self._pooled_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return list(cur.fetchall()) if fetch else []
        except StoreUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001
            # Deliberately broad: psycopg raises a family of transport errors and
            # psycopg_pool raises its own PoolTimeout. Anything that stops us
            # getting an authoritative count is the same condition -- "no store"
            # -- and must reach the caller as such rather than as a 500.
            raise StoreUnavailable(f"{type(exc).__name__}: {exc}") from exc

    # -- operations
    def increment(
        self, keys: Sequence[RateLimitKey], windows: Sequence[int]
    ) -> dict[tuple[str, str, str], tuple[int, int]]:
        if len(keys) != len(windows):
            raise ValueError("each key needs exactly one window width")
        params: list[Any] = []
        for key, window in zip(keys, windows, strict=True):
            params.extend(
                [
                    key.workspace_id,
                    key.user_id,
                    key.endpoint_class.value,
                    window,
                    window,
                    window,
                ]
            )
        rows = self._execute(build_increment_sql(len(keys)), params)
        return {(str(row[0]), str(row[1]), str(row[2])): (int(row[3]), int(row[4])) for row in rows}

    def prune(self, batch_size: int) -> int:
        rows = self._execute(PRUNE_SQL, [batch_size])
        return int(rows[0][0]) if rows else 0

    def active_optimization_jobs(self, workspace_id: str) -> int:
        rows = self._execute(ACTIVE_OPTIMIZATION_JOBS_SQL, [workspace_id])
        return int(rows[0][0]) if rows else 0


# --- the limiter -------------------------------------------------------------


@dataclass
class _DenyCache:
    """Bounded, window-scoped memory of source addresses already over budget.

    This is per-process, and that is safe *because it can only ever deny*. The
    bug being fixed was per-process state that ADMITTED too much; a per-process
    cache that only refuses cannot reintroduce it -- the worst it can do is
    refuse a caller that another instance would also have refused.

    It exists to stop a caller that is already over its network budget from
    generating one database write, and one table row, per request.
    """

    max_entries: int = 4096
    clock: Callable[[], float] = time.monotonic
    # Keyed by (network principal, endpoint class), NOT by principal alone.
    # Keying on the principal would mean a caller who exhausted the DAILY
    # assistant budget was short-circuited on every other class -- reads
    # included -- for the rest of that day, from a budget that never applied to
    # them. The entry must expire with the bucket that created it, and only for
    # the traffic that bucket governs.
    _denied_until: dict[tuple[str, str], float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def deny_until(self, principal: str, endpoint_class: str, until: float) -> None:
        with self._lock:
            if len(self._denied_until) >= self.max_entries:
                # Bounded by construction: drop everything already expired, and
                # if that is not enough, drop the whole map. Losing entries only
                # costs us a database round trip; it cannot over-admit.
                now = self.clock()
                self._denied_until = {k: v for k, v in self._denied_until.items() if v > now}
                if len(self._denied_until) >= self.max_entries:
                    self._denied_until.clear()
            self._denied_until[(principal, endpoint_class)] = until

    def seconds_remaining(self, principal: str, endpoint_class: str) -> int:
        with self._lock:
            key = (principal, endpoint_class)
            until = self._denied_until.get(key)
            if until is None:
                return 0
            remaining = until - self.clock()
            if remaining <= 0:
                self._denied_until.pop(key, None)
                return 0
            return max(1, int(remaining) + 1)


class DistributedRateLimiter:
    """Enforces the shared quota across every API instance."""

    def __init__(
        self,
        store: RateLimitStore | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._store = store if store is not None else PostgresRateLimitStore()
        self._clock = clock
        self._deny_cache = _DenyCache(clock=clock)
        self._prune_lock = threading.Lock()
        self._next_prune_at = 0.0

    @property
    def store(self) -> RateLimitStore:
        return self._store

    # -- configuration
    @staticmethod
    def enabled() -> bool:
        return _truthy_env("ZONEPILOT_RATE_LIMIT_ENABLED", default=True)

    @staticmethod
    def fail_open() -> bool:
        """Operator escape hatch. Off by default, and never silent when on."""
        return _truthy_env("ZONEPILOT_RATE_LIMIT_FAIL_OPEN", default=False)

    @staticmethod
    def network_multiplier() -> int:
        """How much more a source address may spend than one identity.

        Above 1 so that a shared NAT or an office egress IP is not throttled to a
        single user's budget, while a single address still cannot outspend the
        whole tenant.
        """
        return _int_env("ZONEPILOT_RATE_LIMIT_NETWORK_MULTIPLIER", 5)

    # -- main entry point
    def check(
        self,
        *,
        endpoint_class: EndpointClass,
        workspace_id: str,
        user_id: str,
        network_id: str,
    ) -> RateLimitDecision:
        """Charge this request to every bucket that applies and decide.

        Returns a decision; never raises for a store outage. The caller inspects
        ``store_unavailable`` and applies the configured failure mode.
        """
        classes = (endpoint_class, *companion_classes(endpoint_class))

        cached = self._deny_cache.seconds_remaining(network_id, endpoint_class.value)
        if cached:
            rate_limit_metrics.increment("deny_cache_short_circuit", endpoint_class.value)
            rate_limit_metrics.increment("denied", endpoint_class.value)
            return RateLimitDecision(
                allowed=False,
                endpoint_class=endpoint_class,
                limit=0,
                remaining=0,
                retry_after_seconds=cached,
                scope="network",
                reason="network budget exhausted",
            )

        keys: list[RateLimitKey] = []
        windows: list[int] = []
        limits: dict[tuple[str, str, str], int] = {}

        for cls in classes:
            policy = policy_for(cls)
            candidates = (
                RateLimitKey(NO_WORKSPACE, network_id, cls),
                RateLimitKey(workspace_id, user_id, cls),
            )
            for key in candidates:
                identity = (key.workspace_id, key.user_id, key.endpoint_class.value)
                if identity in limits:
                    # Anonymous traffic makes the two keys identical. Emitting it
                    # twice would trip Postgres' "cannot affect row a second
                    # time" and take the whole check down.
                    continue
                limits[identity] = policy.limit * (self.network_multiplier() if key.scope == "network" else 1)
                keys.append(key)
                windows.append(policy.window_seconds)

        try:
            counts = self._store.increment(keys, windows)
        except StoreUnavailable as exc:
            return self._store_outage(endpoint_class, exc)

        self._maybe_prune()

        worst: RateLimitDecision | None = None
        remaining_headroom = None
        for identity, limit in limits.items():
            observed = counts.get(identity)
            if observed is None:
                # The statement did not account for a bucket we asked about. That
                # is a broken store, not an allowance.
                return self._store_outage(endpoint_class, StoreUnavailable(f"no count returned for bucket {identity}"))
            count, retry_after = observed
            headroom = limit - count
            if remaining_headroom is None or headroom < remaining_headroom:
                remaining_headroom = headroom
            if count > limit:
                scope = "network" if identity[1].startswith(_NETWORK_PREFIX) else "identity"
                if scope == "network":
                    self._deny_cache.deny_until(network_id, endpoint_class.value, self._clock() + retry_after)
                candidate = RateLimitDecision(
                    allowed=False,
                    endpoint_class=endpoint_class,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=max(1, retry_after),
                    scope=scope,
                    reason=f"{identity[2]} budget exhausted",
                )
                # Report the longest wait, so a client that obeys Retry-After
                # comes back once rather than once per exhausted bucket.
                if worst is None or candidate.retry_after_seconds > worst.retry_after_seconds:
                    worst = candidate

        if worst is not None:
            rate_limit_metrics.increment("denied", endpoint_class.value)
            return worst

        rate_limit_metrics.increment("allowed", endpoint_class.value)
        return RateLimitDecision(
            allowed=True,
            endpoint_class=endpoint_class,
            limit=policy_for(endpoint_class).limit,
            remaining=max(0, remaining_headroom or 0),
            retry_after_seconds=0,
        )

    # -- extra quotas
    def check_optimization_concurrency(self, workspace_id: str) -> RateLimitDecision:
        """Cap concurrently active optimization jobs per workspace.

        Concurrency is a gauge, not a rate, so it is answered from the authoritative
        source -- the job rows themselves -- rather than from a counter that would
        need a matching decrement on every terminal transition and would drift the
        first time a worker died mid-solve.
        """
        limit = _int_env("ZONEPILOT_MAX_CONCURRENT_OPTIMIZATIONS_PER_WORKSPACE", 3)
        if workspace_id == NO_WORKSPACE:
            # No workspace selected yet; the route's own auth will settle it.
            return RateLimitDecision(allowed=True, endpoint_class=EndpointClass.OPTIMIZATION, limit=limit)
        try:
            active = self._store.active_optimization_jobs(workspace_id)
        except StoreUnavailable as exc:
            return self._store_outage(EndpointClass.OPTIMIZATION, exc)
        if active >= limit:
            rate_limit_metrics.increment("denied", EndpointClass.OPTIMIZATION.value)
            return RateLimitDecision(
                allowed=False,
                endpoint_class=EndpointClass.OPTIMIZATION,
                limit=limit,
                remaining=0,
                retry_after_seconds=_int_env("ZONEPILOT_OPTIMIZATION_RETRY_AFTER_SECONDS", 30),
                scope="workspace",
                reason="concurrent optimization job limit reached",
            )
        return RateLimitDecision(
            allowed=True,
            endpoint_class=EndpointClass.OPTIMIZATION,
            limit=limit,
            remaining=max(0, limit - active),
        )

    def consume_assistant_tool_invocations(
        self, *, workspace_id: str, user_id: str, count: int = 1
    ) -> RateLimitDecision:
        """Charge ``count`` tool invocations against the daily tool budget.

        Separate from the assistant *request* budget because one request can fan
        out into many tool calls, and it is the fan-out that costs money.

        NOT YET CALLED from services/zonepilot/assistant/tools.py -- that module is
        outside this change's ownership. Until it is wired in, the daily tool
        budget is enforceable but unenforced.
        """
        if count < 1:
            raise ValueError("tool invocation count must be positive")
        cls = EndpointClass.ASSISTANT_TOOL_DAILY
        policy = policy_for(cls)
        key = RateLimitKey(workspace_id, _bounded_identifier(user_id, "unknown"), cls)
        try:
            counts = self._store.increment([key] * count, [policy.window_seconds] * count)
        except StoreUnavailable as exc:
            return self._store_outage(cls, exc)
        observed = counts.get((key.workspace_id, key.user_id, cls.value))
        if observed is None:
            return self._store_outage(cls, StoreUnavailable("no count returned for tool budget"))
        used, retry_after = observed
        if used > policy.limit:
            rate_limit_metrics.increment("denied", cls.value)
            return RateLimitDecision(
                allowed=False,
                endpoint_class=cls,
                limit=policy.limit,
                remaining=0,
                retry_after_seconds=max(1, retry_after),
                scope="identity",
                reason="daily assistant tool budget exhausted",
            )
        rate_limit_metrics.increment("allowed", cls.value)
        return RateLimitDecision(
            allowed=True,
            endpoint_class=cls,
            limit=policy.limit,
            remaining=max(0, policy.limit - used),
        )

    # -- failure handling
    def _store_outage(self, endpoint_class: EndpointClass, exc: Exception) -> RateLimitDecision:
        rate_limit_metrics.increment("store_unavailable", endpoint_class.value)
        open_mode = self.fail_open()
        rate_limit_metrics.increment(
            "fail_open_admitted" if open_mode else "fail_closed_rejected", endpoint_class.value
        )
        # error, not warning: a limiter that cannot count is a limiter that is not
        # limiting, whichever mode it is in. This must page, not scroll past.
        _LOG.error(
            "rate_limit_store_unavailable",
            extra={
                "endpoint_class": endpoint_class.value,
                "fail_mode": "open" if open_mode else "closed",
                "error_code": "RATE_LIMIT_STORE_UNAVAILABLE",
                "reason": type(exc).__name__,
            },
        )
        return RateLimitDecision(
            allowed=open_mode,
            endpoint_class=endpoint_class,
            limit=0,
            remaining=0,
            retry_after_seconds=_int_env("ZONEPILOT_RATE_LIMIT_OUTAGE_RETRY_AFTER_SECONDS", 5),
            store_unavailable=True,
            reason="rate limit store unavailable",
        )

    # -- housekeeping
    def _maybe_prune(self) -> None:
        """Delete expired buckets on a deterministic schedule.

        Tied to a fixed interval rather than a random sample so that "when does
        this run" has an answer. Every instance prunes; SKIP LOCKED in the
        function means they divide the work instead of blocking each other.
        """
        interval = _int_env("ZONEPILOT_RATE_LIMIT_PRUNE_INTERVAL_SECONDS", 60)
        now = self._clock()
        with self._prune_lock:
            if now < self._next_prune_at:
                return
            self._next_prune_at = now + interval
        try:
            deleted = self._store.prune(_int_env("ZONEPILOT_RATE_LIMIT_PRUNE_BATCH", 5000))
        except StoreUnavailable:
            # The check itself already succeeded; a failed prune must not turn a
            # served request into an error. Retention is still bounded because
            # the next request after the interval tries again.
            _LOG.warning("rate_limit_prune_failed", extra={"error_code": "RATE_LIMIT_PRUNE_FAILED"})
            return
        if deleted:
            rate_limit_metrics.increment("prune_rows_deleted", "all", deleted)


limiter = DistributedRateLimiter()


def principal_dimensions(
    authorization: str | None, client_host: str | None, forwarded_for: str | None
) -> tuple[str, str, str]:
    """Derive (workspace_id, user_id, network_id) for a request.

    The first two come from unverified claims and are for fairness and
    attribution. The third is the enforceable one. See the module docstring.
    """
    network_id = network_principal(client_host, forwarded_for)
    claims = unverified_claims(authorization)
    if not claims:
        # No token: identity and network are the same caller, so the same key.
        return NO_WORKSPACE, network_id, network_id
    workspace_id = _bounded_identifier(claims.get("workspace_id"), NO_WORKSPACE)
    user_id = _bounded_identifier(claims.get("sub"), network_id)
    return workspace_id, user_id, network_id


def iter_metric_lines() -> Iterable[str]:
    return rate_limit_metrics.render_prometheus_lines()
