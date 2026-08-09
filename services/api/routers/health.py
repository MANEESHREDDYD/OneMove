import os
import httpx
from fastapi import APIRouter, Response

router = APIRouter(tags=["observability"])

@router.get("/healthz")
def liveness_probe():
    """Basic liveness probe for orchestration platforms"""
    return {"status": "ok"}

@router.get("/readyz")
async def readiness_probe(response: Response):
    """Readiness probe checking critical dependencies like DB"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY")
    
    db_connected = False
    
    if supabase_url and supabase_anon_key:
        try:
            # Quick lightweight HTTP HEAD check against the Supabase REST API
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.head(
                    f"{supabase_url}/rest/v1/",
                    headers={"apikey": supabase_anon_key}
                )
                if res.status_code in (200, 401, 403, 404): 
                    # If it responds with HTTP logic, it's reachable. 
                    # 404/401 implies reachable but maybe path/auth mismatch, still "connected" to network.
                    db_connected = True
        except Exception:
            pass
            
    if not db_connected:
        response.status_code = 503
        return {"status": "unready", "db_connected": False}
        
    return {"status": "ready", "db_connected": True}
