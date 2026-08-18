# ZonePilot API Reference (v1.5.1)

All endpoints reside under `/api/v1` and require `Authorization: Bearer <token>` and `x-workspace-id: <id>`.

---

## 1. Network & GIS
- `GET /api/v1/zones` — Returns 94 Uber H3 Resolution 8 cells.
- `GET /api/v1/zones/{zone_id}/state` — Point-In-Time state for one zone across weather/traffic providers.
- `GET /api/v1/network/map-layers` — Overlaid GIS layers (pilot boundary, H3 cells, facility points).

## 2. Optimization (R3)
- `POST /api/v1/optimizations` — Run OR-Tools CP-SAT multi-scenario solver (returns 201/202 with `job_id`).
- `GET /api/v1/optimizations/{id}` — Fetch durable optimization results, opened facilities, and wall time.
- `GET /api/v1/optimizations` — List recent optimization jobs for workspace.

## 3. Resilience & Scenarios (R4)
- `POST /api/v1/scenarios` — Trigger failure scenario injection (ROAD_CLOSURE, CONGESTION_SPIKE, HEAVY_RAIN).
- `GET /api/v1/scenarios/{id}` — Fetch evaluated scenario metrics (P50/P90/P95, degradation grade).
- `GET /api/v1/scenarios` — List evaluated scenarios for workspace.

## 4. Decision Ledger & Replay (R7)
- `POST /api/v1/decisions` — Record immutable decision in PostgreSQL.
- `GET /api/v1/decisions/{id}` — Get decision record.
- `GET /api/v1/decisions` — List recorded decisions.
- `POST /api/v1/decisions/{id}/replay` — Execute Point-In-Time replay and verify anti-leakage.
- `POST /api/v1/decisions/{id}/shadow` — Create prospective shadow evaluation.
- `GET /api/v1/shadows/{id}` — Get shadow evaluation status.

## 5. Forecasting (R2)
- `POST /api/v1/forecast/predict` — Run causal forecast prediction against historical cutoff.
- `GET /api/v1/forecast/predictions` — Query historical predictions for a zone.

## 6. Assistant & Evidence
- `POST /api/v1/assistant/query` — Typed, evidence-grounded operator copilot.
- `GET /api/v1/datasets` — Catalog of immutable datasets and SHA-256 hashes.
- `GET /api/v1/health` — API and database connectivity status.
- `GET /api/v1/version` — Version contract and git commit SHA.
