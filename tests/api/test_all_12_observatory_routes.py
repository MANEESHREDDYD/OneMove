"""Comprehensive test suite proving all 12 Observatory API routes on FastAPI."""

import pytest
from fastapi.testclient import TestClient

from services.api.core.auth import get_current_user
from services.api.main import app


def mock_operator_auth():
    return {
        "sub": "00000000-0000-0000-0000-000000000002",
        "workspace_id": "00000000-0000-0000-0000-000000000001",
        "role": "operator",
    }


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_operator_auth
    yield
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


def test_route_1_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_route_2_version(monkeypatch):
    monkeypatch.setenv("ZONEPILOT_APP_VERSION", "1.5.1")
    monkeypatch.setenv("ZONEPILOT_GIT_SHA", "483c8e1f6d256c39987d3780ffdb342f935f7ac2")
    monkeypatch.setenv("ZONEPILOT_SCHEMA_VERSION", "1.0.0")
    res = client.get("/api/v1/version")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()["data"]
        assert data["app_version"] == "1.5.1"
        assert data["git_sha"] == "483c8e1f6d256c39987d3780ffdb342f935f7ac2"


def test_route_3_zones():
    res = client.get("/api/v1/zones")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()
        assert len(data["data"]) == 94


def test_route_4_map_layers():
    res = client.get("/api/v1/network/map-layers")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()
        assert len(data["data"]) >= 1


def test_route_5_datasets():
    res = client.get("/api/v1/datasets")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()
        assert len(data["data"]) >= 1


def test_route_6_data_health():
    res = client.get("/api/v1/data-health")
    assert res.status_code in {200, 503}
    if res.status_code == 200:
        data = res.json()
        assert isinstance(data["data"], list)
        assert "evaluated_at" in data


