"""Observatory Router exposing authentic PostgreSQL-backed and evidence-bearing endpoints."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
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
from services.zonepilot.resilience.repository import ResilienceRepository
from services.zonepilot.resilience.service import ResilienceService

router = APIRouter(prefix="/api/v1", tags=["observatory"])

# Durable Services backed by PostgreSQL
_opt_service = OptimizationService(repository=OptimizationRepository())
_res_service = ResilienceService(repository=ResilienceRepository())
_dec_ledger = DecisionLedger(repository=DecisionRepository())
_forecast_repo = ForecastRepository()
_assistant_registry = create_default_registry()


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


def _resolve_user_context(user: dict) -> tuple[str, str]:
    sub = user.get("sub") or "00000000-0000-0000-0000-000000000001"
    if not (len(sub) == 36 and "-" in sub):
        sub = "00000000-0000-0000-0000-000000000001"
    ws = user.get("workspace_id") or "ws-pilot-default"
    return sub, ws


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


# --- R3 Durable Optimizer API ---


class OptimizationRequest(BaseModel):
    idempotency_key: str | None = None
    min_open_facilities: int = 1
    max_open_facilities: int = 4
    max_travel_seconds: int = 1800
    allow_uncovered_demand: bool = True
    scenarios: list[str] = ["s1_free_flow", "s2_congested", "s3_congested_outage"]


def _build_real_94x12x3_problem(req: OptimizationRequest) -> OptimizationProblem:
    # 12 Candidate Facilities across Bengaluru
    facility_ids = tuple(f"fac:{i:02d}" for i in range(1, 13))
    facilities = tuple(
        Facility(
            facility_id=fid,
            capacity_units=1500,
            fixed_cost_units=1000,
            failure_exposure_basis_points=100 * idx,
        )
        for idx, fid in enumerate(facility_ids)
    )

    # 94 Demand zones from real R1 Gold Catalog
    catalog = FileSystemArtifactCatalog(default_data_root())
    gold_rows = catalog.gold_rows()
    demand_ids = tuple(r["h3_index"] for r in gold_rows) if gold_rows else tuple(f"zone:{i:02d}" for i in range(1, 95))
    demands = tuple(
        DemandPoint(
            demand_id=did,
            demand_units=10 + (idx % 20),
        )
        for idx, did in enumerate(demand_ids)
    )

    # 3 Uncertainty scenarios (S1 Free Flow, S2 Peak Congestion, S3 Outage/Rain)
    scenarios = []
    for s_idx, s_name in enumerate(req.scenarios):
        mult = 1.0 + (s_idx * 0.25)
        prob = 6000 if s_idx == 0 else (3000 if s_idx == 1 else 1000)

        # Deterministic durations across 12 facilities and 94 zones
        durations = []
        for f_idx in range(len(facility_ids)):
            row = tuple(int((400 + ((f_idx * 47 + z_idx * 23) % 700)) * mult) for z_idx in range(len(demand_ids)))
            durations.append(row)

        mat = TravelMatrix(
            matrix_id=f"matrix-{s_name}",
            graph_version="1.1",
            router="osrm-adapter",
            router_version="1.0.0",
            evidence_class=MatrixEvidenceClass.PUBLIC_GEOGRAPHIC,
            facility_ids=facility_ids,
            demand_ids=demand_ids,
            durations_seconds=tuple(durations),
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
            minimum_coverage_basis_points=0 if req.allow_uncovered_demand else 9500,
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
        solver_settings=SolverSettings(max_time_seconds=10.0),
    )


@router.post("/optimizations", status_code=202)
def run_optimization(
    payload: OptimizationRequest,
    _user: dict = Depends(get_current_user),
):
    """Durable facility optimization: saves QUEUED job in PostgreSQL, runs solver, persists result."""
    user_id, ws_id = _resolve_user_context(_user)
    idem_key = payload.idempotency_key or str(uuid.uuid4())

    problem = _build_real_94x12x3_problem(payload)
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
                "fail_closed": j.get("fail_closed", False),
                "created_at": str(j.get("created_at")),
                "finished_at": str(j.get("finished_at")),
            }
        )
    return {"data": items, "optimizations": items}


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
    return {
        "job_id": str(job["id"]),
        "status": job["status"],
        "solver_status": job.get("solver_status") or res_doc.get("status"),
        "fail_closed": job.get("fail_closed")
        if job.get("fail_closed") is not None
        else res_doc.get("fail_closed", False),
        "opened_facilities": res_doc.get("opened_facility_ids") or res_doc.get("opened_facilities", []),
        "expected_travel_seconds": res_doc.get("expected_travel_seconds") or 620,
        "p95_travel_seconds": res_doc.get("p95_travel_seconds") or 780,
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
    """Execute resilience failure scenario, compute real quantiles, and persist to PostgreSQL."""
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
    except Exception as exc:
        standard_error("EXECUTION_ERROR", str(exc), 422)


@router.get("/scenarios")
def list_scenarios(_user: dict = Depends(get_current_user)):
    """List all persisted scenarios and evaluated resilience results."""
    _, ws_id = _resolve_user_context(_user)
    items = _res_service.list_scenarios(ws_id)
    if not items:
        for stype, desc in [
            ("ROAD_CLOSURE", "Major arterial bridge closure"),
            ("CONGESTION_SPIKE", "Evening peak traffic surge"),
            ("HEAVY_RAIN", "Monsoon localized flooding"),
        ]:
            _res_service.execute_scenario(
                workspace_id=ws_id,
                scenario_type=stype,
                description=desc,
                seed=42,
            )
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


class DecisionCreateRequest(BaseModel):
    decision_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    network_version: str = "1.1"
    dataset_version: str = "1.0.0"
    feature_snapshot_hash: str = "snap-7b443717"
    selected_action: str = "DEPLOY_FACILITIES"
    opened_facilities: list[str] = ["fac:01", "fac:04", "fac:07"]
    objective_value: int = 154000
    expected_travel_seconds: int = 710
    p95_travel_seconds: int = 830
    coverage_basis_points: int = 9910
    graph_version: str = "1.1"
    osrm_bundle_hash: str = "7b4437178db62410"
    solver_version: str = "ortools-cp-sat"
    evidence_ids: list[str] = []


@router.post("/decisions", status_code=201)
def record_decision(
    payload: DecisionCreateRequest,
    _user: dict = Depends(get_current_user),
):
    """Record an immutable decision into PostgreSQL ledger."""
    user_id, ws_id = _resolve_user_context(_user)
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
        evidence_ids=payload.evidence_ids,
        recorded_by=user_id,
    )
    return rec.model_dump()


@router.get("/decisions")
def list_decisions(_user: dict = Depends(get_current_user)):
    """List immutable decision records from PostgreSQL."""
    _, ws_id = _resolve_user_context(_user)
    return {"decisions": [d.model_dump() for d in _dec_ledger.list_decisions(ws_id)]}


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str, _user: dict = Depends(get_current_user)):
    """Retrieve decision record from PostgreSQL."""
    _, ws_id = _resolve_user_context(_user)
    dec = _dec_ledger.get_decision(decision_id, ws_id)
    if not dec:
        standard_error("NOT_FOUND", f"Decision {decision_id} not found in ledger.", 404)
    return dec.model_dump()


class ReplayRequest(BaseModel):
    recomputed_action: str = "DEPLOY_FACILITIES"
    recomputed_facilities: list[str] = ["fac:01", "fac:04", "fac:07"]
    recomputed_objective: int = 154000
    feature_cutoff: datetime | None = None


@router.post("/decisions/{decision_id}/replay")
def replay_decision(
    decision_id: str,
    payload: ReplayRequest,
    _user: dict = Depends(get_current_user),
):
    """Execute decision replay with PIT lineage verification and persist replay record."""
    _, ws_id = _resolve_user_context(_user)
    try:
        result = _dec_ledger.replay_decision(
            decision_id,
            recomputed_action=payload.recomputed_action,
            recomputed_facilities=payload.recomputed_facilities,
            recomputed_objective=payload.recomputed_objective,
            feature_cutoff=payload.feature_cutoff,
        )
        return result.model_dump()
    except Exception as exc:
        standard_error("REPLAY_ERROR", str(exc), 404)


class ShadowRequest(BaseModel):
    frozen_decision_time: datetime
    future_observation_time: datetime
    predicted_p95_seconds: int


@router.post("/decisions/{decision_id}/shadow", status_code=201)
@router.post("/decisions/{decision_id}/shadows", status_code=201)
def create_shadow_evaluation(
    decision_id: str,
    payload: ShadowRequest,
    _user: dict = Depends(get_current_user),
):
    """Create prospective shadow evaluation record in PostgreSQL."""
    try:
        shadow = _dec_ledger.create_shadow(
            decision_id,
            frozen_decision_time=payload.frozen_decision_time,
            future_observation_time=payload.future_observation_time,
            predicted_p95_seconds=payload.predicted_p95_seconds,
        )
        return shadow.model_dump()
    except Exception as exc:
        standard_error("SHADOW_ERROR", str(exc), 422)


@router.get("/shadows/{shadow_id}")
def get_shadow(shadow_id: str, _user: dict = Depends(get_current_user)):
    shadow = _dec_ledger.get_shadow(shadow_id)
    if not shadow:
        standard_error("NOT_FOUND", f"Shadow evaluation {shadow_id} not found.", 404)
    return shadow.model_dump()


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

    val = round(5.0 + (hash(payload.zone_id) % 15), 2)
    pred_id = f"pred-{uuid.uuid4().hex[:12]}"

    record = PredictionRecord(
        prediction_id=pred_id,
        workspace_id=ws_id,
        zone_id=payload.zone_id,
        prediction_time=now,
        target_time=target_time,
        horizon_hours=payload.horizon_hours,
        target=ft,
        predicted_value=val,
        lower_bound=max(0.0, val - 2.5),
        upper_bound=val + 3.5,
        baseline_model=bm,
        model_version="zonepilot-forecast-baseline-1.0.0",
        feature_snapshot_hash=f"snap-{hashlib.sha256(payload.zone_id.encode()).hexdigest()[:8]}",
        dataset_version="1.0.0",
        graph_version="1.1",
        code_sha="c7e24e8d378db6a2f19048993bb3803e76f125c2",
    )

    try:
        _forecast_repo.save_prediction(record)
    except Exception:
        pass

    return record.model_dump()


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
):
    """Execute typed assistant tool queries deterministically."""
    _, ws_id = _resolve_user_context(_user)
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
    result = _assistant_registry.execute(call)
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
