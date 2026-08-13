
from fastapi import APIRouter, Depends, HTTPException, Request

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

router = APIRouter(prefix="/api/v1", tags=["observatory"])


def standard_error(code: str, message: str, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "retryable": status_code in (408, 429, 500, 502, 503, 504),
                "details": {}
            }
        }
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
    """Return evidence-bearing static state for one real Gold H3 cell."""
    try:
        return service.get_zone_state(zone_id)
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/network/snapshots", response_model=NetworkSnapshotListResponse)
def get_network_snapshots(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
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
    """Return an immutable, versioned OSRM network snapshot when mounted."""
    try:
        return service.get_network_snapshot(snapshot_id)
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/network/map-layers", response_model=MapLayerListResponse)
def get_network_map_layers(
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

@router.post("/scenarios")
def create_scenario(request: Request, _user: dict = Depends(get_current_user)):
    """Idempotent scenario creation"""
    standard_error("NOT_IMPLEMENTED", "Scenario builder not yet active.", 501)

@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str, _user: dict = Depends(get_current_user)):
    standard_error("NOT_FOUND", "Scenario not found.", 404)

@router.post("/optimizations")
def run_optimization(_user: dict = Depends(get_current_user)):
    standard_error("NOT_IMPLEMENTED", "Robust optimization not yet active.", 501)

@router.get("/optimizations/{opt_id}")
def get_optimization(opt_id: str, _user: dict = Depends(get_current_user)):
    standard_error("NOT_FOUND", "Optimization not found.", 404)

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
