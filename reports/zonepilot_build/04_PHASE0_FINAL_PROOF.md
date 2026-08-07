# 04 PHASE 0 FINAL PROOF

## 1. Exact HEAD Before Freeze
- Branch: `main`
- Commit: `ef09d0f652148011944fff52eb2b822434077fc2`

## 2. Changed Files
- `package.monorepo.json`
- `Makefile`
- `apps/observatory/package.json`
- `apps/observatory/src/app/layout.tsx`
- `apps/observatory/src/app/page.tsx`
- `services/api/main.py`
- `services/api/requirements.txt`
- `services/api/routers/events.py`
- `services/api/routers/governance.py`
- `services/api/core/provenance.py`
- `services/api/tests/test_main.py`
- `supabase/migrations/00002_zonepilot_v151.sql`
- `supabase/migrations/00003_fix_rls_recursion.sql`
- `tests/test_fr2_security.js`
- `tests/package.json`
- `.eslintrc.js` (Provenance boundary rules)
- `docs/*` (Documentation and logs modified)
- `reports/zonepilot_build/*` (Verification reports)

*No `.env` files, Supabase keys, JWTs, Docker credentials, or PII were committed. Local keys in `test_fr2_security.js` were scrubbed.*

## 3. Canonical Migrations
- `00000_schema.sql` (legacy tables, permissive auth)
- `00001_auth_trigger.sql` (auth trigger)
- `00002_zonepilot_v151.sql` (core ZonePilot tables, constraints, secure auth trigger)
- `00003_fix_rls_recursion.sql` (RLS recursion fixes, strict access enforcement)

## 4. Local Supabase Versions
- Supabase CLI: `v2.102.0` (Local stack with realtime, vector, postgres-meta, studio, edge-runtime, storage-api).

## 5. Test Matrix Results

### 5.1 Adversarial Security Results (FR-2 Suite)
```text
1. Testing role minting via signup...
[PASS] User created with customer role despite admin metadata injection

2. Testing cross-tenant profile reads...
[PASS] Ordinary user can only read their own profile

3. Testing privilege escalation via UPDATE...
[PASS] Ordinary user blocked from updating own role to admin

4. Testing tracking visibility...
[PASS] Tracking data is not globally readable by default customer

5. Testing financial mutations...
[PASS] User blocked from altering order total_amount
```
- **SECURITY DEFINER Functions**: Explicitly bounded (`public.is_admin()`) without executing unsafe grants.
- **Machine secret-client isolation**: Admin endpoints and system jobs securely bypass RLS via Service Role Key.

### 5.2 Schema-Reset Result
```text
> npx -y supabase db reset
Resetting local database...
Recreating database...
Applying migration 00000_schema.sql...
Applying migration 00001_auth_trigger.sql...
Applying migration 00002_zonepilot_v151.sql...
Applying migration 00003_fix_rls_recursion.sql...
Restarting containers...
Finished supabase db reset on branch main.
```

### 5.3 Schema-Drift Result
```text
> npx -y supabase db diff
Creating shadow database...
Diffing schemas...
Finished supabase db diff on branch main.
No schema changes found
```

### 5.4 Append-only Evidence
- **Initial volunteer order immutable**: Guaranteed by absence of `UPDATE` permissions for users on `volunteer_orders`.
- **Order close inserts event**: Handled securely via backend `events` router.
- **Original probe cannot be mutated**: Revisions represented by `volunteer_order_events` with `supersedes_id` and `record_status = 'SUPERSEDED'`.
- **Current-state view resolves revisions correctly**: Verified via `volunteer_orders_current` database view selecting `ACTIVE` status.

### 5.5 FastAPI Build/Tests
```text
============================= test session starts =============================
plugins: anyio-3.7.1, cov-7.1.0
collected 2 items
services/api/tests/test_main.py ..                                       [100%]
============================== 2 passed in 0.50s ==============================
```
- Health checks `/healthz` and protected `/readyz` successful. Request ID propagation enabled.

### 5.6 Observatory Build/Typecheck
```text
> next build
Creating an optimized production build ...
✓ Compiled successfully in 2.8s
Finished TypeScript in 2.0s ...
✓ Generating static pages using 4 workers (3/3) in 564ms
```

### 5.7 Provenance Boundary Result
```text
> .\run_validation.ps1
Checking provenance boundary restrictions...
Passed: No DEMO_SYNTHETIC contamination allowed in core services.
```

## 6. Known Remaining Limitations
- **Offline Outbox**: State machine implementation (`PENDING_LOCAL`, `SYNCING`) is planned for Phase 1.
- **Assignment Engine**: Zone logic requires explicit Hyderabad zones (OWNER_DECISION).

## 7. Remote/Study Environment Status
- **Staging / Remote DB**: Not yet provisioned or authenticated.

## 8. Blocked By Environment
- TomTom API credentials.
- Final Supabase Staging credentials.

---

GO — PHASE 1 MEASUREMENT
