"""Observatory Router exposing authentic PostgreSQL-backed and evidence-bearing endpoints."""

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

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
from services.api.core.telemetry import (
    DEPENDENCY_UNAVAILABLE,
    error_envelope,
    is_dependency_exception,
    looks_like_dependency_failure,
)
from services.api.repositories.artifact_catalog import ArtifactCorrupt, ArtifactNotFound, ArtifactNotReady
from services.api.services.observatory import ObservatoryService, get_observatory_service
from services.zonepilot.assistant.contracts import AssistantToolCall, ToolName
from services.zonepilot.assistant.tools import build_assistant_registry
from services.zonepilot.decisions.ledger import DecisionLedger
from services.zonepilot.decisions.repository import DecisionRepository
from services.zonepilot.economics.registry import CANONICAL_EXPERIMENTS
from services.zonepilot.forecast.contracts import BaselineModelType, ForecastTarget, PredictionRecord
from services.zonepilot.forecast.repository import ForecastRepository
from services.zonepilot.optimization.contracts import (
    DemandPoint,
    Facility,
    MatrixEvidenceClass,
    ObjectiveWeights,
    OptimizationConstraints,
    OptimizationProblem,
    SolverSettings,
    TravelMatrix,
    UncertaintyScenario,
)
from services.zonepilot.optimization.r1_catalog import FileSystemArtifactCatalog, default_data_root
from services.zonepilot.optimization.repository import OptimizationRepository
from services.zonepilot.optimization.service import OptimizationService
from services.zonepilot.release import current_release_sha
from services.zonepilot.resilience.repository import ResilienceRepository
from services.zonepilot.resilience.service import ResilienceService

router = APIRouter(prefix="/api/v1", tags=["observatory"])

# Durable Services backed by PostgreSQL
_opt_service = OptimizationService(repository=OptimizationRepository())
_res_service = ResilienceService(repository=ResilienceRepository())
_dec_ledger = DecisionLedger(repository=DecisionRepository())
_forecast_repo = ForecastRepository()


def standard_error(code: str, message: str, status_code: int = 400, **details: Any):
    """Raise the canonical error envelope (F-025).

    request_id and trace_id are injected by the app-level handler in
    services.api.main from the ids RequestIdMiddleware put on the request.
    """
    raise HTTPException(
        status_code=status_code,
        detail=error_envelope(code, message, status_code=status_code, details=details or None),
    )


def _fail_if_dependency_unavailable(exc: Exception) -> None:
    """F-025: a dependency outage is a retryable 503, never a 4xx client error.

    The broad `except Exception` blocks in this router exist to translate domain
    errors. Without this guard a DatabaseConfigurationError or a psycopg
    connection failure falls through them and is reported as 422
    VALIDATION_FAILED -- telling the caller its own request was permanently
    malformed when the real answer is "retry, the store is down".
    """
    if is_dependency_exception(exc):
        standard_error(
            DEPENDENCY_UNAVAILABLE,
            "A backing dependency is not available to serve this request.",
            503,
            dependency="database",
        )


def _translate_artifact_error(exc: Exception) -> None:
    _fail_if_dependency_unavailable(exc)
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


def _resolve_user_context(user: dict) -> tuple[str, str]:
    if not isinstance(user, dict):
        standard_error("UNAUTHORIZED", "Not authenticated", 401)
    sub = user.get("sub")
    if not sub or not isinstance(sub, str) or not sub.strip():
        standard_error("UNAUTHORIZED", "Invalid authentication token: missing sub", 401)
    ws = user.get("workspace_id")
    if not ws or not isinstance(ws, str) or not ws.strip():
        standard_error("FORBIDDEN", "Workspace membership required", 403)
    return sub.strip(), ws.strip()


# --- Zone & Network Endpoints ---


