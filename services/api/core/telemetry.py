from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_RESERVED_LOG_FIELDS = set(logging.makeLogRecord({}).__dict__)
_SENSITIVE_FIELDS = {
    "authorization",
    "password",
    "token",
    "jwt",
    "api_key",
    "apikey",
    "refresh_token",
    "secret",
}


def safe_request_id(value: str | None, fallback: Callable[[], str]) -> str:
    return value if value and _SAFE_ID.fullmatch(value) else fallback()


def opaque_principal(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": os.environ.get("ZONEPILOT_SERVICE", "zonepilot-api"),
            "environment": os.environ.get("ZONEPILOT_ENV", "local"),
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_FIELDS or key.startswith("_"):
                continue
            if key.lower() in _SENSITIVE_FIELDS:
                payload[key] = "[REDACTED]"
            elif value is not None and isinstance(value, (str, int, float, bool, dict, list)):
                payload[key] = value
        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(os.environ.get("ZONEPILOT_LOG_LEVEL", "INFO").upper())


def initialize_error_tracking() -> bool:
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=dsn,
            environment=os.environ.get("ZONEPILOT_ENV", "local"),
            release=os.environ.get("ZONEPILOT_RELEASE"),
            send_default_pii=False,
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
        )
        return True
    except (ImportError, ValueError):
        logging.getLogger("zonepilot.telemetry").exception("error_tracker_initialization_failed")
        return False


class MetricsRegistry:
    """Small in-process metrics registry suitable for the current single-service scale."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, int], int] = {}
        self._latency_sum: dict[tuple[str, str], float] = {}
        self._latency_count: dict[tuple[str, str], int] = {}

    def observe_request(self, method: str, route: str, status: int, latency_seconds: float) -> None:
        request_key = (method, route, status)
        latency_key = (method, route)
        with self._lock:
            self._requests[request_key] = self._requests.get(request_key, 0) + 1
            self._latency_sum[latency_key] = self._latency_sum.get(latency_key, 0.0) + latency_seconds
            self._latency_count[latency_key] = self._latency_count.get(latency_key, 0) + 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP zonepilot_api_requests_total Total HTTP requests.",
            "# TYPE zonepilot_api_requests_total counter",
        ]
        with self._lock:
            for (method, route, status), count in sorted(self._requests.items()):
                labels = f'method="{method}",route="{route}",status="{status}"'
                lines.append(f"zonepilot_api_requests_total{{{labels}}} {count}")
            lines.extend(
                [
                    "# HELP zonepilot_api_request_latency_seconds HTTP request latency.",
                    "# TYPE zonepilot_api_request_latency_seconds summary",
                ]
            )
            for (method, route), total in sorted(self._latency_sum.items()):
                labels = f'method="{method}",route="{route}"'
                lines.append(f"zonepilot_api_request_latency_seconds_sum{{{labels}}} {total:.9f}")
                lines.append(
                    f"zonepilot_api_request_latency_seconds_count{{{labels}}} {self._latency_count[(method, route)]}"
                )
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()


@dataclass
class _Window:
    count: int
    resets_at: float


class InMemoryRateLimiter:
    """Thread-safe fixed-window limiter; intentionally local to one API process."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._windows: dict[tuple[str, str], _Window] = {}

    def check(self, bucket: str, principal: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = self._clock()
        key = (bucket, principal)
        with self._lock:
            window = self._windows.get(key)
            if window is None or now >= window.resets_at:
                window = _Window(count=0, resets_at=now + window_seconds)
                self._windows[key] = window
            if window.count >= limit:
                return False, max(1, int(window.resets_at - now) + 1)
            window.count += 1
            return True, max(0, limit - window.count)


rate_limiter = InMemoryRateLimiter()


def rate_policy(path: str, authenticated: bool) -> tuple[str, int] | None:
    if not _truthy_env("ZONEPILOT_RATE_LIMIT_ENABLED", default=True):
        return None
    if "/auth" in path:
        return "auth", int(os.environ.get("ZONEPILOT_AUTH_RATE_LIMIT_PER_MINUTE", "10"))
    if any(segment in path for segment in ("/scenarios", "/optimizer", "/jobs")):
        return "expensive", int(os.environ.get("ZONEPILOT_EXPENSIVE_RATE_LIMIT_PER_MINUTE", "20"))
    if authenticated:
        return "authenticated", int(os.environ.get("ZONEPILOT_API_RATE_LIMIT_PER_MINUTE", "120"))
    return None


def _truthy_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# --- F-025: canonical API error contract -------------------------------------
#
# One definition of the wire envelope, shared by the middleware, the app-level
# exception handlers and the routers, so a client can rely on exactly one shape:
#
#   {"error": {"code", "message", "retryable", "details", "request_id", "trace_id"}}

CANONICAL_ERROR_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_FAILED",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "DEPENDENCY_UNAVAILABLE",
    503: "DEPENDENCY_UNAVAILABLE",
    504: "DEPENDENCY_UNAVAILABLE",
}

