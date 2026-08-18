# ZonePilot Decision Ledger & Time Travel Replay

## 1. Durable Decision Lifecycle

Every facility optimization decision in ZonePilot is stored immutably in PostgreSQL (`public.decision_records`):

```
Decision Request -> CP-SAT Solver -> Record in DB -> Generate Lineage Hash
                                       |
                                       +---> Time Travel Replay (verify PIT)
                                       +---> Create Shadow (future regret evaluation)
```

## 2. Decision Record Schema

| Field | Type | Description |
|---|---|---|
| `decision_id` | `VARCHAR(64)` | Unique decision identifier (e.g. `dec-957953f9...`). |
| `workspace_id` | `VARCHAR(64)` | Tenancy workspace boundary. |
| `decision_time` | `TIMESTAMPTZ` | Exact timestamp when the decision was executed. |
| `selected_action` | `VARCHAR(64)` | Operational action (e.g. `DEPLOY_FACILITIES`). |
| `opened_facilities` | `JSONB` | Array of facility IDs selected (e.g. `["fac:01", "fac:04"]`). |
| `objective_value` | `BIGINT` | Total deterministic weighted objective value. |
| `p95_travel_seconds` | `INTEGER` | Computed P95 travel latency across the network. |
| `coverage_basis_points` | `INTEGER` | Fraction of covered demand in basis points ($10000 = 100\%$). |
| `code_sha` | `VARCHAR(40)` | Pinned Git commit SHA of the solving engine. |

## 3. Time Travel Replay Verification

When a historical decision is replayed via `POST /api/v1/decisions/{id}/replay`:
1. The solver reconstructs the exact problem graph frozen at `decision_time`.
2. Verifies that no features available after `decision_time` were used ($\text{PIT Valid} = \text{True}$).
3. Verifies that recomputed facilities and objective match the original record $100\%$.
4. Writes an audit record to `public.decision_replays`.