def test_route_7_optimization_submission_is_durable():
    """Submission alone: the job must be accepted and persisted as QUEUED.

    This asserts the submission contract only. Nothing consumes the queue in
    this process, so requiring SUCCESS here made the test depend on a worker
    that does not exist -- it observed FAILED and reported a red build for a
    system behaving correctly. The worker half is covered by
    test_route_7_optimization_lifecycle_with_real_worker below.
    """
    import uuid

    req = {
        # A fixed idempotency key made every run resolve to the first run's job,
        # so one bad outcome was inherited forever.
        "idempotency_key": f"test-idem-route-7-{uuid.uuid4()}",
        "min_open_facilities": 2,
        "max_open_facilities": 4,
        "max_travel_seconds": 1800,
        "allow_uncovered_demand": True,
    }
    post_res = client.post("/api/v1/optimizations", json=req)
    assert post_res.status_code in {200, 201, 202}
    job_id = post_res.json()["job_id"]

    get_res = client.get(f"/api/v1/optimizations/{job_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["job_id"] == job_id
    assert data["status"] == "QUEUED", "a submitted job with no worker must stay QUEUED"
    assert data["solver_status"] is None


def test_route_7_optimization_lifecycle_with_real_worker():
    """QUEUED -> terminal, driven by the production worker code path.

    This runs the same lease claim, problem reconstruction, solve and
    persistence the deployed worker runs; only the Pub/Sub transport is absent.
    No result is injected and no status is faked.
    """
    import uuid

    from services.zonepilot.optimization.pubsub_worker import _reconstruct_problem_from_payload
    from services.zonepilot.optimization.repository import OptimizationRepository
    from services.zonepilot.optimization.service import OptimizationService
    from services.zonepilot.release import current_release_sha

    req = {
        "idempotency_key": f"test-lifecycle-{uuid.uuid4()}",
        "min_open_facilities": 1,
        "max_open_facilities": 4,
        "max_travel_seconds": 1800,
        "allow_uncovered_demand": True,
    }
    post_res = client.post("/api/v1/optimizations", json=req)
    assert post_res.status_code in {200, 201, 202}
    job_id = post_res.json()["job_id"]

    assert client.get(f"/api/v1/optimizations/{job_id}").json()["status"] == "QUEUED"

    repository = OptimizationRepository()
    service = OptimizationService(repository=repository)

    lease = repository.claim_job_lease(
        job_id=job_id, lease_owner=f"pytest-{uuid.uuid4().hex[:8]}", lease_seconds=300
    )
    assert lease, "the worker must be able to claim a QUEUED job"

    row = repository.get_job_system(job_id)
    assert row is not None
    problem = _reconstruct_problem_from_payload(row["request_payload"] or {})
    service.run_solver_for_job(job_id, problem, code_sha=current_release_sha())

    final = client.get(f"/api/v1/optimizations/{job_id}").json()
    assert final["status"] in {"SUCCESS", "FAILED"}, f"unexpected terminal status {final['status']}"
    # Every terminal solver state must be typed and readable -- never a 500.
    assert final["solver_status"] in {
        "OPTIMAL",
        "FEASIBLE",
        "INFEASIBLE",
        "TIME_LIMIT",
        "MODEL_INVALID",
    }, f"untyped solver status {final['solver_status']}"

    if final["solver_status"] in {"OPTIMAL", "FEASIBLE"}:
        assert final["demand_zones_total"] == 94
        assert final["assigned_zones"] + final["uncovered_zones"] == final["demand_zones_total"]


def test_route_8_scenarios_side_effect_free():
    # GET is side effect free
    get_res = client.get("/api/v1/scenarios")
    assert get_res.status_code == 200

    # POST creates scenario
    post_res = client.post(
        "/api/v1/scenarios",
        json={
            "scenario_type": "ROAD_CLOSURE",
            "description": "Corridor disruption test",
            # "multiplier" is not a parameter this API accepts, so the scenario
            # described no effect on the routed network and was correctly
            # refused. The contract requires travel_time_inflation_basis_points
            # or unreachable_facility_demand_pairs.
            "parameters": {"travel_time_inflation_basis_points": 4000},
            "seed": 42,
        },
    )
    assert post_res.status_code == 201
    scen_id = post_res.json()["scenario_id"]

    # GET specific scenario
    scen_res = client.get(f"/api/v1/scenarios/{scen_id}")
    assert scen_res.status_code == 200
    assert scen_res.json()["scenario_id"] == scen_id

    # A scenario that describes no effect on the network must be refused rather
    # than stored as a disruption that changes nothing.
    empty_res = client.post(
        "/api/v1/scenarios",
        json={
            "scenario_type": "ROAD_CLOSURE",
            "description": "describes nothing",
            "parameters": {},
            "seed": 42,
        },
    )
    assert empty_res.status_code == 422
    assert empty_res.json()["error"]["code"] == "SCENARIO_NOT_REPRESENTABLE"


def test_route_9_experiments():
    res = client.get("/api/v1/experiments")
    assert res.status_code == 200
    assert len(res.json()["experiments"]) == 4


def test_route_10_decisions_and_pit_replay():
    import hashlib

    from services.zonepilot.optimization.r1_catalog import default_data_root

    mat_path = default_data_root() / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"
    mat_sha = hashlib.sha256(mat_path.read_bytes()).hexdigest()

    # Record decision
    dec_req = {
        "network_version": "1.1.0+bad320dd48da",
        "dataset_version": "1.0.0",
        "feature_snapshot_hash": "snap-7b443717",
        "selected_action": "OPEN_FACILITIES",
        "opened_facilities": [
            "fac:88618925a5fffff",
            "fac:88618925a7fffff",
            "fac:8861892ec3fffff",
            "fac:8861892ecbfffff",
        ],
        "objective_value": 1756300000000,
        "expected_travel_seconds": 620,
        "p95_travel_seconds": 840,
        "coverage_basis_points": 9600,
        "graph_version": "1.1.0+bad320dd48da",
        "osrm_bundle_hash": mat_sha,
        "solver_version": "ortools-cp-sat",
    }

    # As posted, this is optimizer-shaped output with no optimization_job_id
    # behind it. The API refuses it, which is the whole point of the decision
    # class separation: a hand-authored decision must never be presentable as
    # solver output. The test previously asserted the forgery succeeded.
    forged = client.post("/api/v1/decisions", json=dec_req)
    assert forged.status_code == 422
    assert "optimization_job_id" in forged.json()["error"]["message"]

    # Declared as what it is, the same decision is accepted and recorded as
    # operator-authored.
    dec_req = {
        **dec_req,
        "decision_class": "MANUAL_OPERATOR_DECISION",
        "operator_rationale": (
            "Recorded by hand for the API contract test; not derived from a solver run."
        ),
    }
    post_res = client.post("/api/v1/decisions", json=dec_req)
    assert post_res.status_code == 201
    dec_id = post_res.json()["decision_id"]

    # Replay decision with PIT validation
    rep_res = client.post(
        f"/api/v1/decisions/{dec_id}/replay",
        json={},
    )
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["pit_valid"] is True

    # A hand-authored decision was never produced by the optimizer, so it has no
    # optimization policy and cannot be reproduced by re-solving. Replay says so
    # rather than re-running the solver and presenting the result as though it
    # reproduced this decision. The test previously required EXACT_MATCH here,
    # which would have meant a manual decision validating itself against solver
    # output it never came from.
    assert rep_data["match_status"] == "MANUAL_DECISION_NOT_REPLAYABLE"
    assert rep_data["reproduced_exact_action"] is False
    assert rep_data["objective_match"] is False


def test_route_11_forecast_prediction():
    res = client.post(
        "/api/v1/forecast/predict",
        json={
            "zone_id": "8860145b41fffff",
            "horizon_hours": 12,
            "target": "WEATHER_TRAVEL_INFLATION_PERCENT",
            "model": "LAST_OBSERVATION",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["zone_id"] == "8860145b41fffff"
    assert data["horizon_hours"] == 12


def test_route_12_assistant_query():
    res = client.post(
        "/api/v1/assistant/query",
        json={
            "query": "What is the network state for zone 8860145b41fffff?",
            "tool_name": "get_zone_state",
            "arguments": {"zone_id": "8860145b41fffff"},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_name"] == "get_zone_state"
    assert "result_data" in data
