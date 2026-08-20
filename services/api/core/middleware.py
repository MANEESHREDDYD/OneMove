import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from services.api.core.telemetry import (
    error_envelope,
    metrics,
    opaque_principal,
    rate_limiter,
    rate_policy,
    resolve_trace_id,
    safe_request_id,
)

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

        authorization = request.headers.get("authorization", "")
        authenticated = authorization.lower().startswith("bearer ")
        principal_source = (
            authorization[7:] if authenticated else (request.client.host if request.client else "unknown")
        )
        policy = rate_policy(request.url.path, authenticated)
        if policy:
            bucket, limit = policy
            allowed, remaining = rate_limiter.check(bucket, opaque_principal(principal_source), limit)
            if not allowed:
                response = JSONResponse(
                    status_code=429,
                    content=error_envelope(
                        "RATE_LIMITED",
                        "Request rate limit exceeded.",
                        status_code=429,
                        request_id=req_id,
                        trace_id=trace_id,
                        details={"bucket": bucket, "limit_per_minute": limit},
                    ),
                    headers={"retry-after": str(remaining), "x-request-id": req_id, "x-trace-id": trace_id},
                )
                self._record(request, response.status_code, started, req_id, correlation_id)
                return response

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
