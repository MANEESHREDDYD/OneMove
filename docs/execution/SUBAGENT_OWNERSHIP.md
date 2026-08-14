# Subagent Ownership

| Agent | Branch | Worktree | Owned Paths | Read-only Dependencies | Expected Outputs | Tests | Dependency Gate | Status |
|-------|--------|----------|-------------|------------------------|------------------|-------|-----------------|--------|
| 1. CI Repair | `ws/phase1-measurement` | `.` | `*/**/*.py` | None | Python formatting fixes | `pytest`, `ruff` | None | DONE |
| 2. R0.5 DB/Security | `ws/phase1-measurement` | `.` | `supabase/migrations/*`, `db.py` | None | Local Least-Privilege Role | `test_rls_execution` | None | DONE |
| 3. OSM Pipeline | `ws/phase1-measurement` | `.` | `services/collectors/context/osm.py` | Geofabrik Metadata | Pilot Corridor PBF, Node Count | Execution | None | IN_PROGRESS |
| 4. OSRM Benchmark | `ws/phase1-measurement` | `.` | `services/routing/osrm_pipeline.py` | Agent 3 Pilot PBF | OSRM matrix, graph size | Execution | Agent 3 | PENDING |
| 7. Backend API | `ws/phase1-measurement` | `.` | `services/api/*` | None | FastAPI routes | `pytest` | None | PENDING |
| 8. Frontend | `ws/phase1-measurement` | `.` | `frontend/*` | Agent 7 API Specs | Next.js screens | Jest | None | PENDING |
| 9. Auth/Security | `ws/phase1-measurement` | `.` | `services/api/auth.py` | None | Auth tests | `pytest` | None | PENDING |
| 10. Observability | `ws/phase1-measurement` | `.` | `services/api/health.py` | None | Structured logs, health API | `pytest` | None | PENDING |
