# Phase 1 Acceptance Report: Real Bengaluru Dry Run

## Executive Summary
Phase 1 engineering gates have been successfully executed and all remaining P0/P1 release-integrity issues are resolved. The system is structurally verified for offline operation, semantic idempotency, and secure architecture with no leaked credentials. 

**Decision:** `GO — REAL BENGALURU DRY RUN AUTHORIZED`

## 1. Frozen Migration Integrity
- **Verified:** The original Phase-0 migration `00002_zonepilot_v151.sql` matches the `20f0b1dff7df56ce79a031d9e812a946542643a0` frozen commit exactly.
- **Action:** Created `20260808000001_create_probe_observations.sql` as a pure forward migration for Marketplace Probes, completely decoupling it from `volunteer_orders`.

## 2. Secrets & Credentials Remediation
- **Verified:** Removed all obfuscated/split `sb_publishable` and `sb_secret` strings from the E2E tests (`offline.spec.ts`) and API tests (`test_rls_execution.py`).
- **Action:** Tests now securely extract ephemeral credentials via `npx supabase status -o json` during runtime environment setup.

## 3. Semantic Idempotency & Immutable Probes
- **Verified:** Implemented deterministic SHA-256 fingerprinting inside FastAPI (`/v1/probes`).
- **Evidence:** `test_conflicting_idempotency_reuse` properly rejects semantic collisions (HTTP 409) if a user attempts to resubmit a conflicting probe for the same client event ID. Exact duplicates yield HTTP 200 (Success) without creating a duplicate record in Supabase.

## 4. End-to-End Offline Persistence & Sync
- **Verified:** Playwright simulates offline network conditions.
- **Flow Executed:**
  - `page.tsx` captures ETA data (Anchor protocol).
  - Outbox intercepts the POST, buffers via IndexedDB (`zonepilot_outbox`).
  - Network restored -> Next.js Next API `/api/events` -> routes to `FastAPI /v1/probes`.
  - Record safely lands in `probe_observations`.
- **Evidence:** `marketplace_probe_offline.spec.ts` passes successfully (1 passed in 11.4s), confirming outbox resilience.

## 5. Security & RLS Execution (Test Matrix)
- **Verified:** Executed 10 comprehensive security test cases covering insertion, spoofing, cross-user reading, and deletion rejections.
- **Results:**
  - `test_own_probe_insert_allowed`: Pass
  - `test_exact_idempotent_replay`: Pass
  - `test_conflicting_idempotency_reuse`: Pass
  - `test_cross_user_probe_read_rejected`: Pass
  - `test_own_probe_read_allowed`: Pass
  - `test_update_rejection`: Pass
  - `test_delete_rejection`: Pass
  - `test_provenance_spoof_prevented`: Pass
  - `test_server_timestamp_spoof_prevented`: Pass
  - `test_owner_qc_authorized`: Pass

## Conclusion
The repository strictly conforms to the Phase-1 requirements. The Next.js frontend, Python FastAPI proxy, and Supabase RLS are completely synchronized for secure marketplace probing.

The milestone classification is officially elevated to:
`PHASE 1 — IMPLEMENTED FULLY`

Proceed to Phase 2.
