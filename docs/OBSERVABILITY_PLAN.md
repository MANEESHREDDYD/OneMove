# Observability Plan

Audit date: 2026-06-10

OneMove currently has deterministic local-first observability placeholders. It does not claim real production APM.

## Implemented Local Signals

- `/admin/system-health` dashboard.
- `npm run healthcheck`.
- Database connection check.
- Required table checks.
- Demo user checks.
- Pipeline status.
- Latest ML run status.
- Latest data quality result.
- Cached RLS test status.
- Build version/commit hash.
- Request/event count placeholder.
- Pipeline freshness.
- Failed pipeline count.
- Failed ML job count.
- Last successful intelligence refresh.

## Production Observability Still Needed

- Structured request logs.
- Centralized log storage.
- Error monitoring.
- Distributed tracing.
- Metrics dashboard.
- Alert routing.
- SLOs and burn-rate alerts.
- On-call paging.
- Incident timelines and postmortems.
- Synthetic uptime checks from outside localhost.

## Honest Claim

Implemented: local readiness and pipeline health visibility.

Not implemented: production APM, production tracing, incident paging, or global service observability.

