from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime
from core.auth import get_supabase
from supabase import Client, create_client
import os
import hashlib
import json

router = APIRouter()

class OrderEventCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    order_id: str
    event_type: str
    occurred_at: datetime
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
            "provenance": "OBSERVED",
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
    model_config = ConfigDict(extra='forbid')
    assignment_id: str
    client_event_id: str
    observed_at_device: datetime
    device_clock_offset_ms: Optional[int] = None
    time_quality: Optional[str] = None
    eta_low_min: Optional[int] = None
    eta_high_min: Optional[int] = None
    option_count: Optional[int] = None
    availability_state: str
    reference_basket_price: Optional[float] = None
    supersedes_id: Optional[str] = None
    correction_reason: Optional[str] = None

def _get_service_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Service Role Key missing")
    return create_client(url, key)

@router.post("/v1/probes")
async def create_probe(req: Request, probe: ProbeObservationCreate, supabase: Client = Depends(get_supabase)):
    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    token = auth_header.split(" ")[1]
    
    # Cryptographic JWT verification
    from core.auth import verify_token
    payload = verify_token(token)
    participant_id = payload["sub"]
    
    service_client = _get_service_client()
    
    # Load Assignment and verify ownership
    assign_res = service_client.table("assignments").select("*").eq("id", probe.assignment_id).execute()
    if not assign_res.data or len(assign_res.data) == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")
        
    assignment = assign_res.data[0]
    if assignment["participant_id"] != participant_id:
        raise HTTPException(status_code=403, detail="Assignment does not belong to participant")
    if assignment["status"] != "ACTIVE":
        raise HTTPException(status_code=403, detail="Assignment is not ACTIVE")
        
    # Validation for Correction
    if probe.supersedes_id:
        orig_res = service_client.table("probe_observations").select("*").eq("id", probe.supersedes_id).execute()
        if not orig_res.data or len(orig_res.data) == 0:
            raise HTTPException(status_code=404, detail="Original probe not found")
        orig = orig_res.data[0]
        if orig["participant_id"] != participant_id:
            raise HTTPException(status_code=403, detail="Original probe belongs to a different participant")
        if orig["assignment_id"] != probe.assignment_id:
            raise HTTPException(status_code=403, detail="Original probe belongs to a different assignment")
        if orig["study_id"] != assignment["study_id"]:
            raise HTTPException(status_code=403, detail="Original probe belongs to a different study")
        if orig["record_status"] == "WITHDRAWN":
            raise HTTPException(status_code=403, detail="Original probe is withdrawn")

    # Derive structural fields from assignment
    study_id = assignment["study_id"]
    zone_cluster = assignment["zone_cluster"]
    platform = assignment["platform"]
    intent = assignment["intent"]
    protocol = assignment["protocol"]
    scheduled_for = assignment.get("scheduled_for")
    protocol_version = assignment["protocol_version"]
    
    # Calculate deterministic semantic hash (using server-resolved structural fields!)
    semantic_dict = {
        "assignment_id": probe.assignment_id,
        "protocol": protocol,
        "eta_low_min": probe.eta_low_min,
        "eta_high_min": probe.eta_high_min,
        "option_count": probe.option_count,
        "availability_state": probe.availability_state,
        "reference_basket_price": probe.reference_basket_price,
        "observed_at_device": probe.observed_at_device.isoformat(),
        "zone_cluster": zone_cluster,
        "platform": platform,
        "intent": intent
    }
    canonical_payload = json.dumps(semantic_dict, sort_keys=True)
    client_payload_hash = hashlib.sha256(canonical_payload.encode('utf-8')).hexdigest()
    
    # Server controlled fields
    provenance = "OBSERVED"
    received_at_server = datetime.utcnow().isoformat()
    
    # Timing derivation
    timing_valid = False
    timing_deviation_seconds = 0
    if scheduled_for:
        try:
            sched_dt = datetime.fromisoformat(scheduled_for.replace('Z', '+00:00'))
            obs_dt = probe.observed_at_device
            if obs_dt.tzinfo is None:
                obs_dt = obs_dt.replace(tzinfo=datetime.timezone.utc)
            timing_deviation_seconds = int((obs_dt - sched_dt).total_seconds())
            # For example, +/- 5 minutes is valid
            timing_valid = abs(timing_deviation_seconds) <= 300
        except Exception:
            pass
    
    insert_data = {
        "study_id": study_id,
        "assignment_id": probe.assignment_id,
        "participant_id": participant_id,
        "client_event_id": probe.client_event_id,
        "zone_cluster": zone_cluster,
        "platform": platform,
        "intent": intent,
        "protocol": protocol,
        "scheduled_for": scheduled_for,
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
        "protocol_version": protocol_version,
        "provenance": provenance,
        "supersedes_id": probe.supersedes_id,
        "correction_reason": probe.correction_reason,
        "client_payload_hash": client_payload_hash,
    }
    
    try:
        # Use user-scoped client so RLS applies
        res = supabase.table("probe_observations").insert(insert_data).execute()
        return res.data
    except Exception as e:
        err_str = str(e).lower()
        if "duplicate key" in err_str or "uq_probe_participant_client_event" in err_str:
            # Semantic Idempotency Check using Service Role
            existing = service_client.table("probe_observations").select("client_payload_hash").eq("participant_id", participant_id).eq("client_event_id", probe.client_event_id).execute()
            
            if existing.data and len(existing.data) > 0:
                if existing.data[0]["client_payload_hash"] == client_payload_hash:
                    return {"idempotent_replay": True, "message": "Exact payload duplicate ignored."}
                else:
                    raise HTTPException(status_code=409, detail="Conflicting reuse of client_event_id with different payload.")
            raise HTTPException(status_code=409, detail=str(e))
        
        print("PROBE INSERT ERROR:", e, flush=True)
        raise HTTPException(status_code=400, detail=str(e))
