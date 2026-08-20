import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.core.middleware import RequestIdMiddleware
from services.api.core.telemetry import (
    DEPENDENCY_UNAVAILABLE,
    canonical_error_code,
    configure_logging,
    error_envelope,
    initialize_error_tracking,
    is_retryable_status,
)
from services.api.routers import events, health, observatory, version
from services.common.db_dsn import DatabaseConfigurationError

configure_logging()
initialize_error_tracking()

app = FastAPI(
    title="OneMove Decision Engine API",
    description="OneMove Physical Commerce Network Intelligence & Decision Optimization API (internal engine namespace: zonepilot)",
    version="1.5.1",
)
app.add_middleware(RequestIdMiddleware)
allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "ZONEPILOT_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["authorization", "content-type", "x-correlation-id", "x-request-id", "x-workspace-id"],
)


logger = logging.getLogger("zonepilot.api")


def _correlation(request: Request) -> tuple[str, str]:
    """Read the ids RequestIdMiddleware put on the request. Never invent new ones."""
    return (
        getattr(request.state, "request_id", "unknown"),
        getattr(request.state, "trace_id", "unknown"),
    )


def _json(status_code: int, payload: dict, request_id: str, trace_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers={"x-request-id": request_id, "x-trace-id": trace_id},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id, trace_id = _correlation(request)

    # Routers may raise HTTPException whose detail is already the structured
    # envelope (see routers.observatory.standard_error). Complete it rather than
    # re-wrapping it, so the router's own code/details survive.
    if isinstance(exc.detail, dict) and isinstance(exc.detail.get("error"), dict):
        body = dict(exc.detail["error"])
        body.setdefault("code", canonical_error_code(exc.status_code))
        body.setdefault("message", "")
        body.setdefault("retryable", is_retryable_status(exc.status_code))
        body.setdefault("details", {})
        body["request_id"] = req_id
        body["trace_id"] = trace_id
        return _json(exc.status_code, {"error": body}, req_id, trace_id)

    return _json(
        exc.status_code,
        error_envelope(
            canonical_error_code(exc.status_code),
            str(exc.detail),
            status_code=exc.status_code,
            request_id=req_id,
            trace_id=trace_id,
        ),
        req_id,
        trace_id,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """422 is reserved for a bad *client* schema and is never retryable."""
    req_id, trace_id = _correlation(request)
    safe_errors = [
        {
            "location": [str(part) for part in error.get("loc", ())],
            "type": str(error.get("type", "validation_error")),
            "message": str(error.get("msg", "Invalid value")),
        }
        for error in exc.errors()
    ]
    return _json(
        422,
        error_envelope(
            "VALIDATION_FAILED",
            "The request body or parameters are invalid.",
            status_code=422,
            request_id=req_id,
            trace_id=trace_id,
            details={"errors": safe_errors},
        ),
        req_id,
        trace_id,
    )


# --- F-025: dependency outages are 503, centrally -----------------------------
#
# A database that is unconfigured, unreachable or mid-failover is a *retryable
# dependency* condition. Previously it escaped as an unhandled 500 or, worse,
# was translated by a route into 422 VALIDATION_FAILED, telling the client its
# own request was permanently malformed. These handlers are registered on the
# app so every route inherits the behaviour without local try/except.


def _dependency_unavailable(request: Request, exc: Exception, message: str, dependency: str) -> JSONResponse:
    req_id, trace_id = _correlation(request)
    logger.error(
        "dependency_unavailable",
        exc_info=exc,
        extra={
            "request_id": req_id,
            "trace_id": trace_id,
            "route": request.url.path,
            "dependency": dependency,
            "error_code": DEPENDENCY_UNAVAILABLE,
        },
    )
    return _json(
        503,
        error_envelope(
            DEPENDENCY_UNAVAILABLE,
            message,
            status_code=503,
            request_id=req_id,
            trace_id=trace_id,
            retryable=True,
            details={"dependency": dependency},
        ),
        req_id,
        trace_id,
    )


@app.exception_handler(DatabaseConfigurationError)
async def database_configuration_error_handler(request: Request, exc: DatabaseConfigurationError):
    return _dependency_unavailable(
        request,
        exc,
        "The database is not available to serve this request.",
        "database",
    )


try:  # psycopg is a hard runtime dependency, but the contract must not break if it is absent.
    import psycopg

    _PSYCOPG_DEPENDENCY_ERRORS: tuple[type[BaseException], ...] = (
        psycopg.OperationalError,
        psycopg.InterfaceError,
    )
except ImportError:  # pragma: no cover - psycopg is declared in pyproject
    _PSYCOPG_DEPENDENCY_ERRORS = ()


async def _psycopg_dependency_handler(request: Request, exc: Exception):
    # The driver message can embed host/user details, so it is logged, never returned.
    return _dependency_unavailable(
        request,
        exc,
        "The database is not available to serve this request.",
        "database",
    )


for _dependency_error in _PSYCOPG_DEPENDENCY_ERRORS:
    app.add_exception_handler(_dependency_error, _psycopg_dependency_handler)


app.include_router(events.router)
app.include_router(observatory.router)
app.include_router(version.router)
app.include_router(health.router)
app.include_router(health.router, prefix="/api/v1")
