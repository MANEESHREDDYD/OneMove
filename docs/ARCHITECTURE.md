# ZonePilot Technical Architecture

## 1. System Overview

ZonePilot is a deterministic spatial decision platform designed for urban logistics network optimization, multi-scenario resilience stress testing, and Point-In-Time auditable decision replay.

```
+-------------------------------------------------------------------------+
|                       Observatory Frontend (Next.js)                    |
|  /network | /optimize | /resilience | /decisions | /replay | /evidence   |
+------------------------------------+------------------------------------+
                                     | Authenticated HTTPS / Proxy
                                     v
+-------------------------------------------------------------------------+
|                        FastAPI Operational Gateway                      |
|       - Request ID / Telemetry Middleware                               |
|       - Supabase JWT Verification & Tenancy Principal Resolution        |
|       - Rate Limiting & Audit Logging                                   |
+----------+-------------------+-------------------+----------------------+
           |                   |                   |
           v                   v                   v
+--------------------+ +-------------------+ +----------------------------+
|  CP-SAT Optimizer  | | Resilience Engine | | Decision Ledger & Replay   |
|  - 94x12x3 Network | | - Network Breaker | | - Point-In-Time Verification|
|  - Tie-Breaking    | | - Latency P50/95  | | - Prospective Shadows      |
|  - Pareto Analysis | | - Exposure Index  | | - Exact Reproducibility    |
+----------+---------+ +---------+---------+ +--------------+-------------+
           |                     |                          |
           +---------------------+--------------------------+
                                 |
                                 v
+-------------------------------------------------------------------------+
|                       PostgreSQL 15 (Supabase Hosted)                   |
|  Tables: optimization_jobs, optimization_results, resilience_scenarios, |
|          resilience_results, decision_records, decision_replays,        |
|          shadow_evaluations, weather_observations, workspaces           |
+-------------------------------------------------------------------------+
```

## 2. Spatial Partitioning & Network Domain
- **Grid Topology:** 94 Uber H3 Resolution 8 spatial cells covering Bengaluru Urban core.
- **Lineage Verification:** Every zone is anchored to verified OpenStreetMap geometries and Uber H3 spatial indexes.
- **Facility Candidates:** 12 geographically distributed candidate locations (`fac:01` to `fac:12`).

## 3. Mathematical Optimization (R3)
- **Engine:** Google OR-Tools CP-SAT integer programming solver.
- **Multi-Scenario Uncertainty:** Formulated across 3 simultaneous scenarios:
  1. `s1_free_flow` (Base velocity conditions).
  2. `s2_congested` (Peak travel inflation).
  3. `s3_congested_outage` (Peak traffic compound with facility outage).
- **Determinism:** Strict lexicographical tie-breaking over candidate facility sets ensures bitwise-identical outputs on repeated solves.

## 4. Multi-Tenant Tenancy Model
- Every request resolves a trusted `WorkspacePrincipal` from the server-side database.
- RLS policies and table constraints ensure strict cross-workspace data isolation.