@router.get("/zones", response_model=ZoneListResponse)
def get_zones(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Return H3 cells present in verified Gold network artifact."""
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
def get_layers(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Return vector tile / GeoJSON metadata for interactive map rendering."""
    try:
        return service.map_layers()
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/datasets", response_model=DatasetListResponse)
def get_datasets(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Return catalog of immutable data assets with cryptographic checksums."""
    try:
        return service.list_datasets()
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/data-health", response_model=DataHealthResponse)
def get_data_health(
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Return real-time data freshness, staleness, and quality monitoring across providers."""
    try:
        return service.data_health()
    except Exception as exc:
        _translate_artifact_error(exc)


@router.get("/evidence/osm/{tile_path:path}")
def get_osm_evidence_tile(
    tile_path: str,
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Fetch raw OSM evidence vector tile by relative artifact path."""
    if ".." in tile_path or "//" in tile_path:
        standard_error("INVALID_ARGUMENT", "Invalid tile path traversal attempt", 422)
    try:
        raw_bytes = service.get_osm_tile(tile_path)
        return Response(content=raw_bytes, media_type="application/octet-stream")
    except Exception as exc:
        _translate_artifact_error(exc)


# --- R1 Optimization API ---


class OptimizationRequest(BaseModel):
    idempotency_key: str | None = None
    min_open_facilities: int = Field(default=1, ge=1)
    max_open_facilities: int = Field(default=4, ge=1)
    max_travel_seconds: int = Field(default=1800, ge=1)
    allow_uncovered_demand: bool = True
    scenarios: list[str] = ["s1_free_flow", "s2_congested", "s3_congested_outage"]


def _build_real_94x12x3_problem(req: OptimizationRequest) -> OptimizationProblem:
    mat_path = default_data_root() / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"
    if not mat_path.is_file():
        raise FileNotFoundError(
            "MATRIX_UNAVAILABLE: Authentic r1_osrm_travel_matrix.json is missing. Failing closed without synthetic substitution."
        )

    matrix_doc = json.loads(mat_path.read_text(encoding="utf-8"))
    facility_ids = tuple(matrix_doc["facility_ids"])
    demand_ids = tuple(matrix_doc["demand_ids"])
    base_durations = matrix_doc["base_durations_seconds"]
    graph_version = matrix_doc.get("graph_version", "1.1.0+bad320dd48da")
    router = matrix_doc.get("router", "osrm-routed-table")
    router_version = matrix_doc.get(
        "router_version",
        "osrm/osrm-backend@sha256:af5d4a83fb90086a43b1ae2ca22872e6768766ad5fcbb07a29ff90ec644ee409",
    )

    catalog = FileSystemArtifactCatalog(default_data_root())
    gold_rows = {str(r["h3_index"]): r for r in catalog.gold_rows()}

    facilities = tuple(
        Facility(
            facility_id=fid,
            capacity_units=1500,
            fixed_cost_units=1000,
            failure_exposure_basis_points=100 * idx,
        )
        for idx, fid in enumerate(facility_ids)
    )

    demands = tuple(
        DemandPoint(
            demand_id=did,
            demand_units=max(
                1,
                int(
                    gold_rows.get(did.split(":")[-1], {}).get("commercial_poi_count", 1) * 3
                    + gold_rows.get(did.split(":")[-1], {}).get("intersection_count", 1)
                ),
            ),
        )
        for did in demand_ids
    )

    # 3 Uncertainty scenarios with authentic provenance
    scenarios = []
    for s_idx, s_name in enumerate(req.scenarios):
        mult = 1.0 if s_idx == 0 else (1.4 if s_idx == 1 else 1.6)
        prob = 6000 if s_idx == 0 else (3000 if s_idx == 1 else 1000)

        durations = tuple(
            tuple(int(math.ceil(math_ceil_dur * mult)) for math_ceil_dur in row) for row in base_durations
        )

        evidence_cls = (
            MatrixEvidenceClass.PUBLIC_GEOGRAPHIC
            if s_idx == 0
            else (MatrixEvidenceClass.DERIVED if s_idx == 1 else MatrixEvidenceClass.SIMULATED_FAILURE)
        )
        parent_id = None if s_idx == 0 else "matrix-s1_free_flow"

        mat = TravelMatrix(
            matrix_id=f"matrix-{s_name}",
            graph_version=graph_version,
            router=router,
            router_version=router_version,
            evidence_class=evidence_cls,
            facility_ids=facility_ids,
            demand_ids=demand_ids,
            durations_seconds=durations,
            parent_matrix_id=parent_id,
        )

        scenarios.append(
            UncertaintyScenario(
                scenario_id=s_name,
                probability_basis_points=prob,
                travel_matrix=mat,
                capacity_adjustments=(),
            )
        )

    return OptimizationProblem(
        problem_id=f"opt-94x12x3-{uuid.uuid4().hex[:8]}",
        facilities=facilities,
        demand_points=demands,
        scenarios=tuple(scenarios),
        constraints=OptimizationConstraints(
            min_open_facilities=req.min_open_facilities,
            max_open_facilities=req.max_open_facilities,
            max_travel_seconds=req.max_travel_seconds,
            minimum_coverage_basis_points=0,
            allow_uncovered_demand=req.allow_uncovered_demand,
        ),
        objective_weights=ObjectiveWeights(
            assumption_version="r1-proxy-1.0.0",
            expected_travel=5000,
            p95_travel=1000,
            facility_cost=3000,
            failure_exposure=500,
            coverage_loss=5000 if req.allow_uncovered_demand else 0,
        ),
        solver_settings=SolverSettings(max_time_seconds=30.0, num_search_workers=1),
    )


@router.post("/optimizations", status_code=202)
def run_optimization(
    payload: OptimizationRequest,
    _user: dict = Depends(get_current_user),
):
    """Queue durable facility optimization in PostgreSQL and dispatch to Pub/Sub asynchronously."""
    user_id, ws_id = _resolve_user_context(_user)
    idem_key = payload.idempotency_key or str(uuid.uuid4())

    try:
        problem = _build_real_94x12x3_problem(payload)
    except FileNotFoundError as fnf_err:
        standard_error("MATRIX_UNAVAILABLE", str(fnf_err), 503)

    job = _opt_service.submit_optimization(
        requested_by=user_id,
        workspace_id=ws_id,
        idempotency_key=idem_key,
        problem=problem,
        custom_payload=payload.model_dump(),
    )
    return {
        "job_id": str(job["id"]),
        "status": job["status"],
        "solver_status": job.get("solver_status"),
        "idempotency_key": idem_key,
        "created_at": str(job.get("created_at")),
    }


@router.get("/optimizations")
def list_optimizations(
    _user: dict = Depends(get_current_user),
):
    """List recent persistent optimization jobs for the workspace."""
    _, ws_id = _resolve_user_context(_user)
    jobs = _opt_service.repository.list_jobs(ws_id)
    items = []
    for j in jobs:
        items.append(
            {
                "job_id": str(j["id"]),
                "status": j["status"],
                "solver_status": j.get("solver_status"),
                "created_at": str(j.get("created_at")),
                "started_at": str(j.get("started_at")),
                "finished_at": str(j.get("finished_at")),
                "run_duration_ms": j.get("run_duration_ms"),
            }
        )
    return {"jobs": items}


@router.get("/optimizations/{opt_id}")
def get_optimization(
    opt_id: str,
    _user: dict = Depends(get_current_user),
):
    """Retrieve persistent optimization job and computed result from PostgreSQL."""
    _, ws_id = _resolve_user_context(_user)
    job = _opt_service.get_optimization(opt_id, ws_id)
    if not job:
        standard_error("NOT_FOUND", f"Optimization job {opt_id} not found in database.", 404)

    res_doc = job.get("result_document") or {}
    opened = res_doc.get("opened_facility_ids") or res_doc.get("opened_facilities", [])
    expected_travel = res_doc.get("expected_travel_seconds")
    p95_travel = res_doc.get("p95_travel_seconds")
    if expected_travel is None and "objective" in res_doc:
        expected_travel = res_doc["objective"].get("expected_travel_probability_demand_seconds")
    if p95_travel is None and "objective" in res_doc:
        p95_travel = res_doc["objective"].get("p95_travel_demand_seconds")

    return {
        "job_id": str(job["id"]),
        "status": job["status"],
        "solver_status": job.get("solver_status") or res_doc.get("status"),
        "fail_closed": job.get("fail_closed")
        if job.get("fail_closed") is not None
        else res_doc.get("fail_closed", False),
        "opened_facilities": opened,
        "expected_travel_seconds": expected_travel,
        "p95_travel_seconds": p95_travel,
        "coverage_basis_points": res_doc.get("coverage_basis_points"),
        "created_at": str(job.get("created_at")),
        "started_at": str(job.get("started_at")),
        "finished_at": str(job.get("finished_at")),
        "run_duration_ms": job.get("run_duration_ms"),
        "result_document": res_doc,
    }


# --- R4 Durable Scenario Execution API ---


class ScenarioCreateRequest(BaseModel):
    scenario_type: str = "ROAD_CLOSURE"
    description: str = "Simulated primary corridor disruption"
    parameters: dict[str, Any] = Field(default_factory=dict)
    seed: int = 42


@router.post("/scenarios", status_code=201)
def create_and_run_scenario(
    payload: ScenarioCreateRequest,
    _user: dict = Depends(get_current_user),
):
    """Execute scenario evaluation, compute graph degradation and delta metrics, save to PostgreSQL."""
    user_id, ws_id = _resolve_user_context(_user)
    try:
        scen = _res_service.execute_scenario(
            workspace_id=ws_id,
            scenario_type=payload.scenario_type,
            description=payload.description,
            parameters=payload.parameters,
            seed=payload.seed,
            created_by=user_id,
        )
        return scen
    except FileNotFoundError as matrix_err:
        # The authentic routing matrix is absent. Fail closed with a retryable
        # dependency error rather than grading resilience on invented travel
        # times (F-010).
        standard_error("MATRIX_UNAVAILABLE", str(matrix_err), 503)
    except HTTPException:
        raise
    except Exception as exc:
        _fail_if_dependency_unavailable(exc)
        standard_error("EXECUTION_ERROR", str(exc), 422)


@router.get("/scenarios")
def list_scenarios(_user: dict = Depends(get_current_user)):
    """List all persisted scenarios and evaluated resilience results."""
    _, ws_id = _resolve_user_context(_user)
    items = _res_service.list_scenarios(ws_id)
    return {"data": items, "scenarios": items}


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str, _user: dict = Depends(get_current_user)):
    """Retrieve durable scenario definition and real evaluated resilience metrics."""
    _, ws_id = _resolve_user_context(_user)
    scen = _res_service.get_scenario(scenario_id, ws_id)
    if not scen:
        standard_error("NOT_FOUND", f"Scenario {scenario_id} not found in database.", 404)
    return scen


# --- R5 Experiments API ---


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


# --- R7 Durable Decision Ledger & Replay API ---


class DecisionFreezeRequest(BaseModel):
    optimization_job_id: str
    scenario_ids: list[str] = Field(default_factory=lambda: ["s1_free_flow", "s2_congested", "s3_congested_outage"])
    operator_rationale: str | None = None


class DecisionCreateRequest(BaseModel):
    """Direct decision record submission.

    Every lineage and measurement field is REQUIRED. These previously carried
    fabricated defaults, so POST /decisions with an empty body wrote a complete,
    plausible-looking decision -- facilities, objective value, travel times,
    coverage, artifact hashes -- into the immutable ledger with no real lineage,
    bypassing the DECISION_LINEAGE_INCOMPLETE guards that the optimization-backed
    path enforces. A ledger that can be populated with invented measurements is
    not an audit trail.

    Prefer optimization_job_id, which derives lineage from a real solver run.
    """

    optimization_job_id: str | None = None

    # Without an optimization_job_id this endpoint writes caller-supplied numbers
    # straight into the durable ledger. Requiring the fields (F-005) stopped an
    # EMPTY body but not a well-formed fiction: an independent certifier posted
    # invented facilities, an invented OSRM hash and 100% coverage and received a
    # 201. Required is not the same as validated.
    #
    # A caller may therefore no longer author a decision implicitly. Recording one
    # by hand is a legitimate operator action, but it must be declared as such and
    # must never be indistinguishable from optimizer output.
    decision_class: Literal["MANUAL_OPERATOR_DECISION"] | None = None
    operator_rationale: str | None = Field(default=None, min_length=20)

    decision_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    network_version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    feature_snapshot_hash: str = Field(min_length=1)
    selected_action: str = Field(min_length=1)
    opened_facilities: list[str] = Field(min_length=1)
    objective_value: int
    expected_travel_seconds: int = Field(ge=0)
    p95_travel_seconds: int = Field(ge=0)
    coverage_basis_points: int = Field(ge=0, le=10000)
    graph_version: str = Field(min_length=1)
    osrm_bundle_hash: str = Field(min_length=1)
    solver_version: str = Field(min_length=1)
    evidence_ids: list[str] = []


@router.post("/decisions/freeze", status_code=201)
def freeze_decision(
    payload: DecisionFreezeRequest,
    _user: dict = Depends(get_current_user),
):
    """Freeze an immutable decision reconstructed strictly from authoritative optimization job state."""
    user_id, ws_id = _resolve_user_context(_user)
    job = _opt_service.get_optimization(payload.optimization_job_id, ws_id)
    if not job:
        standard_error("NOT_FOUND", f"Optimization job {payload.optimization_job_id} not found in workspace.", 404)
    try:
        rec = _dec_ledger.freeze_decision_from_optimization(
            job=job,
            workspace_id=ws_id,
            operator_rationale=payload.operator_rationale,
            recorded_by=user_id,
        )
        return rec.model_dump()
    except ValueError as val_err:
        err_msg = str(val_err)
        if "DECISION_LINEAGE_INCOMPLETE" in err_msg:
            standard_error("DECISION_LINEAGE_INCOMPLETE", err_msg, 422)
        else:
            standard_error("OPTIMIZATION_NOT_COMPLETED", err_msg, 400)
    except Exception as exc:
        standard_error("DECISION_STORE_UNAVAILABLE", str(exc), 503)


@router.post("/decisions", status_code=201)
def record_decision(
    payload: DecisionCreateRequest,
    _user: dict = Depends(get_current_user),
):
    """Record or freeze an immutable decision into PostgreSQL ledger.

    Prefer POST /decisions/freeze, which reconstructs every field from authoritative
    optimization state. The hand-authored path below is retained for genuine operator
    decisions but must be declared explicitly.
    """
    user_id, ws_id = _resolve_user_context(_user)

    if not payload.optimization_job_id:
        # Fail closed: an undeclared hand-authored decision is indistinguishable
        # from optimizer output once it is in the ledger.
        if payload.decision_class != "MANUAL_OPERATOR_DECISION" or not payload.operator_rationale:
            standard_error(
                "DECISION_LINEAGE_INCOMPLETE",
                "A decision without optimization_job_id is not derived from a solver run. "
                "Supply optimization_job_id to freeze from authoritative optimization state, or declare "
                'decision_class="MANUAL_OPERATOR_DECISION" with an operator_rationale of at least 20 '
                "characters. Hand-authored decisions are recorded as such and are never presented as "
                "optimizer output.",
                422,
            )

    if payload.optimization_job_id:
        job = _opt_service.get_optimization(payload.optimization_job_id, ws_id)
        if not job:
            standard_error("NOT_FOUND", f"Optimization job {payload.optimization_job_id} not found in workspace.", 404)
        try:
            rec = _dec_ledger.freeze_decision_from_optimization(
                job=job,
                workspace_id=ws_id,
                recorded_by=user_id,
            )
            return rec.model_dump()
        except ValueError as val_err:
            err_msg = str(val_err)
            if "DECISION_LINEAGE_INCOMPLETE" in err_msg:
                standard_error("DECISION_LINEAGE_INCOMPLETE", err_msg, 422)
            else:
                standard_error("OPTIMIZATION_NOT_COMPLETED", err_msg, 400)
        except Exception as exc:
            standard_error("DECISION_STORE_UNAVAILABLE", str(exc), 503)

    try:
        rec = _dec_ledger.record_decision(
            workspace_id=ws_id,
            decision_time=payload.decision_time,
            network_version=payload.network_version,
            dataset_version=payload.dataset_version,
            feature_snapshot_hash=payload.feature_snapshot_hash,
            selected_action=payload.selected_action,
            opened_facilities=payload.opened_facilities,
            objective_value=payload.objective_value,
            expected_travel_seconds=payload.expected_travel_seconds,
            p95_travel_seconds=payload.p95_travel_seconds,
            coverage_basis_points=payload.coverage_basis_points,
            graph_version=payload.graph_version,
            osrm_bundle_hash=payload.osrm_bundle_hash,
            solver_version=payload.solver_version,
            # Mark provenance on the record itself. The declaration must survive
            # into the ledger, not merely gate the request, or a later reader
            # cannot tell a hand-authored decision from a solver-derived one.
            evidence_ids=tuple(payload.evidence_ids) + ("provenance:MANUAL_OPERATOR_DECISION",),
            recorded_by=user_id,
        )
        return rec.model_dump()
    except Exception as exc:
        standard_error("DECISION_STORE_UNAVAILABLE", str(exc), 503)


@router.get("/decisions")
def list_decisions(_user: dict = Depends(get_current_user)):
    """List immutable decision records from PostgreSQL."""
    _, ws_id = _resolve_user_context(_user)
    try:
        return {"decisions": [d.model_dump() for d in _dec_ledger.list_decisions(ws_id)]}
    except Exception as exc:
        standard_error("DECISION_STORE_UNAVAILABLE", str(exc), 503)


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str, _user: dict = Depends(get_current_user)):
    """Retrieve decision record from PostgreSQL."""
    _, ws_id = _resolve_user_context(_user)
    try:
        dec = _dec_ledger.get_decision(decision_id, ws_id)
        if not dec:
            standard_error("NOT_FOUND", f"Decision {decision_id} not found in ledger.", 404)
        return dec.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        standard_error("DECISION_STORE_UNAVAILABLE", str(exc), 503)


class ReplayRequest(BaseModel):
    model_config = {"extra": "ignore"}
    feature_cutoff: datetime | None = None


@router.post("/decisions/{decision_id}/replay")
def replay_decision(
    decision_id: str,
    payload: ReplayRequest | None = None,
    _user: dict = Depends(get_current_user),
):
    """Execute server-side deterministic Point-in-Time decision replay."""
    _, ws_id = _resolve_user_context(_user)
    try:
        result = _dec_ledger.replay_decision(
            decision_id,
            workspace_id=ws_id,
            feature_cutoff=payload.feature_cutoff if payload else None,
        )
        return result.model_dump()
    except LookupError as not_found_exc:
        standard_error("NOT_FOUND", str(not_found_exc), 404)
    except FileNotFoundError as fnf_exc:
        standard_error("MATRIX_UNAVAILABLE", str(fnf_exc), 503)
    except Exception as exc:
        _fail_if_dependency_unavailable(exc)
        standard_error("REPLAY_ERROR", str(exc), 422)


class ShadowRequest(BaseModel):
    future_observation_time: datetime
    frozen_decision_time: datetime | None = None
    predicted_p95_seconds: int | None = None


@router.post("/decisions/{decision_id}/shadow", status_code=201)
@router.post("/decisions/{decision_id}/shadows", status_code=201)
def create_shadow_evaluation(
    decision_id: str,
    payload: ShadowRequest,
    _user: dict = Depends(get_current_user),
):
    """Create prospective shadow evaluation record in PostgreSQL."""
    _, ws_id = _resolve_user_context(_user)
    try:
        shadow = _dec_ledger.create_shadow(
            decision_id,
            workspace_id=ws_id,
            frozen_decision_time=payload.frozen_decision_time,
            future_observation_time=payload.future_observation_time,
            predicted_p95_seconds=payload.predicted_p95_seconds,
        )
        return shadow.model_dump()
    except LookupError as not_found_exc:
        standard_error("NOT_FOUND", str(not_found_exc), 404)
    except ValueError as val_err:
        standard_error("INVALID_SHADOW_WINDOW", str(val_err), 422)
    except Exception as exc:
        _fail_if_dependency_unavailable(exc)
        standard_error("SHADOW_ERROR", str(exc), 422)


@router.get("/shadows/{shadow_id}")
def get_shadow(shadow_id: str, _user: dict = Depends(get_current_user)):
    _, ws_id = _resolve_user_context(_user)
    try:
        shadow = _dec_ledger.get_shadow(shadow_id, ws_id)
        if not shadow:
            standard_error("NOT_FOUND", f"Shadow evaluation {shadow_id} not found in workspace.", 404)
        return shadow.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        standard_error("DECISION_STORE_UNAVAILABLE", str(exc), 503)


# --- R2 Forecast API ---


class ForecastRequest(BaseModel):
    zone_id: str = "88618925d3fffff"
    target: str = "WEATHER_TRAVEL_INFLATION_PERCENT"
    model: str = "LAST_OBSERVATION"
    horizon_hours: int = 1


@router.post("/forecast/predict", status_code=201)
def predict_forecast(
    payload: ForecastRequest,
    _user: dict = Depends(get_current_user),
):
    """Generate and persist a point-in-time deterministic forecast for an observable target."""
    _, ws_id = _resolve_user_context(_user)
    now = datetime.now(timezone.utc)
    target_time = datetime.fromtimestamp(now.timestamp() + payload.horizon_hours * 3600, tz=timezone.utc)

    try:
        ft = ForecastTarget(payload.target)
        bm = BaselineModelType(payload.model)
    except ValueError as exc:
        standard_error("INVALID_ARGUMENT", str(exc), 422)

    pred_id = f"pred-{uuid.uuid4().hex[:12]}"
    record = PredictionRecord(
        prediction_id=pred_id,
        workspace_id=ws_id,
        zone_id=payload.zone_id,
        prediction_time=now,
        target_time=target_time,
        horizon_hours=payload.horizon_hours,
        target=ft,
        predicted_value=None,
        lower_bound=None,
        upper_bound=None,
        baseline_model=bm,
        # No forecast is produced yet, so no model, snapshot, dataset or graph
        # backs this record. Previously these were literals and the snapshot hash
        # was sha256(zone_id) -- a hash of the request, not of any feature
        # snapshot -- and the evidence id resolved nowhere (F-018). Recording
        # nothing is the truthful answer while the state is EVIDENCE_ACCUMULATING.
        model_version=None,
        feature_snapshot_hash=None,
        dataset_version=None,
        graph_version=None,
        code_sha=current_release_sha(),
        evidence_ids=(),
    )

    try:
        _forecast_repo.save_prediction(record)
    except Exception as exc:
        standard_error("FORECAST_STORE_UNAVAILABLE", str(exc), 503)

    return {
        **record.model_dump(),
        "status": "EVIDENCE_ACCUMULATING",
        "message": "Baseline forecast recorded; evidence accumulating for temporal target window.",
    }


@router.get("/forecast/{zone_id}")
def get_zone_forecasts(
    zone_id: str,
    _user: dict = Depends(get_current_user),
):
    """Retrieve persisted predictions for a specific zone."""
    _, ws_id = _resolve_user_context(_user)
    rows = _forecast_repo.get_zone_forecasts(zone_id, ws_id)
    return {"forecasts": rows}


# --- R8 Assistant Deterministic Query API ---


class AssistantQuery(BaseModel):
    query: str
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)


@router.post("/assistant/query")
def assistant_query(
    body: AssistantQuery,
    _user: dict = Depends(get_current_user),
    service: ObservatoryService = Depends(get_observatory_service),
):
    """Execute typed assistant tool queries against authoritative sources only."""
    _, ws_id = _resolve_user_context(_user)
    registry = build_assistant_registry(
        observatory_service=service,
        decision_ledger=_dec_ledger,
        forecast_repository=_forecast_repo,
    )
    tool = ToolName.GET_ZONE_STATE
    if body.tool_name:
        try:
            tool = ToolName(body.tool_name)
        except ValueError:
            standard_error("INVALID_ARGUMENT", f"Unknown tool: {body.tool_name}", 422)

    call = AssistantToolCall(
        tool_name=tool,
        arguments=body.arguments,
        workspace_id=ws_id,
    )
    result = registry.execute(call)

    # F-025 / P0-ASSISTANT-TRUTH-001. A *domain* miss ("no such zone in the gold
    # network", "zone_id is required") is a legitimate typed 200 answer: the
    # assistant answered truthfully that no authoritative record backs the
    # question. An *infrastructure* failure is not -- the tool registry flattens
    # every handler exception into error_message, so a database outage would
    # otherwise be served as a successful business answer carrying success=false.
    # Those become a retryable 503 like any other dependency outage.
    if not result.success and looks_like_dependency_failure(result.error_message):
        standard_error(
            DEPENDENCY_UNAVAILABLE,
            "An authoritative source for this query is not available.",
            503,
            dependency="database",
            tool_name=tool.value,
        )

    return result.model_dump()


# --- Evidence Inspector ---


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
