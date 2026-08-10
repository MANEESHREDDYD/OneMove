from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.core.middleware import RequestIdMiddleware
from services.api.routers import events, governance, health, observatory

app = FastAPI(title="ZonePilot API", version="1.5.1")
app.add_middleware(RequestIdMiddleware)

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
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request body or parameters are invalid.",
                "request_id": req_id,
                "retryable": False,
                "details": {"errors": exc.errors()}
            }
        }
    )

app.include_router(events.router)
app.include_router(governance.router)
app.include_router(observatory.router)
app.include_router(health.router)
