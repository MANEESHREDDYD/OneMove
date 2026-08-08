from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from core.auth import get_supabase
from supabase import Client

router = APIRouter()

class OrderEventCreate(BaseModel):
    order_id: str
    event_type: str
    occurred_at: datetime
    provenance: str
    client_event_id: str
    supersedes_id: Optional[str] = None
    correction_reason: Optional[str] = None
    payload: Optional[Any] = None

@router.post("/v1/events")
async def create_event(event: OrderEventCreate, supabase: Client = Depends(get_supabase)):
    try:
        # FastAPI handles the proxying and enforces the schema. 
        # Then it passes to Supabase using the User's JWT (RLS).
        res = supabase.table("volunteer_order_events").insert({
            "order_id": event.order_id,
            "event_type": event.event_type,
            "occurred_at": event.occurred_at.isoformat(),
            "provenance": event.provenance,
            "client_event_id": event.client_event_id,
            "supersedes_id": event.supersedes_id,
            "correction_reason": event.correction_reason,
            "payload": event.payload
        }).execute()
        return res.data
    except Exception as e:
        print("SUPABASE INSERT ERROR:", e, flush=True)
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
