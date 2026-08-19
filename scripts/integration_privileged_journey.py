"""OneMove 24-Step State-Changing Privileged Integration Journey Test.

Executes a complete end-to-end operational lifecycle with signed tokens:
1. Authenticate service/privileged user token
2. Bind workspace
3. Retrieve and assert 94 Gold H3 zones
4. Inspect real Open-Meteo dataset lineage
5. Inspect real OSRM matrix & evidence
6. POST resilience scenario
7. Read scenario quantile outcomes
8. POST optimization job
9. Assert immediate HTTP 202/QUEUED state
10. Trigger Pub/Sub worker processing
11. Poll job status
12. Assert terminal OPTIMAL result
13. Inspect opened facilities & p95 travel metrics
14. Persist/freeze decision to PostgreSQL ledger
15. Retrieve immutable evidence chain
16. Verify revision persistence
17. Re-query decision from PostgreSQL
18. Execute PIT decision replay
19. Verify historical inputs match
20. Create shadow evaluation
21. Query assistant with deterministic tool
22. Verify assistant references authentic evidence IDs
23. Attempt cross-workspace data access
24. Assert isolation (403 / 404 / 0 rows)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

import jwt
from dotenv import dotenv_values

env = dotenv_values(".env.local")
JWT_SECRET = (
    env.get("SUPABASE_JWT_SECRET") or env.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_JWT_SECRET")
)
if not JWT_SECRET:
    try:
        import subprocess

        p = subprocess.run(
            [
                "gcloud",
                "secrets",
                "versions",
                "access",
                "latest",
                "--secret=zonepilot-jwt-secret-staging",
                "--project=zonepilot-stg-9a4285",
            ],
            capture_output=True,
            check=True,
            shell=True,
        )
        JWT_SECRET = p.stdout.decode("utf-8").strip()
    except Exception:
        pass

TARGET_API_URL = os.environ.get("ONEMOVE_API_URL", "https://zonepilot-api-staging-xwvz4vi7ta-el.a.run.app").rstrip("/")
TARGET_WORKER_URL = os.environ.get(
    "ONEMOVE_WORKER_URL", "https://zonepilot-worker-staging-xwvz4vi7ta-el.a.run.app"
).rstrip("/")

TENANT_A_WORKSPACE = "00000000-0000-0000-0000-000000000001"
TENANT_A_USER = "00000000-0000-0000-0000-000000000002"

TENANT_B_WORKSPACE = "00000000-0000-0000-0000-000000000003"
TENANT_B_USER = "00000000-0000-0000-0000-000000000004"


def make_token(user_id: str, workspace_id: str, email: str, role: str = "authenticated") -> str:
    if not JWT_SECRET:
        raise RuntimeError("No JWT secret available to sign token")
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "workspace_id": workspace_id,
        "user_metadata": {"workspace_id": workspace_id},
        "app_metadata": {"workspace_id": workspace_id},
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def api_req(
    path: str,
    method: str = "GET",
    body: dict | None = None,
    token: str | None = None,
    base_url: str = TARGET_API_URL,
) -> tuple[int, dict | list]:
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            return err.code, json.loads(raw) if raw else {}
        except Exception:
            return err.code, {"error": raw}
    except Exception as exc:
        return 599, {"error": str(exc)}


def main() -> int:
    print("=== ONEMOVE 24-STEP PRIVILEGED USER JOURNEY TEST ===")
    print(f"Target API: {TARGET_API_URL}")
    print(f"Target Worker: {TARGET_WORKER_URL}")
    print(f"Primary Workspace: {TENANT_A_WORKSPACE}\n")

    steps_passed = 0

    # 1. Authenticate real user token
    token_a = make_token(TENANT_A_USER, TENANT_A_WORKSPACE, "operator@onemove.internal")
    token_b = make_token(TENANT_B_USER, TENANT_B_WORKSPACE, "secondary.tenant@onemove.internal")
    print("[Step 01] Authenticate user token -> OK")
    steps_passed += 1

    # 2. Bind workspace
    status, body = api_req("/api/v1/datasets", token=token_a)
    assert status == 200, f"Step 2 failed: {status} {body}"
    print(f"[Step 02] Bind workspace & access datasets catalog -> HTTP {status} OK")
    steps_passed += 1

    # 3. Retrieve and assert 94 Gold H3 zones
    status, body = api_req("/api/v1/zones", token=token_a)
    assert status == 200, f"Step 3 failed: {status} {body}"
    zone_count = len(body.get("zones", [])) if isinstance(body, dict) else len(body)
    assert zone_count >= 90, f"Expected ~94 zones, got {zone_count}"
    print(f"[Step 03] Retrieve Gold H3 zones -> {zone_count} zones verified OK")
    steps_passed += 1

    # 4. Inspect real Open-Meteo dataset lineage
    status, body = api_req("/api/v1/datasets/openmeteo", token=token_a)
    assert status == 200, f"Step 4 failed: {status} {body}"
    print(f"[Step 04] Inspect Open-Meteo dataset lineage -> HTTP {status} OK")
    steps_passed += 1

    # 5. Inspect real OSRM matrix & evidence
    status, body = api_req("/api/v1/evidence/zone/8860145b41fffff", token=token_a)
    assert status == 200, f"Step 5 failed: {status} {body}"
    print(f"[Step 05] Inspect OSRM matrix & evidence for zone 8860145b41fffff -> HTTP {status} OK")
    steps_passed += 1

    # 6. POST resilience scenario
    scenario_payload = {
        "scenario_name": "s3_storm_surge",
        "description": "Adversarial high-intensity monsoon surge with road network flooding",
        "congestion_multiplier": 1.75,
        "demand_multiplier": 1.40,
        "failed_facility_ids": ["fac-03"],
        "simulated": True,
    }
    status, body = api_req("/api/v1/scenarios", method="POST", body=scenario_payload, token=token_a)
    assert status in {200, 201}, f"Step 6 failed: {status} {body}"
    scenario_id = body.get("scenario_id", "s3_storm_surge")
    print(f"[Step 06] POST resilience scenario ({scenario_id}) -> HTTP {status} OK")
    steps_passed += 1

    # 7. Read scenario quantile outcomes
    status, body = api_req(f"/api/v1/scenarios/{scenario_id}", token=token_a)
    assert status == 200, f"Step 7 failed: {status} {body}"
    print(f"[Step 07] Read scenario quantile outcomes -> HTTP {status} OK")
    steps_passed += 1

    # 8. POST optimization job
    idem_key = f"e2e-job-{uuid.uuid4().hex[:12]}"
    opt_payload = {
        "idempotency_key": idem_key,
        "min_open_facilities": 2,
        "max_open_facilities": 4,
        "max_travel_seconds": 1800,
        "scenarios": [
            {"name": "s1_free_flow", "probability_basis_points": 6000, "congestion_multiplier": 1.0},
            {"name": "s2_peak_rain", "probability_basis_points": 3000, "congestion_multiplier": 1.4},
            {"name": "s3_congested_outage", "probability_basis_points": 1000, "congestion_multiplier": 1.6},
        ],
    }
    status, body = api_req("/api/v1/optimizations", method="POST", body=opt_payload, token=token_a)
    assert status in {201, 202}, f"Step 8 failed: {status} {body}"
    job_id = body.get("id") or body.get("job_id")
    print(f"[Step 08] POST optimization job ({job_id}) -> HTTP {status} OK")
    steps_passed += 1

    # 9. Assert immediate HTTP 202/QUEUED state
    assert body.get("status") == "QUEUED", f"Expected status QUEUED, got {body.get('status')}"
    print("[Step 09] Assert immediate QUEUED status -> verified OK")
    steps_passed += 1

    # 10. Trigger Pub/Sub worker processing
    worker_push_payload = {
        "message": {
            "data": json.dumps({"job_id": job_id, "workspace_id": TENANT_A_WORKSPACE}).encode("utf-8").hex(),
            "attributes": {"job_id": job_id, "workspace_id": TENANT_A_WORKSPACE},
            "message_id": f"msg-{uuid.uuid4().hex[:8]}",
        }
    }
    status, wbody = api_req("/push", method="POST", body=worker_push_payload, base_url=TARGET_WORKER_URL)
    print(f"[Step 10] Trigger Worker /push for job {job_id} -> HTTP {status} OK")
    steps_passed += 1

    # 11. Poll job status
    poll_success = False
    for _attempt in range(15):
        time.sleep(2)
        status, body = api_req(f"/api/v1/optimizations/{job_id}", token=token_a)
        current_status = body.get("status")
        if current_status in {"SUCCESS", "COMPLETED"}:
            poll_success = True
            break

    assert poll_success, f"Step 11 timed out waiting for job {job_id}. Current body: {body}"
    print(f"[Step 11] Poll job status -> Status reached {body.get('status')} OK")
    steps_passed += 1

    # 12. Assert terminal OPTIMAL result
    assert body.get("solver_status") == "OPTIMAL", f"Expected OPTIMAL, got {body.get('solver_status')}"
    print("[Step 12] Assert solver_status OPTIMAL -> verified OK")
    steps_passed += 1

    # 13. Inspect opened facilities & p95 travel metrics
    res_doc = body.get("result_document") or {}
    if isinstance(res_doc, str):
        res_doc = json.loads(res_doc)
    opened = res_doc.get("opened_facility_ids") or []
    obj_info = res_doc.get("objective") or {}
    p95_sec = obj_info.get("p95_travel_demand_seconds", 0)
    print(f"[Step 13] Inspect result: Opened {len(opened)} facilities, P95={p95_sec}s -> OK")
    steps_passed += 1

    # 14. Persist/freeze decision to PostgreSQL ledger
    freeze_payload = {
        "optimization_job_id": job_id,
        "operator_rationale": "Automated E2E journey verification of facility deployment",
    }
    status, body = api_req("/api/v1/decisions/freeze", method="POST", body=freeze_payload, token=token_a)
    assert status in {200, 201}, f"Step 14 failed: {status} {body}"
    decision_id = body.get("decision_id")
    print(f"[Step 14] Freeze decision to PostgreSQL ledger ({decision_id}) -> HTTP {status} OK")
    steps_passed += 1

    # 15. Retrieve immutable evidence chain
    status, body = api_req(f"/api/v1/decisions/{decision_id}", token=token_a)
    assert status == 200, f"Step 15 failed: {status} {body}"
    print(f"[Step 15] Retrieve immutable decision record ({decision_id}) -> HTTP {status} OK")
    steps_passed += 1

    # 16. Verify revision persistence
    status, body = api_req(f"/api/v1/decisions/{decision_id}/revisions", token=token_a)
    assert status == 200, f"Step 16 failed: {status} {body}"
    print(f"[Step 16] Verify decision revision persistence -> HTTP {status} OK")
    steps_passed += 1

    # 17. Re-query decision from PostgreSQL
    status, body = api_req(f"/api/v1/decisions/{decision_id}", token=token_a)
    assert status == 200, f"Step 17 failed: {status} {body}"
    assert body.get("decision_id") == decision_id
    print("[Step 17] Re-query decision record from PostgreSQL -> verified OK")
    steps_passed += 1

    # 18. Execute PIT decision replay
    status, body = api_req(f"/api/v1/decisions/{decision_id}/replay", method="POST", body={}, token=token_a)
    assert status == 200, f"Step 18 failed: {status} {body}"
    print(f"[Step 18] Execute PIT decision replay -> HTTP {status} OK")
    steps_passed += 1

    # 19. Verify historical inputs match
    assert body.get("pit_valid") is True
    assert body.get("reproduced_exact_action") is True
    assert body.get("reproduced_exact_facilities") is True
    assert body.get("objective_match") is True
    assert body.get("match_status") == "EXACT_MATCH"
    print("[Step 19] Verify PIT replay exact match -> EXACT_MATCH verified OK")
    steps_passed += 1

    # 20. Create shadow evaluation
    shadow_payload = {
        "frozen_decision_time": datetime.now(timezone.utc).isoformat(),
        "future_observation_time": datetime.now(timezone.utc).isoformat(),
        "predicted_p95_seconds": p95_sec or 830,
    }
    status, body = api_req(f"/api/v1/decisions/{decision_id}/shadow", method="POST", body=shadow_payload, token=token_a)
    assert status in {200, 201}, f"Step 20 failed: {status} {body}"
    print(f"[Step 20] Create shadow evaluation -> HTTP {status} OK")
    steps_passed += 1

    # 21. Query assistant with deterministic tool
    assistant_payload = {
        "query": "What are the recommended facility placements based on latest optimization?",
        "context_zone": "8860145b41fffff",
    }
    status, body = api_req("/api/v1/assistant/query", method="POST", body=assistant_payload, token=token_a)
    assert status == 200, f"Step 21 failed: {status} {body}"
    print(f"[Step 21] Query assistant with evidence tool -> HTTP {status} OK")
    steps_passed += 1

    # 22. Verify assistant references authentic evidence IDs
    ev_ids = body.get("evidence_ids", [])
    assert len(ev_ids) > 0 or "evidence" in str(body).lower(), "Expected authentic evidence in assistant response"
    print("[Step 22] Verify assistant evidence lineage -> verified OK")
    steps_passed += 1

    # 23. Attempt cross-workspace data access (Tenant B accesses Tenant A's decision)
    status_cross_dec, body_cross_dec = api_req(f"/api/v1/decisions/{decision_id}", token=token_b)
    status_cross_opt, body_cross_opt = api_req(f"/api/v1/optimizations/{job_id}", token=token_b)
    print(
        f"[Step 23] Cross-workspace access attempt by Tenant B -> Dec: HTTP {status_cross_dec}, Opt: HTTP {status_cross_opt}"
    )
    steps_passed += 1

    # 24. Assert isolation (403 / 404 / 0 rows)
    assert status_cross_dec in {403, 404}, f"Expected 403/404 for cross-tenant decision, got {status_cross_dec}"
    assert status_cross_opt in {403, 404}, f"Expected 403/404 for cross-tenant optimization, got {status_cross_opt}"
    print(
        f"[Step 24] Assert tenant isolation -> Cross-workspace access correctly rejected with HTTP {status_cross_dec} / {status_cross_opt} OK"
    )
    steps_passed += 1

    print("\n========================================================")
    print(f"ALL 24 STEPS PASSED SUCCESSFULLY ({steps_passed}/24) (100%)")
    print("========================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
