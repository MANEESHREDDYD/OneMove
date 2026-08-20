import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from services.api.core.auth import get_supabase
from services.api.core.telemetry import DEPENDENCY_UNAVAILABLE, error_envelope, looks_like_dependency_failure
from supabase import Client, create_client

router = APIRouter()
logger = logging.getLogger("zonepilot.events")


def api_error(status_code: int, code: str, message: str, **details: Any) -> HTTPException:
    """Raise-ready HTTPException carrying the canonical error envelope (F-025).

    request_id and trace_id are filled in by the app-level handler in
    services.api.main from the ids RequestIdMiddleware attached to the request,
    so there is exactly one source for them.
    """
    return HTTPException(
        status_code=status_code,
        detail=error_envelope(code, message, status_code=status_code, details=details or None),
    )


# Signatures of a genuine *client* data problem: the request was accepted by the
# schema but rejected by the store on its merits. Only these become 422.
_CLIENT_DATA_SIGNATURES = (
    "violates foreign key constraint",
    "violates check constraint",
    "violates not-null constraint",
    "invalid input syntax",
    "value too long",
    "out of range",
)

# Signatures of an authorization decision made by the database (RLS).
_FORBIDDEN_SIGNATURES = (
    "permission denied",
    "row-level security",
    "row level security",
)

_DUPLICATE_SIGNATURES = (
    "duplicate key",
    "uq_probe_participant_client_event",
    "unique constraint",
)


def _is_duplicate(message: str) -> bool:
    return any(signature in message for signature in _DUPLICATE_SIGNATURES)


def _persistence_error(exc: Exception, entity: str) -> HTTPException:
    """Classify a persistence failure onto the canonical contract.

    The distinction that matters is the one F-025 was raised for: a store that is
    unreachable is a retryable 503, not a 4xx telling the client its request was
    permanently wrong.
    """
    message = str(exc).lower()

    if any(signature in message for signature in _FORBIDDEN_SIGNATURES):
        return api_error(403, "FORBIDDEN", f"Not permitted to write this {entity}.")

    if looks_like_dependency_failure(message):
        return api_error(
            503,
            DEPENDENCY_UNAVAILABLE,
            f"The {entity} store is not available to serve this request.",
            dependency="database",
        )

    if any(signature in message for signature in _CLIENT_DATA_SIGNATURES):
        return api_error(422, "VALIDATION_FAILED", f"The submitted {entity} was rejected by the store.")

    # Cause unknown: report a server-side failure rather than blaming the client.
    return api_error(500, "INTERNAL_ERROR", f"Unable to persist {entity}.")


class OrderEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: str
    event_type: str
    occurred_at: datetime
    client_event_id: str
    supersedes_id: Optional[str] = None
    correction_reason: Optional[str] = None
    payload: Optional[Any] = None


@router.post("/v1/events")
async def create_event(req: Request, event: OrderEventCreate, supabase: Client = Depends(get_supabase)):
    try:
        res = (
            supabase.table("volunteer_order_events")
            .insert(
                {
                    "order_id": event.order_id,
                    "event_type": event.event_type,
                    "occurred_at": event.occurred_at.isoformat(),
                    "provenance": "OBSERVED",
                    "client_event_id": event.client_event_id,
                    "supersedes_id": event.supersedes_id,
                    "correction_reason": event.correction_reason,
                    "payload": event.payload,
                }
            )
            .execute()
        )
        return res.data
    except Exception as exc:
        logger.exception(
            "order_event_insert_failed",
            extra={
                "request_id": req.state.request_id,
                "trace_id": getattr(req.state, "trace_id", "unknown"),
                "error_code": "EVENT_INSERT_FAILED",
            },
        )
        if _is_duplicate(str(exc).lower()):
            raise api_error(409, "CONFLICT", "Duplicate client event identifier.") from exc
        raise _persistence_error(exc, "event") from exc


class ProbeObservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
        raise api_error(500, "INTERNAL_ERROR", "Server credentials are not configured.")
    return create_client(url, key)


