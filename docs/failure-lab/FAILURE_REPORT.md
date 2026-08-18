# ZonePilot Adversarial Failure Lab Report

**Stream Owners**: X1 (Adversarial Destroyer) & X2 (Remediation & Non-Recurrence Engineer)  
**Program Base SHA**: `daf7ca5c222f80a84ec1ebd1f5b5c337e41a7fc1`  
**Status**: ACTIVE TRACKING & REMEDIATION

---

## 1. Executive Summary

This report documents vulnerabilities, architectural defects, and production-truth discrepancies identified during independent adversarial scrutiny. In accordance with the 17-Agent Mandate, no finding is closed merely upon a developer claim; every remediation requires independent replication, regression testing, and verification by X1/H3/H4.

---

## 2. Tracked Defect Inventory

| Defect ID | Severity | Component | Finding Summary | Remediation Stream | Status |
|:---|:---|:---|:---|:---|:---:|
| `P0-AUTH-001` | **P0** | Auth Middleware / `observatory.py` | `_resolve_user_context` defaulted to synthetic user/workspace on missing headers | H4 / X2 | **IN PROGRESS** |
| `P0/P1-TRUTH-001` | **P0** | Optimizer / `observatory.py` | Problem builder generated travel durations via mathematical formula instead of OSRM matrix | A1 / A3 / X2 | **IN PROGRESS** |
| `P1-TRUTH-002` | **P1** | GIS / Catalog | Fallback generated synthetic H3 cell IDs (`8861892...`) when Gold catalog missing | A1 / H5 / X2 | **IN PROGRESS** |
| `P1-TRUTH-003` | **P1** | Optimizer API | `get_optimization` returned hardcoded fallback metrics (620s expected, 780s p95) | A3 / X2 | **IN PROGRESS** |
| `P1-SCENARIO-001` | **P1** | Resilience API | `GET /api/v1/scenarios` mutated database by creating default scenarios | A4 / X2 | **IN PROGRESS** |
| `P1-DURABILITY-001` | **P1** | Decisions / Forecast Repo | Database connection failures swallowed and silently fell back to in-memory dict | A7 / X2 | **IN PROGRESS** |
| `P1-PIT-001` | **P1** | Decision Replay | Decision replay did not reconstruct snapshot lineage against temporal store | A7 / A2 / X2 | **IN PROGRESS** |
| `P1-RELEASE-001` | **P1** | Observability / API | Stale hardcoded Git commit SHAs (`c7e24e8d...`) embedded in runtime records | H1 / A6 / X2 | **IN PROGRESS** |
| `P1-ASYNC-001` | **P1** | Cloud / SRE / API | `POST /optimizations` ran long CP-SAT solver synchronously in HTTP request | A3 / A6 / X2 | **IN PROGRESS** |
| `P1-PERF-001` | **P1** | Optimizer Science | PR #30 attempted to reduce 94x12x3 to 24x6x3 and set p95=0 rather than optimizing CP-SAT | A3 / X2 | **REMEDIATED (PR #30 Closed)** |

---

## 3. Detailed Failure Profiles & Reproduction Steps

### P0-AUTH-001: Fail-Open User and Workspace Context
- **Vulnerability**: Unauthenticated callers to `/api/v1/zones`, `/api/v1/optimizations`, etc., were assigned default principal `00000000-0000-0000-0000-000000000001` and workspace `ws-pilot-default`.
- **Target Invariant**: Production APIs must fail closed with HTTP 401 Unauthorized or HTTP 403 Forbidden whenever auth credentials or workspace memberships are unverified.
- **Fix**: Require `get_current_user` and `get_workspace_principal` across all API routers. Reject missing contexts without fallback.

### P0/P1-TRUTH-001: Synthetic Routing Duration Matrix in Optimizer
- **Defect**: `_build_real_94x12x3_problem` used `(400 + ((f_idx * 47 + z_idx * 23) % 700)) * mult` to populate duration matrices.
- **Target Invariant**: Optimization problems must consume verified `TravelMatrix` artifacts produced by the OSRM routing engine over real OpenStreetMap Bengaluru road topology.
- **Fix**: Connect optimizer problem construction directly to the `TravelMatrix` catalog backed by the 94 H3 cell pilot area and real candidate facilities.

### P1-SCENARIO-001: Side-Effecting GET Endpoints
- **Defect**: Invoking `GET /api/v1/scenarios` when zero scenarios existed in the database triggered 3 insert operations.
- **Target Invariant**: GET requests must be strictly idempotent and side-effect free (RFC 9110).
- **Fix**: Return `{"data": [], "scenarios": []}` when empty; rely on explicit `POST /api/v1/scenarios` for execution.

### P1-DURABILITY-001: Silent In-Memory Fallback on DB Failure
- **Defect**: Repositories caught `psycopg.Error` and fell back to `_in_memory_jobs` / `_in_memory_decisions`.
- **Target Invariant**: Production database outages must fail closed with 503 `DATABASE_UNAVAILABLE`.
- **Fix**: Eliminate all runtime in-memory dictionaries outside unit test mocks.

---

## 4. Verification Protocol

1. **X1 Exploitation Attempt**: Execute automated test reproducing each condition against the live API.
2. **X2 Fix Validation**: Verify code change removes the defect.
3. **Non-Recurrence Test**: Merge dedicated regression test into test suite.
4. **H3 / H4 Sign-Off**: Confirm QA and security approval.
