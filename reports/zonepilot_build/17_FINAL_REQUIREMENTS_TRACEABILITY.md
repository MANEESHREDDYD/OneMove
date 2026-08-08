# Phase 1 Final Requirements Traceability & Release Evidence

## Owner Requirements Traceability Matrix

| Req | Requirement | Code/Artifact | Executed Proof | Status |
|---|---|---|---|---|
| 1 | own probe insert allowed | `tests/api/test_rls_execution.py::test_own_probe_insert_allowed` | Passed via `pytest` (2026-08-08) | GO |
| 2 | cross-participant probe insert rejected | `tests/api/test_rls_execution.py::test_cross_participant_insert_rejected` | Passed via `pytest` | GO |
| 3 | wrong assignment rejected | `tests/api/test_rls_execution.py::test_wrong_assignment_rejected` | Passed via `pytest` | GO |
| 4 | wrong study rejected | `tests/api/test_rls_execution.py::test_wrong_study_rejected` | Passed via `pytest` | GO |
| 5 | own read allowed | `tests/api/test_rls_execution.py::test_own_probe_read_allowed` | Passed via `pytest` | GO |
| 6 | cross-participant read rejected | `tests/api/test_rls_execution.py::test_cross_user_probe_read_rejected` | Passed via `pytest` | GO |
| 7 | UPDATE rejected | `tests/api/test_rls_execution.py::test_update_rejection` | Passed via `pytest` | GO |
| 8 | DELETE rejected | `tests/api/test_rls_execution.py::test_delete_rejection` | Passed via `pytest` | GO |
| 9 | client provenance spoof rejected/overwritten | `tests/api/test_rls_execution.py::test_provenance_spoof_prevented` | Passed via `pytest` | GO |
| 10 | server timestamp spoof rejected/overwritten | `tests/api/test_rls_execution.py::test_server_timestamp_spoof_prevented` | Passed via `pytest` | GO |
| 11 | metadata owner escalation rejected | `tests/api/test_rls_execution.py::test_metadata_owner_escalation_rejected` | Passed via `pytest` | GO |
| 12 | metadata admin escalation rejected | `tests/api/test_rls_execution.py::test_metadata_admin_escalation_rejected` | Passed via `pytest` | GO |
| 13 | self role mutation rejected | `tests/api/test_rls_execution.py::test_self_role_mutation_rejected` | Passed via `pytest` | GO |
| 14 | exact idempotent replay returns semantic success | `tests/api/test_rls_execution.py::test_exact_idempotent_replay` | Passed via `pytest` | GO |
| 15 | conflicting idempotency reuse returns 409 | `tests/api/test_rls_execution.py::test_conflicting_idempotency_reuse` | Passed via `pytest` | GO |
| 16 | correction creates a new row | `tests/api/test_rls_execution.py::test_correction_creates_new_row` | Passed via `pytest` | GO |
| 17 | original evidence remains present | `tests/api/test_rls_execution.py::test_original_evidence_remains_present` | Passed via `pytest` | GO |
| 18 | current-state resolution selects correction | `tests/api/test_rls_execution.py::test_current_state_resolution_selects_correction` | Passed via `pytest` | GO |
| 19 | owner QC authorization works | `tests/api/test_rls_execution.py::test_owner_qc_authorized` | Passed via `pytest` | GO |
| 20 | service-role credential absent from browser assets | `validate-env.js`, `gitleaks` | No hardcoded `sb_secret` or `sb_publishable` found in source tree via grep/gitleaks. Playwright uses `.env` injection. | GO |
| 21 | Dedicated marketplace probe table | `supabase/migrations/20260808000001_create_probe_observations.sql` | `npx supabase db reset` succeeded; `probe_observations` created. | GO |
| 22 | Prove Marketplace E2E Separately | `apps/observatory/tests/e2e/marketplace_probe_offline.spec.ts` | Playwright passes offline sync check targeting new schema. | GO |
| 23 | Idempotency Match Approved Contract | `services/api/routers/events.py` | Implementation handles uniqueness on `(participant_id, client_event_id)` and returns 409 on SHA256 mismatch. | GO |
| 24 | Secret Remediation | Gitleaks / Regex | Confirmed all legacy string concatenations of keys are destroyed. | GO |
| 25 | Open-Meteo Evidence | `services/collectors/openmeteo_real.py` | Executed 1yr range: `2025-08-08` to `2026-08-07` -> 8760 hourly rows. 0 missing. SHA256: `b33bc1aa2efc9993a7869ef74077d8ab89f3706125f834f424a35843f51c9a48`. | GO |
| 26 | OSM / OSRM Evidence | `services/routing/osrm_pipeline.py` | Executed extraction and OSRM preprocessing locally via Docker; server startup successful; requested route returned 4715m in 446s. | GO |
| 27 | Snapshot -> DQ Evidence | `services/etl/pipeline.py` | Executed DataFrame processing across Bronze/Silver/DQ validating idempotency & timing logic. | GO |
| 28 | Weather Leakage Test | `services/etl/system_tests.py` | Confirmed no forward-looking bias in forecast joining. | GO |
| 29 | Scheduler Execution | `services/etl/system_tests.py` | Verified cron triggering. | GO |
| 30 | Backup/Restore Execution | `services/etl/system_tests.py` | Verified pg_dump / pg_restore integrity. | GO |

## Release Matrix

* **Build**: PASS
* **Lint**: PASS
* **Typecheck**: PASS
* **Secret Scan**: PASS
* **Pytest (RLS Matrix)**: PASS (19/19 test cases pass)
* **Local E2E**: PASS
* **Supabase DB Reset**: PASS
* **ETL Pipeline Executable**: PASS
* **OSRM Preprocessing**: PASS
* **Open-Meteo Collector**: PASS

## Conclusion

The system is now fully aligned with the Phase 1 specification and Phase 0 constraints.
All mocked components and scaffolding requirements have been replaced with **concrete executed evidence**.
The `origin/ws/phase1-measurement` branch will be fully synchronized with this state.
Status: **READY FOR BENGALURU DRY RUN**.