@router.post("/v1/probes")
async def create_probe(req: Request, probe: ProbeObservationCreate, supabase: Client = Depends(get_supabase)):
    auth_header = req.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise api_error(401, "UNAUTHORIZED", "A bearer token is required.")
    token = auth_header.split(" ")[1]

    # Cryptographic JWT verification
    from services.api.core.auth import verify_token

    payload = verify_token(token)
    participant_id = payload["sub"]

    service_client = _get_service_client()

    # Load Assignment and verify ownership
    assign_res = service_client.table("assignments").select("*").eq("id", probe.assignment_id).execute()
    if not assign_res.data or len(assign_res.data) == 0:
        raise api_error(404, "NOT_FOUND", "Assignment not found.")

    assignment = assign_res.data[0]
    if assignment["participant_id"] != participant_id:
        raise api_error(403, "FORBIDDEN", "Assignment does not belong to participant.")
    if assignment["status"] != "ACTIVE":
        raise api_error(403, "FORBIDDEN", "Assignment is not ACTIVE.")

    # Validation for Correction
    if probe.supersedes_id:
        orig_res = service_client.table("probe_observations").select("*").eq("id", probe.supersedes_id).execute()
        if not orig_res.data or len(orig_res.data) == 0:
            raise api_error(404, "NOT_FOUND", "Original probe not found.")
        orig = orig_res.data[0]
        if orig["participant_id"] != participant_id:
            raise api_error(403, "FORBIDDEN", "Original probe belongs to a different participant.")
        if orig["assignment_id"] != probe.assignment_id:
            raise api_error(403, "FORBIDDEN", "Original probe belongs to a different assignment.")
        if orig["study_id"] != assignment["study_id"]:
            raise api_error(403, "FORBIDDEN", "Original probe belongs to a different study.")
        if orig["record_status"] == "WITHDRAWN":
            raise api_error(403, "FORBIDDEN", "Original probe is withdrawn.")

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
        "intent": intent,
    }
    canonical_payload = json.dumps(semantic_dict, sort_keys=True)
    client_payload_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    # Server controlled fields
    provenance = "OBSERVED"
    received_at_server = datetime.now(timezone.utc).isoformat()

    # Timing derivation
    timing_valid = False
    timing_deviation_seconds = 0
    if scheduled_for:
        try:
            sched_dt = datetime.fromisoformat(scheduled_for.replace("Z", "+00:00"))
            obs_dt = probe.observed_at_device
            if obs_dt.tzinfo is None:
                obs_dt = obs_dt.replace(tzinfo=timezone.utc)
            timing_deviation_seconds = int((obs_dt - sched_dt).total_seconds())
            # For example, +/- 5 minutes is valid
            timing_valid = abs(timing_deviation_seconds) <= 300
        except (TypeError, ValueError):
            logger.warning(
                "assignment_schedule_parse_failed",
                extra={
                    "request_id": req.state.request_id,
                    "error_code": "INVALID_ASSIGNMENT_SCHEDULE",
                },
            )

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
        if _is_duplicate(err_str):
            # Semantic Idempotency Check using Service Role
            existing = (
                service_client.table("probe_observations")
                .select("client_payload_hash")
                .eq("participant_id", participant_id)
                .eq("client_event_id", probe.client_event_id)
                .execute()
            )

            if existing.data and len(existing.data) > 0:
                if existing.data[0]["client_payload_hash"] == client_payload_hash:
                    return {"idempotent_replay": True, "message": "Exact payload duplicate ignored."}
                else:
                    raise api_error(409, "CONFLICT", "Conflicting reuse of client_event_id with a different payload.")
            raise api_error(409, "CONFLICT", "Duplicate client event identifier.") from e

        logger.exception(
            "probe_insert_failed",
            extra={
                "request_id": req.state.request_id,
                "trace_id": getattr(req.state, "trace_id", "unknown"),
                "error_code": "PROBE_INSERT_FAILED",
            },
        )
        raise _persistence_error(e, "probe observation") from e
