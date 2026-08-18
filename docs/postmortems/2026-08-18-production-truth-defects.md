# Incident Postmortem: ZonePilot Production-Truth & Optimization Defects

**Incident Reference**: `INC-20260818-PROD-TRUTH`  
**Severity**: P0 / P1  
**Owner**: X2 (Remediation & Non-Recurrence Engineer)  
**Date**: 2026-08-18  
**Status**: RESOLVED & VERIFIED  

---

## 1. Summary
Following independent adversarial review, multiple production-truth gaps were identified in `main`:
1. **P0-AUTH-001**: `_resolve_user_context` in `observatory.py` defaulted unauthenticated requests to a synthetic user and workspace ID rather than failing closed (401/403).
2. **P0/P1-TRUTH-001**: The optimizer problem builder constructed routing duration matrices via a synthetic modulo formula rather than consuming the authentic OSRM travel matrix.
3. **P1-SCENARIO-001**: `GET /api/v1/scenarios` exhibited side-effects by mutating the database with default scenarios when empty.
4. **P1-PERF-001**: PR #30 attempted to achieve subsecond test speeds by weakening the business problem to 24x6x3 and setting `p95_travel=0`.
5. **P1-RELEASE-001**: Stale commit SHAs were hardcoded into models and repositories.

---

## 2. Root Cause Analysis
- **Auth**: The endpoint helper `_resolve_user_context` contained fallback defaults (`sub or "00000000-..."`) from early prototype code.
- **Routing Matrix**: The Observatory router had an inline placeholder formula rather than binding to `FileSystemArtifactCatalog` and `r1_osrm_travel_matrix.json`.
- **Optimization**: The mixed-integer CP-SAT solver performed multiple unnecessary sequential solves for each non-tied candidate variable, causing slow solves on full problem sizes.
- **REST Semantics**: The scenarios list handler had an auto-seed fallback that executed database insertions on GET.

---

## 3. Remediations & Non-Recurrence Controls
1. **Strict Auth Enforcement**: Replaced `_resolve_user_context` with fail-closed validation rejecting empty or malformed tokens.
2. **Authentic OSRM Travel Matrix**: Precomputed and versioned `data_root/private/official/gold/r1_osrm_travel_matrix.json` (12x94) from real Bengaluru road graph and linked directly into problem generation.
3. **True 94x12x3 CP-SAT Optimization**: Preserved the full problem dimensions (94 demand zones x 12 facilities x 3 scenarios) and non-zero `p95_travel=1000`. Closed PR #30. Proved optimality on CP-SAT within standard worker budget.
4. **Side-Effect-Free GET Endpoints**: Removed state mutation from `GET /api/v1/scenarios`.
5. **Dynamic Release Tracking**: Introduced `services/zonepilot/release.py` to resolve live commit SHAs from runtime environments.

---

## 4. Verification Evidence
- **Pytest Full Suite**: 263 passed, 0 failed, 56 skipped.
- **12 Observatory Routes**: 12 passed, 0 failed (`tests/api/test_all_12_observatory_routes.py`).
- **Remote R0 Execution**: Runs `32159814401` (SUCCESS, 4512 records) and `32160021761` (SKIPPED_NO_CHANGE, idempotent) verified.
