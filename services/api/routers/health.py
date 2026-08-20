import hmac
import logging
import os

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import PlainTextResponse

from services.api.core.telemetry import DEPENDENCY_UNAVAILABLE, metrics
from services.common.db_dsn import DatabaseConfigurationError, get_database_dsn

router = APIRouter(tags=["observability"])
logger = logging.getLogger("zonepilot.health")


@router.get("/health")
@router.get("/healthz")
@router.get("/health/live")
def liveness_probe():
    """Basic liveness probe for orchestration platforms"""
    return {"status": "ok"}


def validate_cloud_configuration() -> tuple[bool, str]:
    """Validate environment and GCP project alignment to fail closed on misconfiguration."""
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env not in {"staging", "production"}:
        return True, "local/test environment"

    gcp_project = os.environ.get("GCP_PROJECT_ID")
    pubsub_topic = os.environ.get("PUBSUB_TOPIC_OPTIMIZATIONS")

    if not gcp_project or not pubsub_topic:
        return False, "Missing required cloud configuration: GCP_PROJECT_ID or PUBSUB_TOPIC_OPTIMIZATIONS"


    expected_projects = {
        "staging": "zonepilot-stg-9a4285",
        "production": "zonepilot-prod-9a4285",
    }

    expected_project = expected_projects.get(env)
    if expected_project and gcp_project != expected_project:
        return (
            False,
            f"Environment/project mismatch: ENVIRONMENT='{env}' requires GCP_PROJECT_ID='{expected_project}', got '{gcp_project}'",
        )

    # P0-CREDENTIAL-001: there is no built-in database credential any more. Checked
    # AFTER the project match: deploying against the wrong GCP project is the more
    # specific misconfiguration, and reporting the generic database message first
    # masked it.
    if not (os.environ.get("DATABASE_URL") or os.environ.get("EXECUTION_DATABASE_URL")):
        return False, "Missing required database configuration: DATABASE_URL is not set"

    return True, "valid"


@router.get("/ready")
@router.get("/readyz")
@router.get("/health/ready")
def readiness_probe(response: Response):
    """Readiness probe checking critical dependencies like DB and cloud configuration alignment."""
    cfg_valid, cfg_msg = validate_cloud_configuration()
    if not cfg_valid:
        response.status_code = 503
        logger.error(f"readiness_check_failed_config: {cfg_msg}")
        return {"status": "unready", "db_connected": False, "reason": cfg_msg}

    # F-025: an absent/unusable DSN used to escape this probe as an uncaught
    # DatabaseConfigurationError, which surfaced as a 500. A readiness probe must
    # answer "not ready" in its own documented shape, never crash. The reason is
    # logged rather than returned: this endpoint is unauthenticated.
    try:
        db_url = get_database_dsn()
    except DatabaseConfigurationError:
        response.status_code = 503
        logger.exception(
            "readiness_database_configuration_missing",
            extra={"error_code": DEPENDENCY_UNAVAILABLE, "dependency": "database"},
        )
        return {"status": "unready", "db_connected": False}

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
