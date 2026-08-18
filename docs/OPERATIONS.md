# ZonePilot Operational Runbook & Incident Management

## 1. Health Monitoring
- Health Check: `GET /api/v1/health` returns status of API, database connectivity, and version.
- Observatory Health UI: `/system-health` and `/data-health`.

## 2. Point-In-Time Replay & Audit
- When an operator or auditor requests verification of an optimization:
  1. Locate the `decision_id` in `/decisions` or `public.decision_records`.
  2. Invoke `/replay?id=<decision_id>` to run authentic PIT verification.
  3. Check output for `pit_valid: true`, `reproduced_exact_action: true`, `reproduced_exact_facilities: true`.

## 3. Database Maintenance
- PostgreSQL pooler URL: `aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require`.
- All tables use indexed foreign keys and temporal ranges (`valid_from`, `valid_to`, `information_available_at`).
