from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from core.auth import get_supabase
from supabase import Client, create_client
import os
import hashlib
import json

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

class ProbeObservationCreate(BaseModel):
    study_id: str
    assignment_id: str
    client_event_id: str
    zone_cluster: str
    h3_r8: Optional[str] = None
    platform: str
    intent: str
    protocol: str
    scheduled_for: Optional[datetime] = None
    observed_at_device: datetime
    device_clock_offset_ms: Optional[int] = None
    time_quality: Optional[str] = None
    eta_low_min: Optional[int] = None
    eta_high_min: Optional[int] = None
    option_count: Optional[int] = None
    availability_state: str
    reference_basket_price: Optional[float] = None
    protocol_version: str
    supersedes_id: Optional[str] = None
    correction_reason: Optional[str] = None

import base64

def _get_participant_id(req: Request) -> str:
    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    token = auth_header.split(" ")[1]
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT")
        payload = parts[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
        return decoded.get("sub")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token payload")

def _get_service_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Service Role Key missing")
    return create_client(url, key)

@router.post("/v1/probes")
async def create_probe(req: Request, probe: ProbeObservationCreate, supabase: Client = Depends(get_supabase)):
    participant_id = _get_participant_id(req)
    
    # Calculate deterministic semantic hash
    semantic_dict = {
        "assignment_id": probe.assignment_id,
        "protocol": probe.protocol,
        "eta_low_min": probe.eta_low_min,
        "eta_high_min": probe.eta_high_min,
        "option_count": probe.option_count,
        "availability_state": probe.availability_state,
        "reference_basket_price": probe.reference_basket_price,
        "observed_at_device": probe.observed_at_device.isoformat(),
        "zone_cluster": probe.zone_cluster,
        "platform": probe.platform,
        "intent": probe.intent
    }
    canonical_payload = json.dumps(semantic_dict, sort_keys=True)
    client_payload_hash = hashlib.sha256(canonical_payload.encode('utf-8')).hexdigest()
    
    # Server controlled fields
    provenance = "OBSERVED"
    received_at_server = datetime.utcnow().isoformat()
    
    # Timing derivation
    # In a real app we'd compute timing_deviation_seconds against scheduled_for, etc.
    timing_valid = True
    timing_deviation_seconds = 0
    
    insert_data = {
        "study_id": probe.study_id,
        "assignment_id": probe.assignment_id,
        "participant_id": participant_id,
        "client_event_id": probe.client_event_id,
        "zone_cluster": probe.zone_cluster,
        "h3_r8": probe.h3_r8,
        "platform": probe.platform,
        "intent": probe.intent,
        "protocol": probe.protocol,
        "scheduled_for": probe.scheduled_for.isoformat() if probe.scheduled_for else None,
        "observed_at_device": probe.observed_at_device.isoformat(),
        "received_at_server": received_at_server,
        "device_clock_offset_ms": probe.device_clock_offset_ms,
        "time_quality": probe.time_quality,
        "timing_deviation_seconds": timing_deviation_seconds,
        "timing_valid": timing_valid,
        "eta_low_min": probe.eta_low_min,
        "eta_high_min": probe.eta_high_min,
        "option_count": probe.option_count,
        "availability_state": probe.availability_state,
        "reference_basket_price": probe.reference_basket_price,
        "protocol_version": probe.protocol_version,
        "provenance": provenance,
        "supersedes_id": probe.supersedes_id,
        "correction_reason": probe.correction_reason,
        "client_payload_hash": client_payload_hash,
    }
    
    try:
        res = supabase.table("probe_observations").insert(insert_data).execute()
        return res.data
    except Exception as e:
        err_str = str(e).lower()
        if "duplicate key" in err_str or "uq_probe_participant_client_event" in err_str:
            # Semantic Idempotency Check using Service Role
            service_client = _get_service_client()
            existing = service_client.table("probe_observations").select("client_payload_hash").eq("participant_id", participant_id).eq("client_event_id", probe.client_event_id).execute()
            
            if existing.data and len(existing.data) > 0:
                if existing.data[0]["client_payload_hash"] == client_payload_hash:
                    return {"idempotent_replay": True, "message": "Exact payload duplicate ignored."}
                else:
                    raise HTTPException(status_code=409, detail="Conflicting reuse of client_event_id with different payload.")
            raise HTTPException(status_code=409, detail=str(e))
        
        print("PROBE INSERT ERROR:", e, flush=True)
        raise HTTPException(status_code=400, detail=str(e))