# A retryable status tells the client the failure is transient. 4xx client
# mistakes are never retryable; dependency/transport failures always are.
RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})

DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"

_TRACEPARENT = re.compile(r"^[0-9a-fA-F]{2}-([0-9a-fA-F]{32})-[0-9a-fA-F]{16}-[0-9a-fA-F]{2}$")
_CLOUD_TRACE = re.compile(r"^([0-9a-fA-F]{8,32})(?:/\d+)?(?:;o=[01])?$")

# Signatures of a *dependency* failure (database / pooler / socket), used where a
# lower layer has already flattened the exception into a string and the type is
# no longer available. Keep this list narrow: a false positive turns a permanent
# client error into a retryable one.
_DEPENDENCY_FAILURE_SIGNATURES = (
    "databaseconfigurationerror",
    "database_url is required",
    "execution_database_url",
    "operationalerror",
    "interfaceerror",
    "could not connect",
    "connection refused",
    "connection reset",
    "connection timed out",
    "server closed the connection",
    "no connection to the server",
    "name or service not known",
    "temporary failure in name resolution",
    "pool timeout",
    "too many connections",
    "the database system is starting up",
    "psycopg",
)


def canonical_error_code(status_code: int) -> str:
    """Map an HTTP status onto the one error code clients are allowed to see."""
    return CANONICAL_ERROR_CODES.get(status_code, f"HTTP_{status_code}")


def is_retryable_status(status_code: int) -> bool:
    return status_code in RETRYABLE_STATUS_CODES


def resolve_trace_id(traceparent: str | None, cloud_trace_context: str | None, fallback: str) -> str:
    """Derive a trace id from standard propagation headers, else fall back.

    Accepts W3C `traceparent` and Google Cloud `X-Cloud-Trace-Context` (Cloud Run
    injects the latter). Anything unparseable is ignored rather than echoed, so a
    caller cannot inject arbitrary text into logs or the error envelope.
    """
    if traceparent:
        match = _TRACEPARENT.fullmatch(traceparent.strip())
        if match:
            return match.group(1).lower()
    if cloud_trace_context:
        match = _CLOUD_TRACE.fullmatch(cloud_trace_context.strip())
        if match:
            return match.group(1).lower()
    return fallback


def error_envelope(
    code: str,
    message: str,
    *,
    status_code: int | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    details: dict[str, Any] | None = None,
    retryable: bool | None = None,
) -> dict[str, Any]:
    """Build the canonical error body. `retryable` defaults from the status."""
    if retryable is None:
        retryable = is_retryable_status(status_code) if status_code is not None else False
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": bool(retryable),
            "details": dict(details or {}),
            "request_id": request_id or "unknown",
            "trace_id": trace_id or "unknown",
        }
    }


def looks_like_dependency_failure(message: str | None) -> bool:
    """True when a stringified failure is recognisably a dependency outage.

    Used only where the original exception type has already been discarded by a
    lower layer (for example the assistant tool registry, which flattens every
    handler exception into `error_message`). Prefer catching the exception type.
    """
    if not message:
        return False
    lowered = message.lower()
    return any(signature in lowered for signature in _DEPENDENCY_FAILURE_SIGNATURES)


def is_dependency_exception(exc: BaseException) -> bool:
    """True when an exception means a backing dependency is unusable.

    Imports are local so this module stays a leaf: it is imported by the
    middleware, the app-level handlers and the routers alike.
    """
    try:
        from services.common.db_dsn import DatabaseConfigurationError
    except ImportError:  # pragma: no cover
        pass
    else:
        if isinstance(exc, DatabaseConfigurationError):
            return True

    try:
        import psycopg
    except ImportError:  # pragma: no cover - psycopg is declared in pyproject
        pass
    else:
        if isinstance(exc, (psycopg.OperationalError, psycopg.InterfaceError)):
            return True

    return looks_like_dependency_failure(str(exc))
