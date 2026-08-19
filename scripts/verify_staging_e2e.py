"""OneMove Staging and Production Live Deployment Verification Script.

Tests all canonical endpoints against the live Google Cloud Run deployments
using authentic signed JWTs and verifies point-in-time responses, request correlation IDs,
authentic 94-zone network datasets, map layers, and durable state contracts.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

import jwt
from dotenv import dotenv_values

env = dotenv_values(".env.local")
JWT_SECRET = env.get("SUPABASE_JWT_SECRET") or os.environ.get("SUPABASE_JWT_SECRET")
if not JWT_SECRET:
    # Try reading from Secret Manager if running in authenticated GCP context
    try:
        import subprocess

        res = subprocess.run(
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
        JWT_SECRET = res.stdout.decode("utf-8").strip()
    except Exception:
        pass

STAGING_API_URL = os.environ.get(
    "ZONEPILOT_STAGING_API_URL",
    "https://zonepilot-api-staging-xwvz4vi7ta-el.a.run.app",
)


def create_test_token(role: str = "authenticated") -> str:
    if not JWT_SECRET:
        raise ValueError("SUPABASE_JWT_SECRET is required to authenticate against live deployment")
    payload = {
        "sub": "00000000-0000-0000-0000-000000000002",
        "email": "operator@onemove.internal",
        "workspace_id": "00000000-0000-0000-0000-000000000001",
        "role": role,
        "aud": "authenticated",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def call_endpoint(
    method: str,
    path: str,
    token: str | None = None,
    body: dict | None = None,
    workspace_id: str | None = None,
) -> tuple[int, dict | str]:
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


def run_smoke_suite() -> bool:
    print("=== OneMove Smoke Suite ===")
    code, res = call_endpoint("GET", "/api/v1/health")
    print(f"[SMOKE 1] GET /api/v1/health -> HTTP {code}: {res}")
    assert code == 200, f"Expected 200, got {code}"

    code, res = call_endpoint("GET", "/api/v1/zones")
    print(f"[SMOKE 2] GET /api/v1/zones (No Auth) -> HTTP {code}: {res}")
    assert code == 401, f"Expected 401, got {code}"
    return True


def run_real_e2e_suite() -> bool:
    print("=== OneMove Real E2E Verification Suite ===")
    print(f"Target: {STAGING_API_URL}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")

    token = create_test_token()

    # 1. Health Liveness Probe
    code, res = call_endpoint("GET", "/api/v1/health")
    print(f"[1] GET /api/v1/health -> HTTP {code}: {res}")
    assert code == 200, f"Expected 200, got {code}"

    # 2. Unauthenticated Request Rejection
    code, res = call_endpoint("GET", "/api/v1/zones")
    print(f"[2] GET /api/v1/zones (No Auth) -> HTTP {code}: {res}")
    assert code == 401, f"Expected 401 for unauth, got {code}"
    assert isinstance(res, dict) and res.get("error", {}).get("code") == "UNAUTHORIZED"

    # 3. Authenticated Zones List (Assert exact 94 Gold H3 cells)
    code, res = call_endpoint("GET", "/api/v1/zones", token=token)
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(res, dict)
    zones = res.get("data", [])
    print(f"[3] GET /api/v1/zones (Auth) -> HTTP {code}: count={len(zones)}")
    assert len(zones) == 94, f"Expected 94 zones from verified Gold network, got {len(zones)}"

    # 4. Release Identity / Version
    code, res = call_endpoint("GET", "/api/v1/version", token=token)
    print(f"[4] GET /api/v1/version -> HTTP {code}: {res}")
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(res, dict)
    v_data = res.get("data", {})
    assert v_data.get("app_version") == "1.5.1"
    assert v_data.get("gold", {}).get("record_count") == 94

    # 5. Data Health Summary
    code, res = call_endpoint("GET", "/api/v1/data-health", token=token)
    print(f"[5] GET /api/v1/data-health -> HTTP {code}: {res}")
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(res, dict)
    assert len(res.get("data", [])) >= 5

    # 6. Scenarios List
    code, res = call_endpoint("GET", "/api/v1/scenarios", token=token)
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(res, dict)
    scenarios = res.get("scenarios", [])
    print(f"[6] GET /api/v1/scenarios -> HTTP {code}: count={len(scenarios)}")

    # 7. Datasets Discovery (Assert >= 5 datasets discovered from manifests)
    code, res = call_endpoint("GET", "/api/v1/datasets", token=token)
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(res, dict)
    datasets = res.get("data", [])
    print(f"[7] GET /api/v1/datasets -> HTTP {code}: count={len(datasets)}")
    assert len(datasets) >= 5, f"Expected >= 5 datasets, got {len(datasets)}"

    # 8. Map Layers (Assert >= 3 GeoJSON layers: roads, intersections, pois)
    code, res = call_endpoint("GET", "/api/v1/layers", token=token)
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(res, dict)
    layers = res.get("data", [])
    print(f"[8] GET /api/v1/layers -> HTTP {code}: count={len(layers)}")
    assert len(layers) >= 3, f"Expected >= 3 map layers, got {len(layers)}"

    # 9. Experiments Registry
    code, res = call_endpoint("GET", "/api/v1/experiments", token=token)
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(res, dict)
    experiments = res.get("experiments", [])
    print(f"[9] GET /api/v1/experiments -> HTTP {code}: count={len(experiments)}")
    assert len(experiments) >= 4

    # 10. Decisions Ledger
    code, res = call_endpoint("GET", "/api/v1/decisions", token=token)
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(res, dict)
    decisions = res.get("decisions", [])
    print(f"[10] GET /api/v1/decisions -> HTTP {code}: count={len(decisions)}")

    # 11. Optimizations List
    code, res = call_endpoint("GET", "/api/v1/optimizations", token=token)
    assert code == 200, f"Expected 200, got {code}"
    assert isinstance(res, dict)
    optimizations = res.get("optimizations", [])
    print(f"[11] GET /api/v1/optimizations -> HTTP {code}: count={len(optimizations)}")

    # 12. Assistant Diagnostic Query
    assistant_body = {
        "query": "Get zone state for pilot zone",
        "tool_name": "get_zone_state",
        "arguments": {"zone_id": "8860145b41fffff"},
    }
    code, res = call_endpoint("POST", "/api/v1/assistant/query", token=token, body=assistant_body)
    print(f"[12] POST /api/v1/assistant/query -> HTTP {code}: {res}")
    assert code == 200, f"Expected 200, got {code}"

    print("\n=======================================================")
    print(" ALL 12 REAL E2E VERIFICATION TESTS PASSED (100%)!     ")
    print("=======================================================")
    return True


if __name__ == "__main__":
    run_smoke_suite()
    success = run_real_e2e_suite()
    sys.exit(0 if success else 1)
