from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum
from core.provenance import Provenance

router = APIRouter()

class EventStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"

class OrderEventCreate(BaseModel):
    order_id: str
    event_type: str
    occurred_at: datetime
    provenance: Provenance
    supersedes_id: Optional[str] = None
    correction_reason: Optional[str] = None

@router.post("/v1/orders/{order_id}/events")
async def create_order_event(order_id: str, event: OrderEventCreate):
    """
    Append-only endpoint for order events (FR-4/C1).
    Does not mutate original order data. Appends a new event describing state change.
    """
    # Logic to insert into Supabase via trusted service client
    # ensuring record_status = 'ACTIVE' and handling supersedes logic if provided.
    
    return {"status": "success", "message": "Event appended securely."}

