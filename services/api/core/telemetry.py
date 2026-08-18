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
