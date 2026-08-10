import os

from fastapi import APIRouter, Response

router = APIRouter(tags=["observability"])

@router.get("/healthz")
def liveness_probe():
    """Basic liveness probe for orchestration platforms"""
    return {"status": "ok"}

@router.get("/readyz")
def readiness_probe(response: Response):
    """Readiness probe checking critical dependencies like DB"""
    db_url = os.environ.get("ZONEPILOT_DB_URL")
    
    db_connected = False
    
    if db_url:
        import psycopg
        try:
            with psycopg.connect(db_url, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    db_connected = True
        except Exception:
            pass
            
    if not db_connected:
        response.status_code = 503
        return {"status": "unready", "db_connected": False}
        
    return {"status": "ready", "db_connected": True}
