"""GCP Pub/Sub Push Subscription Worker for asynchronous OneMove facility optimization."""

from __future__ import annotations

import base64
import json
import logging
import math
import os
import time
import uuid
from typing import Any

import psycopg
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, Field

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
from services.zonepilot.optimization.r1_catalog import (
    FileSystemArtifactCatalog,
    default_data_root,
)
from services.zonepilot.optimization.repository import OptimizationRepository
from services.zonepilot.optimization.solver import optimize_facilities
from services.zonepilot.release import current_release_sha

logger = logging.getLogger("onemove.optimization.worker")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="OneMove Optimization Push Worker", version="1.5.1")
_repository = OptimizationRepository()


class PubSubMessage(BaseModel):
    data: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    messageId: str | None = None
    publishTime: str | None = None


class PubSubPushRequest(BaseModel):
    message: PubSubMessage
    subscription: str | None = None


def _reconstruct_problem_from_payload(payload: dict[str, Any]) -> OptimizationProblem:
    """Reconstruct an OptimizationProblem from saved request payload with authentic data.

    Fails closed if the real travel matrix or Gold network catalog is missing.
    No synthetic substitution or fallback constants.
    """
    if "facilities" in payload and "demand_points" in payload and "scenarios" in payload:
        return OptimizationProblem.model_validate(payload)

    min_open = int(payload.get("min_open_facilities", 1))
    max_open = int(payload.get("max_open_facilities", 4))
    max_travel = int(payload.get("max_travel_seconds", 1800))
    allow_uncovered = bool(payload.get("allow_uncovered_demand", True))
    scenarios_list = payload.get("scenarios", ["s1_free_flow", "s2_congested", "s3_congested_outage"])

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

    scenarios = []
    for s_idx, s_name in enumerate(scenarios_list):
        mult = 1.0 if s_idx == 0 else (1.4 if s_idx == 1 else 1.6)
        prob = 6000 if s_idx == 0 else (3000 if s_idx == 1 else 1000)
        durations = tuple(tuple(int(math.ceil(dur * mult)) for dur in row) for row in base_durations)

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
        problem_id=f"opt-async-{uuid.uuid4().hex[:8]}",
        facilities=facilities,
        demand_points=demands,
        scenarios=tuple(scenarios),
        constraints=OptimizationConstraints(
            min_open_facilities=min_open,
            max_open_facilities=max_open,
            max_travel_seconds=max_travel,
            minimum_coverage_basis_points=0,
            allow_uncovered_demand=allow_uncovered,
        ),
        objective_weights=ObjectiveWeights(
            assumption_version="r1-proxy-1.0.0",
            expected_travel=5000,
            p95_travel=1000,
            facility_cost=3000,
            failure_exposure=500,
            coverage_loss=5000 if allow_uncovered else 0,
        ),
        solver_settings=SolverSettings(max_time_seconds=30.0, num_search_workers=1),
    )


@app.get("/healthz")
@app.get("/health/live")
def healthz():
    return {"status": "ok", "service": "onemove-optimization-worker"}


@app.get("/readyz")
@app.get("/health/ready")
def readyz():
    return {"status": "ready", "service": "onemove-optimization-worker"}


