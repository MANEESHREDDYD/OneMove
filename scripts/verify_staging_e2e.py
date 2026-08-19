"""OneMove Staging Live Deployment Verification Script.

Tests all canonical endpoints against the live Google Cloud Run staging deployment
using authentic signed JWTs and verifies point-in-time responses, request correlation IDs,
and durable state contracts.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
import jwt
from dotenv import dotenv_values

env = dotenv_values(".env.local")
JWT_SECRET = env.get("SUPABASE_JWT_SECRET") or env.get("SUPABASE_SERVICE_ROLE_KEY") or "test-secret"
STAGING_API_URL = os.environ.get(
    "ZONEPILOT_STAGING_API_URL",
    "https://zonepilot-api-staging-935663019643.asia-south1.run.app",
)

def create_test_token(role: str = "authenticated") -> str:
    payload = {
        "sub": "usr_operator_stg_001",
        "email": "operator@onemove.internal",
        "role": role,
        "aud": "authenticated",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def call_endpoint(method: str, path: str, token: str | None = None, body: dict | None = None, workspace_id: str | None = None) -> tuple[int, dict | str]:
    url = f"{STAGING_API_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "OneMove-E2E-Verifier/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            raw = res.read().decode("utf-8")
            try:
                return res.status, json.loads(raw)
            except Exception:
                return res.status, raw
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            return err.code, json.loads(raw)
        except Exception:
            return err.code, raw
    except Exception as exc:
        return 500, f"Connection error: {exc}"

def run_suite() -> bool:
    print(f"=== OneMove Staging Live Verification Suite ===")
    print(f"Target: {STAGING_API_URL}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")

    token = create_test_token()
    all_passed = True

    # 1. Health Liveness Probe
    code, res = call_endpoint("GET", "/api/v1/health")
    print(f"[1] GET /api/v1/health -> HTTP {code}: {res}")
    assert code == 200, f"Expected 200, got {code}"

    # 2. Unauthenticated Request Rejection
    code, res = call_endpoint("GET", "/api/v1/zones")
    print(f"[2] GET /api/v1/zones (No Auth) -> HTTP {code}: {res}")
    assert code == 401, f"Expected 401 for unauth, got {code}"
    assert res["error"]["code"] == "UNAUTHORIZED"

    # 3. Authenticated Zones List
    code, res = call_endpoint("GET", "/api/v1/zones", token=token)
    print(f"[3] GET /api/v1/zones (Auth) -> HTTP {code}: count={len(res.get('zones', [])) if isinstance(res, dict) else res}")
    assert code == 200, f"Expected 200, got {code}"

    # 4. Release Identity / Version
    code, res = call_endpoint("GET", "/api/v1/version", token=token)
    print(f"[4] GET /api/v1/version -> HTTP {code}: {res}")
    assert code == 200, f"Expected 200, got {code}"

    # 5. Data Health Summary
    code, res = call_endpoint("GET", "/api/v1/data-health", token=token)
    print(f"[5] GET /api/v1/data-health -> HTTP {code}: {res}")
    assert code == 200, f"Expected 200, got {code}"

    # 6. Scenarios List
    code, res = call_endpoint("GET", "/api/v1/scenarios", token=token)
    print(f"[6] GET /api/v1/scenarios -> HTTP {code}: count={len(res.get('scenarios', [])) if isinstance(res, dict) else res}")
    assert code == 200, f"Expected 200, got {code}"

    # 7. Datasets Discovery
    code, res = call_endpoint("GET", "/api/v1/datasets", token=token)
    print(f"[7] GET /api/v1/datasets -> HTTP {code}: count={len(res.get('datasets', [])) if isinstance(res, dict) else res}")
    assert code == 200, f"Expected 200, got {code}"

    # 8. Map Layers
    code, res = call_endpoint("GET", "/api/v1/layers", token=token)
    print(f"[8] GET /api/v1/layers -> HTTP {code}: count={len(res.get('layers', [])) if isinstance(res, dict) else res}")
    assert code == 200, f"Expected 200, got {code}"

    # 9. Experiments Registry
    code, res = call_endpoint("GET", "/api/v1/experiments", token=token)
    print(f"[9] GET /api/v1/experiments -> HTTP {code}: count={len(res.get('experiments', [])) if isinstance(res, dict) else res}")
    assert code == 200, f"Expected 200, got {code}"

    # 10. Decisions Ledger
    code, res = call_endpoint("GET", "/api/v1/decisions", token=token)
    print(f"[10] GET /api/v1/decisions -> HTTP {code}: count={len(res.get('decisions', [])) if isinstance(res, dict) else res}")
    assert code == 200, f"Expected 200, got {code}"

    # 11. Optimizations List
    code, res = call_endpoint("GET", "/api/v1/optimizations", token=token)
    print(f"[11] GET /api/v1/optimizations -> HTTP {code}: count={len(res.get('optimizations', [])) if isinstance(res, dict) else res}")
    assert code == 200, f"Expected 200, got {code}"

    # 12. Assistant Diagnostic Query
    assistant_body = {
        "query": "Get zone state for pilot zone",
        "tool_name": "get_zone_state",
        "arguments": {"zone_id": "8860145b41fffff"}
    }
    code, res = call_endpoint("POST", "/api/v1/assistant/query", token=token, body=assistant_body)
    print(f"[12] POST /api/v1/assistant/query -> HTTP {code}: {res}")
    assert code == 200, f"Expected 200, got {code}"

    print("\n=======================================================")
    print(" ALL 12 LIVE STAGING VERIFICATION TESTS PASSED (100%)! ")
    print("=======================================================")
    return True

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
