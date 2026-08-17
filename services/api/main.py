import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.core.middleware import RequestIdMiddleware
from services.api.core.telemetry import configure_logging, initialize_error_tracking
from services.api.routers import events, health, observatory

configure_logging()
initialize_error_tracking()

app = FastAPI(title="ZonePilot API", version="1.5.1")
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

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = getattr(request.state, "request_id", "unknown")
    
    # Check if exc.detail is already our structured error envelope
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        payload = exc.detail
        # Make sure request_id is injected
        if "request_id" not in payload["error"]:
            payload["error"]["request_id"] = req_id
        return JSONResponse(status_code=exc.status_code, content=payload)
    
    # Generic format
    code = "UNAUTHORIZED" if exc.status_code == 401 else "FORBIDDEN" if exc.status_code == 403 else f"HTTP_{exc.status_code}"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "request_id": req_id,
                "retryable": exc.status_code in (408, 429, 500, 502, 503, 504),
                "details": {}
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", "unknown")
    safe_errors = [
        {
            "location": [str(part) for part in error.get("loc", ())],
            "type": str(error.get("type", "validation_error")),
            "message": str(error.get("msg", "Invalid value")),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request body or parameters are invalid.",
                "request_id": req_id,
                "retryable": False,
                "details": {"errors": safe_errors}
            }
        }
    )

app.include_router(events.router)
app.include_router(observatory.router)
app.include_router(health.router)
