# ZonePilot Regression Test Matrix

**Owner**: X2 (Remediation & Non-Recurrence Engineer)  
**Verification**: H3 (Independent QA) & H4 (Security)

| Failure ID | Affected Component | Dedicated Regression Test | CI Gate Suite | Status |
|:---|:---|:---|:---|:---:|
| `P0-AUTH-001` | Auth Dependency / Tenancy | `tests/api/test_auth.py::test_unauthenticated_request_rejected` | `Python CI` | **ENFORCED** |
| `P0/P1-TRUTH-001` | Routing Evidence / TravelMatrix | `tests/evidence/test_r1_evidence.py::test_osrm_matrix_consumed_by_optimizer` | `ZonePilot R1 Evidence` | **ENFORCED** |
| `P1-TRUTH-002` | H3 Gold Catalog | `tests/geo/test_pilot_roads_lineage.py::test_gold_h3_indices_authentic` | `Python CI` | **ENFORCED** |
| `P1-TRUTH-003` | Optimization Metrics API | `tests/api/test_durable_optimization_api.py::test_no_hardcoded_metric_fallbacks` | `Python CI` | **ENFORCED** |
| `P1-SCENARIO-001` | Resilience Scenarios API | `tests/api/test_resilience_scenario_api.py::test_get_scenarios_side_effect_free` | `Python CI` | **ENFORCED** |
| `P1-DURABILITY-001` | Database Fail-Closed Policy | `tests/api/test_fault_injection.py::test_db_outage_fails_closed_without_memory_leak` | `Python CI` | **ENFORCED** |
| `P1-PIT-001` | Decision Lineage & Replay | `tests/decisions/test_decision_ledger.py::test_pit_replay_verifies_information_available_at` | `Python CI` | **ENFORCED** |
| `P1-RELEASE-001` | Dynamic Commit SHA Tracking | `tests/execution/test_program_state.py::test_runtime_records_use_live_commit_sha` | `Python CI` | **ENFORCED** |
| `P1-ASYNC-001` | Asynchronous Job Queue | `tests/api/test_durable_optimization_api.py::test_async_job_queue_and_worker_lease` | `Python CI` | **ENFORCED** |
| `P1-PERF-001` | Full 94x12x3 CP-SAT Formulation | `tests/api/test_real_solver_job_execution.py::test_real_solver_execution_94x12x3_optimal` | `Python CI` | **ENFORCED** |
