# OneMove — Canonical Event Contract (Pub/Sub)

## Topics & Subscriptions

- **Primary Job Topic**: `zonepilot-opt-jobs-<env>`
- **Worker Pull Subscription**: `zonepilot-opt-worker-sub-<env>`
- **Dead-Letter Topic**: `zonepilot-opt-dead-letter-<env>`

## Message Payload Schema: Optimization Job Event

```json
{
  "event_id": "evt-uuid-12345",
  "event_type": "OPTIMIZATION_JOB_ENQUEUED",
  "occurred_at": "2026-08-19T00:00:00.000Z",
  "job_id": "opt-uuid-98765",
  "workspace_id": "ws-uuid-11111",
  "actor_id": "user-uuid-22222",
  "scenario_id": "scn-uuid-33333",
  "solver_config": {
    "max_facilities": 5,
    "p95_target_seconds": 1000,
    "demand_coverage_threshold": 1.0,
    "time_limit_seconds": 30
  },
  "matrix_id": "osrm-bengaluru-gold-v1",
  "matrix_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

## Idempotency & Delivery Guarantees

1. **At-Least-Once Delivery**: Workers must gracefully handle duplicate deliveries by checking `public.optimization_jobs.status` in PostgreSQL.
2. **Lease Management**: When a worker claims a job, it executes `UPDATE optimization_jobs SET status = 'RUNNING', worker_id = :worker_id, lease_expires_at = NOW() + INTERVAL '5 minutes' WHERE id = :job_id AND status = 'QUEUED'`.
3. **Dead-Letter Handling**: If a job fails or times out after 5 consecutive delivery attempts, Pub/Sub routes the payload to `zonepilot-opt-dead-letter-<env>` and fires an alert.
