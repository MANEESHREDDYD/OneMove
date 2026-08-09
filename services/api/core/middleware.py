import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

MAX_PAYLOAD_SIZE = 1024 * 1024 * 4 # 4 MiB (Limit for standard routes)
MAX_SCENARIO_PAYLOAD = 1024 * 1024 * 2 # 2 MiB scenario payload

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = req_id
        
        # Payload size enforcement
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > MAX_PAYLOAD_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": f"Payload size exceeds {MAX_PAYLOAD_SIZE} bytes.",
                            "request_id": req_id,
                            "retryable": False,
                            "details": {}
                        }
                    }
                )

        try:
            response = await call_next(request)
            response.headers["x-request-id"] = req_id
            return response
        except Exception as e:
            # We don't catch HTTPException here as FastAPI handles it,
            # but if it's an unhandled 500 error, we format it centrally.
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred.",
                        "request_id": req_id,
                        "retryable": True,
                        "details": {}
                    }
                }
            )
