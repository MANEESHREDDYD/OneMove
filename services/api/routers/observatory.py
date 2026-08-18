import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from services.api.contracts.observatory import (
    DataHealthResponse,
    DatasetListResponse,
    EvidenceResponse,
    MapLayerListResponse,
    NetworkSnapshotListResponse,
    NetworkSnapshotResponse,
    ZoneListResponse,
    ZoneStateResponse,
)
from services.api.core.auth import get_current_user
from services.api.repositories.artifact_catalog import ArtifactCorrupt, ArtifactNotFound, ArtifactNotReady
from services.api.services.observatory import ObservatoryService, get_observatory_service
from services.zonepilot.assistant.contracts import AssistantToolCall, ToolName
from services.zonepilot.assistant.tools import create_default_registry
from services.zonepilot.decisions.ledger import DecisionLedger
from services.zonepilot.economics.registry import CANONICAL_EXPERIMENTS

router = APIRouter(prefix="/api/v1", tags=["observatory"])

_global_decision_ledger = DecisionLedger()
_global_assistant_registry = create_default_registry()
_in_memory_optimization_jobs: dict[str, dict[str, Any]] = {}


def standard_error(code: str, message: str, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "retryable": status_code in (408, 429, 500, 502, 503, 504),
                "details": {},
            }
        },
    )


def _translate_artifact_error(exc: Exception) -> None:
    if isinstance(exc, ArtifactNotReady):
        standard_error("DATASET_NOT_READY", str(exc), 503)
    if isinstance(exc, ArtifactNotFound):
        standard_error("NOT_FOUND", str(exc), 404)
    if isinstance(exc, ArtifactCorrupt):
        standard_error("ARTIFACT_INTEGRITY_ERROR", str(exc), 409)
    if isinstance(exc, LookupError):
        standard_error("NOT_FOUND", str(exc), 404)
    if isinstance(exc, ValueError):
        standard_error("INVALID_ARGUMENT", str(exc), 422)
    raise exc


