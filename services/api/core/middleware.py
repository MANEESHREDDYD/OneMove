import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from services.api.core.ratelimit import (
    EndpointClass,
    classify_endpoint,
    limiter,
    principal_dimensions,
    rate_limit_metrics,
)
from services.api.core.telemetry import (
    error_envelope,
    metrics,
    resolve_trace_id,
    safe_request_id,
)

# Expose the limiter's counters on /metrics. A limiter that has silently stopped
# limiting must be visible from outside the process.
metrics.register_renderer(rate_limit_metrics.render_prometheus_lines)

MAX_PAYLOAD_SIZE = 1024 * 1024 * 4  # 4 MiB (Limit for standard routes)
MAX_SCENARIO_PAYLOAD = 1024 * 1024 * 2  # 2 MiB scenario payload


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        req_id = safe_request_id(request.headers.get("x-request-id"), lambda: str(uuid.uuid4()))
        correlation_id = safe_request_id(request.headers.get("x-correlation-id"), lambda: req_id)
        # F-025: the error envelope carries a trace_id alongside request_id. It is
        # derived from the inbound propagation headers (W3C traceparent, or the
        # X-Cloud-Trace-Context Cloud Run injects) and falls back to the
        # correlation id so the field is always populated and always joinable to
        # the access log for this request.
        trace_id = resolve_trace_id(
            request.headers.get("traceparent"),
            request.headers.get("x-cloud-trace-context"),
            correlation_id,
        )
        request.state.request_id = req_id
        request.state.correlation_id = correlation_id
        request.state.trace_id = trace_id

        # F-023: rate limiting. This runs before routing and therefore before the
        # authentication dependency, so it has no verified principal to key on.
        # It reads unverified token claims for BUCKETING ONLY and pairs every
        # check with a source-address bucket the caller cannot choose. See the
        # module docstring in services/api/core/ratelimit.py.
        #
        # This stage can only ever REFUSE a request. It never admits anything the
        # authenticator or the authorizer would have refused, because it runs
        # strictly earlier and returns a response instead of calling the route.
        limit_response = self._enforce_rate_limit(request, req_id, trace_id)
        if limit_response is not None:
            self._record(request, limit_response.status_code, started, req_id, correlation_id, trace_id)
            return limit_response

        # Payload size enforcement
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                payload_size = int(content_length)
            except ValueError:
                return self._error_response(
                    400, "INVALID_CONTENT_LENGTH", "Content-Length must be an integer.", req_id, trace_id
                )
            if payload_size < 0:
                return self._error_response(
                    400, "INVALID_CONTENT_LENGTH", "Content-Length must not be negative.", req_id, trace_id
                )
            if payload_size > MAX_PAYLOAD_SIZE:
                return JSONResponse(
                    status_code=413,
                    content=error_envelope(
                        "PAYLOAD_TOO_LARGE",
                        f"Payload size exceeds {MAX_PAYLOAD_SIZE} bytes.",
                        status_code=413,
                        request_id=req_id,
                        trace_id=trace_id,
                    ),
                    headers={"x-request-id": req_id, "x-trace-id": trace_id},
                )

        try:
            response = await call_next(request)
            response.headers["x-request-id"] = req_id
            response.headers["x-correlation-id"] = correlation_id
            response.headers["x-trace-id"] = trace_id
            self._record(request, response.status_code, started, req_id, correlation_id, trace_id)
            return response
        except Exception as exc:
            # We don't catch HTTPException here as FastAPI handles it,
            # but if it's an unhandled 500 error, we format it centrally.
            logging.getLogger("zonepilot.api").exception(
                "unhandled_request_exception",
                extra={
                    "request_id": req_id,
                    "correlation_id": correlation_id,
                    "trace_id": trace_id,
                    "route": request.url.path,
                    "error_code": "INTERNAL_ERROR",
                },
            )
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(exc)
            except ImportError:
                pass
            response = self._error_response(
                500,
                "INTERNAL_ERROR",
                "An unexpected error occurred.",
                req_id,
                trace_id,
            )
            self._record(request, response.status_code, started, req_id, correlation_id, trace_id)
            return response

    @staticmethod
    def _enforce_rate_limit(request: Request, req_id: str, trace_id: str) -> JSONResponse | None:
        """Charge the request to its buckets. Returns a response only to refuse."""
        if not limiter.enabled():
            return None

        endpoint_class = classify_endpoint(request.url.path, request.method)
        if endpoint_class is None:
            # Health, readiness and metrics are never limited. A limiter that can
            # fail a liveness probe turns a database blip into an instance-kill
            # loop and blocks the rollback that would fix it.
            return None

        workspace_id, user_id, network_id = principal_dimensions(
            request.headers.get("authorization"),
            request.client.host if request.client else None,
            request.headers.get("x-forwarded-for"),
        )

        decision = limiter.check(
            endpoint_class=endpoint_class,
            workspace_id=workspace_id,
            user_id=user_id,
            network_id=network_id,
        )

        # A workspace may only have so many optimizations in flight at once.
        # Checked after the rate budget so an over-quota caller cannot use this
        # path to probe how busy a workspace is.
        if decision.allowed and endpoint_class is EndpointClass.OPTIMIZATION and request.method.upper() == "POST":
            decision = limiter.check_optimization_concurrency(workspace_id)

        if decision.allowed:
            return None

        if decision.store_unavailable:
            if endpoint_class == EndpointClass.READ:
                logging.getLogger("zonepilot.api").warning(
                    "RATE_LIMIT_BACKEND_UNAVAILABLE",
                    extra={
                        "request_id": req_id,
                        "trace_id": trace_id,
                        "message": "Rate limit store is unavailable. Degrading gracefully to allow low-risk read."
                    }
                )
                return None
            
            # FAIL CLOSED for high-risk operations (OPTIMIZATION, WRITE, ASSISTANT, ADMIN, etc.)
            # The store is Postgres, which is a hard dependency of
            # almost every route here, so failing open would not keep the API
            # usable -- it would only remove the guard rail at the moment the
            # system is least able to absorb load. 503 rather than 429 because
            # the caller is not over quota; our dependency is down. F-025 maps
            # 503 to DEPENDENCY_UNAVAILABLE and marks it retryable.
            return RequestIdMiddleware._limit_response(
                status=503,
                code="DEPENDENCY_UNAVAILABLE",
                message="Rate limit store is unavailable; the request was refused rather than served unmetered.",
                request_id=req_id,
                trace_id=trace_id,
                retry_after=decision.retry_after_seconds,
                details={"endpoint_class": decision.endpoint_class.value, "subsystem": "rate_limit_store"},
            )

        return RequestIdMiddleware._limit_response(
            status=429,
            code="RATE_LIMITED",
            message="Request rate limit exceeded.",
            request_id=req_id,
            trace_id=trace_id,
            retry_after=decision.retry_after_seconds,
            details={
                "endpoint_class": decision.endpoint_class.value,
                "scope": decision.scope,
                "limit": decision.limit,
                "reason": decision.reason,
            },
        )

    @staticmethod
    def _limit_response(
        *,
        status: int,
        code: str,
        message: str,
        request_id: str,
        trace_id: str,
        retry_after: int,
        details: dict,
    ) -> JSONResponse:
        """Refusal in the one canonical envelope, with the headers a client needs."""
        seconds = max(1, int(retry_after))
        return JSONResponse(
            status_code=status,
            content=error_envelope(
                code,
                message,
                status_code=status,
                request_id=request_id,
                trace_id=trace_id,
                details=details,
            ),
            headers={
                "retry-after": str(seconds),
                "x-request-id": request_id,
                "x-trace-id": trace_id,
            },
        )

    @staticmethod
    def _error_response(status: int, code: str, message: str, request_id: str, trace_id: str) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content=error_envelope(
                code,
                message,
                status_code=status,
                request_id=request_id,
                trace_id=trace_id,
            ),
            headers={"x-request-id": request_id, "x-trace-id": trace_id},
        )

    @staticmethod
    def _record(
        request: Request, status: int, started: float, request_id: str, correlation_id: str, trace_id: str
    ) -> None:
        latency = time.perf_counter() - started
        route = getattr(request.scope.get("route"), "path", request.url.path)
        metrics.observe_request(request.method, route, status, latency)
        logging.getLogger("zonepilot.access").info(
            "request_completed",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
                "route": route,
                "status": status,
                "latency_ms": round(latency * 1000, 3),
            },
        )
