# ZonePilot Test Strategy

## 1. Test Pyramid Architecture

```
        /  Browser E2E (Playwright)  \
       /   Persistent Profile Offline \
      /--------------------------------\
     /   Integration & RLS Test Suite   \
    /   PostgREST / FastAPI / System     \
   /--------------------------------------\
  /        Unit & Property Test Suite      \
 /  Vitest / Pytest / Schemas / Idempotency \
/--------------------------------------------\
```

## 2. Test Execution Layers

- **Unit Tests**:
  - `tests/api/test_auth.py`: Cryptographic JWT verification, signature tampering, expired token rejection, wrong issuer/audience checks.
  - `python/tests/test_data_quality.py`: Schema validation, range checks, protocol validation.
- **System & Pipeline Tests**:
  - `services/etl/system_tests.py`: Weather point-in-time leakage, scheduler job idempotency, physical backup/restore verification, and `DRY_RUN` exclusion.
- **Database & RLS Integration Tests**:
  - `tests/api/test_rls_execution.py`: Verified multi-tenant isolation, cross-study assignment boundaries, and view security.
- **Browser E2E Tests**:
  - `apps/observatory/tests/e2e/marketplace_probe_offline.spec.ts`: Marketplace probe persistent profile offline persistence, process restart, reconnect, and single DB row assertion.
  - `apps/observatory/tests/e2e/volunteer_order_offline.spec.ts`: Volunteer order offline persistence, process restart, reconnect, and single `volunteer_order_events` row assertion.
