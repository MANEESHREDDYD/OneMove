# OneMove — Canonical API Contract

**API Version**: `1.5.1`  
**Base Path**: `/api/v1`  
**Internal Engine Namespace**: `zonepilot`  
**Authentication**: Bearer JWT (Strict Fail-Closed, 401/403)  
**Required Request Headers**:
- `Authorization: Bearer <token>`
- `X-Workspace-Id: <workspace-uuid>`
- `X-Request-Id: <request-uuid>` (Optional, server generates if missing)

## Endpoints

### 1. Observatory & System Status
- `GET /health/live` — Liveness check. Returns `{"status": "live", "timestamp": "<ISO>"}`.
- `GET /health/ready` — Readiness check. Returns `{"status": "ready", "database": "connected"}`.
- `GET /api/v1/version` — Release identity and commit SHAs.
- `GET /api/v1/observatory/summary` — High-level network summary metrics.
- `GET /api/v1/observatory/data-health` — Real-world telemetry and data freshness audit.

### 2. Network & Geography
- `GET /api/v1/observatory/network` — 94 H3 Resolution-8 demand zones and 12 candidate facilities.
- `GET /api/v1/observatory/route-matrix` — OSRM precomputed duration matrix with provenance hash.

### 3. Scenario & Resilience
- `GET /api/v1/scenarios` — List persisted disruption scenarios (side-effect free).
- `POST /api/v1/scenarios` — Create and persist a new disruption scenario.
- `GET /api/v1/scenarios/{id}/resilience` — Compute tail latency percentiles (P50, P90, P95) and network failure grade.

### 4. Optimization Engine
- `POST /api/v1/optimizations` — Enqueue 94x12x3 CP-SAT facility allocation job.
- `GET /api/v1/optimizations/{id}` — Poll job status (`QUEUED`, `RUNNING`, `SUCCEEDED`, `INFEASIBLE`).
- `GET /api/v1/optimizations/{id}/results` — Retrieve optimal facility allocations and Pareto frontier.

### 5. Decision Ledger & Point-in-Time Replay
- `POST /api/v1/decisions` — Freeze and persist an operational decision with exact input snapshot.
- `GET /api/v1/decisions/{id}` — Retrieve frozen decision and evidence lineage.
- `POST /api/v1/decisions/{id}/replay` — Re-execute decision under historical $\text{Information Available At} \le \text{Decision Time}$ constraint.

### 6. Operational Assistant
- `POST /api/v1/assistant/chat` — Schema-grounded operational reasoning and constraint explanation.

## Error Response Envelope

All error responses strictly adhere to the typed error envelope:

```json
{
  "error": {
    "code": "UNAUTHORIZED | FORBIDDEN | NOT_FOUND | VALIDATION_ERROR | INTERNAL_ERROR",
    "message": "Human readable description",
    "request_id": "req-uuid-12345",
    "details": {}
  }
}
```