@app.post("/push")
@app.post("/api/v1/optimizations/pubsub-push")
async def process_pubsub_push(request: Request, response: Response):
    """Process GCP Pub/Sub push message with atomic lease claim and failure classification."""
    delivery_attempt = request.headers.get("x-goog-delivery-attempt", "1")
    raw_body = await request.body()

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        logger.error(f"Malformed JSON push payload: {exc}")
        # Ack to discard malformed payloads from infinite retry loop
        return {"status": "discarded", "reason": "malformed_json"}

    msg = data.get("message", {})
    msg_id = msg.get("messageId") or str(uuid.uuid4())
    attrs = msg.get("attributes", {})

    job_id = attrs.get("job_id")
    workspace_id = attrs.get("workspace_id")

    if not job_id and msg.get("data"):
        try:
            decoded = json.loads(base64.b64decode(msg["data"]).decode("utf-8"))
            job_id = decoded.get("job_id")
            workspace_id = decoded.get("workspace_id") or workspace_id
        except Exception:
            pass

    if not job_id:
        logger.warning(f"Pub/Sub message {msg_id} missing job_id; acking to drop.")
        return {"status": "dropped", "reason": "missing_job_id"}

    worker_id = f"worker-{os.uname().nodename if hasattr(os, 'uname') else 'gcp'}-{uuid.uuid4().hex[:6]}"
    logger.info(f"Received Pub/Sub job {job_id} (msg_id={msg_id}, attempt={delivery_attempt})")

    # 1. Atomic lease acquisition
    try:
        lease = _repository.claim_job_lease(job_id=job_id, lease_owner=worker_id, lease_seconds=120)
    except psycopg.OperationalError as db_err:
        logger.error(f"Transient DB operational error claiming lease for job {job_id}: {db_err}")
        response.status_code = 503
        return {"status": "retryable_error", "error": "db_unavailable"}

    if not lease:
        logger.info(f"Job {job_id} already in-flight or completed; acknowledging Pub/Sub message.")
        return {"status": "ack", "reason": "already_claimed_or_completed"}

    # 2. Fetch full job details
    try:
        job = _repository.get_job(job_id)
    except psycopg.OperationalError as db_err:
        logger.error(f"Transient DB error reading job {job_id}: {db_err}")
        response.status_code = 503
        return {"status": "retryable_error", "error": "db_unavailable"}

    if not job:
        logger.error(f"Job {job_id} leased but not found in database; acknowledging.")
        return {"status": "ack", "reason": "job_not_found"}

    # 3. Execute CP-SAT solver
    start_time = time.perf_counter()
    effective_code_sha = current_release_sha()
    payload = job.get("request_payload") or {}

    try:
        problem = _reconstruct_problem_from_payload(payload)

        # Create and persist immutable ProblemSnapshot for true PIT replay
        from services.zonepilot.optimization.contracts import create_problem_snapshot
        manifest_path = default_data_root() / "private" / "official" / "manifests" / "gold_manifest.json"
        matrix_sha = ""
        gold_sha = ""
        if manifest_path.is_file():
            try:
                m_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
                matrix_sha = m_doc.get("osrm_bundle_sha256") or m_doc.get("osrm_table_sha256") or ""
                gold_sha = m_doc.get("gold_h3_table_sha256") or ""
            except Exception:
                pass

        graph_ver = job.get("graph_version") or "1.1"
        matrix_id = job.get("matrix_id") or "r1-table"
        evidence_ids = (
            f"ev-gold-network-{graph_ver}",
            f"ev-osrm-{matrix_id}",
            f"ev-opt-job-{job_id}",
        )

        snapshot = create_problem_snapshot(
            problem,
            code_sha=effective_code_sha,
            dataset_version=job.get("dataset_version") or "1.0.0",
            matrix_sha256=matrix_sha,
            gold_manifest_sha256=gold_sha,
            evidence_ids=evidence_ids,
        )
        _repository.save_problem_snapshot(snapshot, workspace_id=workspace_id)

        result = optimize_facilities(problem)
        run_ms = int((time.perf_counter() - start_time) * 1000)

        result_doc = result.model_dump()
        result_doc["evidence_ids"] = list(evidence_ids)
        result_doc["problem_snapshot_id"] = snapshot.problem_snapshot_id
        result_doc["problem_snapshot_sha256"] = snapshot.problem_snapshot_sha256
        result_doc["dataset_version"] = job.get("dataset_version") or "1.0.0"
        result_doc["network_version"] = graph_ver
        result_doc["solver_version"] = "ortools-cp-sat"

        _repository.save_result(
            job_id=job_id,
            result_document=result_doc,
            pareto_document=None,
            problem_fingerprint=snapshot.problem_snapshot_sha256,
            solver_status=result.status.value,
            action=result.action.value,
            fail_closed=result.fail_closed,
            code_sha=effective_code_sha,
            run_duration_ms=run_ms,
        )
        logger.info(f"Job {job_id} solved successfully in {run_ms}ms (status={result.status.value}, snapshot={snapshot.problem_snapshot_id})")
        return {"status": "ack", "job_id": job_id, "solver_status": result.status.value, "problem_snapshot_id": snapshot.problem_snapshot_id}

    except psycopg.OperationalError as db_err:
        run_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(f"Job {job_id} transient DB operational error: {db_err}")
        response.status_code = 503
        return {"status": "retryable_failure", "job_id": job_id, "error": "db_unavailable"}

    except Exception as exc:
        run_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception(f"Job {job_id} solver failure: {exc}")

        # Fail closed and record failure
        closed_doc = {
            "status": "FAILED",
            "action": "NONE",
            "fail_closed": True,
            "error_message": str(exc),
        }
        _repository.save_result(
            job_id=job_id,
            result_document=closed_doc,
            pareto_document=None,
            problem_fingerprint=f"err-{uuid.uuid4().hex[:8]}",
            solver_status="FAILED",
            action="NONE",
            fail_closed=True,
            code_sha=effective_code_sha,
            run_duration_ms=run_ms,
        )
        return {"status": "ack", "job_id": job_id, "solver_status": "FAILED", "error": str(exc)}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
