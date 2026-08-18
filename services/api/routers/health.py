import hmac
import logging
import os

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import PlainTextResponse

from services.api.core.telemetry import metrics

router = APIRouter(tags=["observability"])
logger = logging.getLogger("zonepilot.health")


@router.get("/healthz")
def liveness_probe():
    """Basic liveness probe for orchestration platforms"""
    return {"status": "ok"}


from services.common.db_dsn import get_database_dsn


@router.get("/readyz")
def readiness_probe(response: Response):
    """Readiness probe checking critical dependencies like DB"""
    db_url = get_database_dsn()

    db_connected = False

    if db_url:
        import psycopg

        try:
            with psycopg.connect(db_url, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    db_connected = True
        except Exception:
            logger.exception("database_readiness_check_failed", extra={"error_code": "DB_UNAVAILABLE"})

    if not db_connected:
        response.status_code = 503
        return {"status": "unready", "db_connected": False}

    return {"status": "ready", "db_connected": True}


@router.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
def operational_metrics(authorization: str | None = Header(default=None)):
    if os.environ.get("ZONEPILOT_METRICS_ENABLED", "false").lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=404, detail="Not found")
    expected_token = os.environ.get("ZONEPILOT_METRICS_TOKEN")
    supplied_token = authorization.removeprefix("Bearer ") if authorization else ""
    if expected_token and not hmac.compare_digest(supplied_token, expected_token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return PlainTextResponse(metrics.render_prometheus(), media_type="text/plain; version=0.0.4")
