# Phase 1: Execution Gate

## 1. Goal
Complete and verify Phase 1 (Measurement System & Infrastructure) of the ZonePilot study, demonstrating real-world data collection, offline PWA synchronization, API isolation, and RLS governance without real persistent data destruction.

## 2. Evidence of Completion

### 2.1 Backend / API Governance (FastAPI + Supabase)
- **RLS Verification**: Executed automated scripts (`tests/api/test_rls_execution.py`) verifying that the role `study_participant` can only `INSERT` into `volunteer_order_events` with their own `participant_id`, but cannot `SELECT`, `UPDATE`, or `DELETE`.
- **API JWT Injection**: Validated integration of Supabase client JWT injection via FastAPI middleware/dependency in `services/api/core/auth.py`.

### 2.2 Frontend PWA Offline Sync (Next.js)
- **Requirement:** PWA must buffer observations when offline and correctly synchronize them when connectivity returns via the Next.js API to FastAPI to Supabase flow.
- **Verification:** Completed via Playwright (`tests/e2e/offline.spec.ts`).
- **Result:** `PASS`.
  - The script sets the browser to offline using Playwright's network conditions.
  - The observation is captured and persisted locally in IndexedDB using `idb-keyval`.
  - The test then simulates coming back online and triggering the `window.addEventListener('online')` hook, which flushes the `syncOutbox`.
  - Direct database querying confirms the record (`PROBE` event) was successfully synced to `volunteer_order_events` with the correct payload `{"etaLow": "20"}`.

### 2.3 Bengaluru Configuration
- Switched default internal models and candidate queries from Hyderabad to `Bengaluru`.
- Updated base protocols and constraints to reference Bengaluru constraints.

## 3. Deviations & Blockers
- **TomTom Traffic API**: Blocked due to missing credentials. Fallback to `DisabledTrafficProvider` is implemented.
- **Offline Module Loading**: Found that dynamic imports (`import()`) fail when offline due to chunk loading failures, requiring static imports.

## 4. Next Steps
- Commit working branch `ws/phase1-measurement`.
- Proceed to Phase 2 (Experimental Design & Simulation).
