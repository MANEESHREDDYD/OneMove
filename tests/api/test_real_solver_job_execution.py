"""Tests proving real OR-Tools CP-SAT solver execution over 94x12x3 network."""

import time
import uuid

from services.api.routers.observatory import OptimizationRequest, _build_real_94x12x3_problem
from services.zonepilot.optimization.service import OptimizationService


def test_real_solver_execution_94x12x3():
    idem_key = f"test-solve-real-{uuid.uuid4().hex[:8]}"
    req = OptimizationRequest(
        idempotency_key=idem_key,
        min_open_facilities=2,
        max_open_facilities=4,
        max_travel_seconds=1800,
        allow_uncovered_demand=True,
    )
    problem = _build_real_94x12x3_problem(req)
    assert len(problem.facilities) == 6
    assert len(problem.scenarios) == 3
    assert len(problem.demand_points) == 24

    service = OptimizationService()
    start_time = time.perf_counter()
    job = service.submit_optimization(
        requested_by="00000000-0000-0000-0000-000000000001",
        workspace_id="ws-test-real-solve",
        idempotency_key=idem_key,
        problem=problem,
    )
    solve_duration = time.perf_counter() - start_time

    assert job["status"] == "SUCCESS"
    assert job["solver_status"] == "OPTIMAL"
    assert not job["fail_closed"]
    assert solve_duration < 30.0

    res_doc = job.get("result_document")
    assert res_doc is not None
    assert 2 <= len(res_doc["opened_facility_ids"]) <= 4
    assert len(res_doc["scenario_metrics"]) == 3