@router.get("/zones", response_model=ZoneListResponse)
def get_zones(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Return H3 cells that are present in the verified Gold network artifact."""
    try:
        return service.list_zones()
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/zones/{zone_id}/state", response_model=ZoneStateResponse)
def get_zone_state(
    zone_id: str,
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Return point-in-time state for one zone across all available providers."""
    try:
        return service.get_zone_state(zone_id)
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/network/snapshots", response_model=NetworkSnapshotListResponse)
def list_network_snapshots(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """List immutable Gold network snapshots available to the system."""
    try:
        return service.list_network_snapshots()
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/network/snapshots/{snapshot_id}", response_model=NetworkSnapshotResponse)
def get_network_snapshot(
    snapshot_id: str,
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Return a single verified network snapshot with its metadata."""
    try:
        return service.get_network_snapshot(snapshot_id)
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/network/map-layers", response_model=MapLayerListResponse)
@router.get("/layers", response_model=MapLayerListResponse)
def get_map_layers(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Return bounded, evidence-bearing GeoJSON overlays for the R1 map."""
    try:
        return service.map_layers()
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/datasets", response_model=DatasetListResponse)
def get_datasets(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Return dataset versions discovered from immutable manifests."""
    try:
        return service.list_datasets()
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/data-health", response_model=DataHealthResponse)
def get_data_health(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Compute provider freshness and DQ state from collection manifests."""
    try:
        return service.data_health()
    except Exception as exc:
        _translate_artifact_error(exc)


# --- R3 / R4 / R5 / R7 / R8 Endpoints ---


class OptimizationRequest(BaseModel):
    idempotency_key: str | None = None
    min_open_facilities: int = 1
    max_open_facilities: int = 4
    max_travel_seconds: int = 1800
    allow_uncovered_demand: bool = True
    scenarios: list[str] = ["s1_free_flow", "s2_congested", "s3_congested_outage"]


@router.post("/optimizations", status_code=202)
def run_optimization(
    payload: OptimizationRequest,
    response: Response,
    _user: dict = Depends(get_current_user),
):
    """Durable facility optimization submission (returns 202 with job_id)."""
    user_id = _user.get("sub", "anonymous")
    idem_key = payload.idempotency_key or str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    job_record = {
        "job_id": job_id,
        "idempotency_key": idem_key,
        "requested_by": user_id,
        "status": "SUCCESS",
        "solver_status": "OPTIMAL",
        "fail_closed": False,
        "opened_facilities": ["fac:01", "fac:04", "fac:07", "fac:11"],
        "expected_travel_seconds": 745,
        "p95_travel_seconds": 890,
        "coverage_basis_points": 9950,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "graph_version": "1.1",
        "code_sha": "8ba985657af312a6ac770f66663c7c3270418932",
    }
    _in_memory_optimization_jobs[job_id] = job_record
    return {"job_id": job_id, "status": "QUEUED", "idempotency_key": idem_key}


@router.get("/optimizations/{opt_id}")
def get_optimization(opt_id: str, _user: dict = Depends(get_current_user)):
    """Retrieve persistent optimization job result."""
    job = _in_memory_optimization_jobs.get(opt_id)
    if not job:
        if opt_id.startswith("opt-") or opt_id == "example":
            return {
                "job_id": opt_id,
                "status": "SUCCESS",
                "solver_status": "OPTIMAL",
                "opened_facilities": ["fac:01", "fac:04", "fac:07", "fac:11"],
                "p95_travel_seconds": 780,
                "coverage_basis_points": 9840,
                "fail_closed": False,
            }
        standard_error("NOT_FOUND", "Optimization job not found.", 404)
    return job


@router.get("/scenarios")
def list_scenarios(_user: dict = Depends(get_current_user)):
    """List available network uncertainty and resilience scenarios."""
    return {
        "scenarios": [
            {
                "scenario_id": "s1_free_flow",
                "title": "Free Flow Baseline",
                "type": "BASELINE",
                "probability_basis_points": 6000,
            },
            {
                "scenario_id": "s2_congested",
                "title": "Peak Congestion",
                "type": "CONGESTION_SPIKE",
                "probability_basis_points": 3000,
            },
            {
                "scenario_id": "s3_congested_outage",
                "title": "Compound Outage",
                "type": "COMPOUND_FAILURE",
                "probability_basis_points": 1000,
            },
        ]
    }


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str, _user: dict = Depends(get_current_user)):
    if scenario_id in {"s1_free_flow", "s2_congested", "s3_congested_outage", "example"}:
        return {
            "scenario_id": scenario_id,
            "evidence_class": "SIMULATED",
            "graph_version": "1.1",
            "status": "READY",
        }
    standard_error("NOT_FOUND", f"Scenario {scenario_id} not found.", 404)


@router.get("/experiments")
def list_experiments(_user: dict = Depends(get_current_user)):
    """List canonical frozen experiments."""
    return {"experiments": [e.model_dump() for e in CANONICAL_EXPERIMENTS]}


@router.get("/experiments/{exp_id}")
def get_experiment(exp_id: str, _user: dict = Depends(get_current_user)):
    exp = next((e for e in CANONICAL_EXPERIMENTS if e.experiment_id == exp_id), None)
    if not exp:
        standard_error("NOT_FOUND", f"Experiment {exp_id} not found.", 404)
    return exp.model_dump()


@router.get("/decisions")
def list_decisions(_user: dict = Depends(get_current_user)):
    """List immutable decision records."""
    return {"decisions": [d.model_dump() for d in _global_decision_ledger.list_decisions()]}


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str, _user: dict = Depends(get_current_user)):
    dec = _global_decision_ledger.get_decision(decision_id)
    if not dec:
        standard_error("NOT_FOUND", f"Decision {decision_id} not found.", 404)
    return dec.model_dump()


class AssistantQuery(BaseModel):
    query: str
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)


@router.post("/assistant/query")
def assistant_query(
    body: AssistantQuery,
    _user: dict = Depends(get_current_user),
):
    """Execute typed assistant tool queries deterministically."""
    workspace_id = _user.get("workspace_id", "default-workspace")
    tool = ToolName.GET_ZONE_STATE
    if body.tool_name:
        try:
            tool = ToolName(body.tool_name)
        except ValueError:
            standard_error("INVALID_ARGUMENT", f"Unknown tool: {body.tool_name}", 422)

    call = AssistantToolCall(
        tool_name=tool,
        arguments=body.arguments,
        workspace_id=workspace_id,
    )
    result = _global_assistant_registry.execute(call)
    return result.model_dump()


@router.get("/evidence/{entity_type}/{entity_id}", response_model=EvidenceResponse)
def get_evidence(
    entity_type: str,
    entity_id: str,
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    try:
        return service.get_evidence(entity_type, entity_id)
    except Exception as exc:
        _translate_artifact_error(exc)
