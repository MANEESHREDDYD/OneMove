# API Observability and Rate Limiting

ZonePilot emits one JSON object per request. Logs include the UTC timestamp, level, service,
environment, request/correlation IDs, route template, status, and latency. Authorization values,
tokens, passwords, API keys, and secrets are never included. Set `ZONEPILOT_LOG_LEVEL` to control
verbosity and `ZONEPILOT_SERVICE`/`ZONEPILOT_ENV` to label the stream.

Set `SENTRY_DSN` to activate backend exception reporting. `ZONEPILOT_RELEASE` should be the
immutable application version plus commit identity. External activation remains owner-controlled;
the API runs without Sentry when the DSN is absent.

Supabase access-token verification supports asymmetric ES256/RS256 signing keys through the
configured project's cached JWKS endpoint and isolated legacy HS256 verification. Pin
`SUPABASE_JWT_ISSUER`; optionally pin `SUPABASE_JWKS_URL` and `SUPABASE_JWT_ALGORITHMS` during
deployment. Never use an untrusted token claim to choose the discovery host.

## Metrics

`GET /metrics` is disabled unless `ZONEPILOT_METRICS_ENABLED=true`. When
`ZONEPILOT_METRICS_TOKEN` is set, the scraper must send it as a bearer token. The endpoint exports
request count and latency summaries labelled by method, route template, and status. It deliberately
does not label by user, workspace, raw path, or request ID, avoiding cardinality and privacy leaks.

Initial alert routing must use measured staging baselines. Start with:

| Severity | Condition | Window | First response |
| --- | --- | --- | --- |
| P0 | Health probe unavailable or readiness DB check fails continuously | 5 minutes | API/DB outage runbook |
| P0 | Confirmed authentication bypass or data-integrity failure | Immediate | Disable affected write path and invoke incident response |
| P1 | 5xx ratio above 5% with at least 20 requests | 10 minutes | Inspect request IDs and recent deploy |
| P1 | Required provider exceeds its documented freshness SLA | 2 consecutive checks | Provider/stale-data runbook |
| P1 | Required job fails 3 consecutive executions | 3 runs | Failed-acquisition runbook |
| P2 | p95 latency exceeds the measured staging budget | 30 minutes | Profile route and DB timings |

Transient single failures do not page.

## Rate limiter

The current limiter is a process-local fixed window. Defaults are 10 authentication attempts,
120 authenticated API calls, and 20 expensive job/scenario/optimizer requests per principal per
minute. Override them with `ZONEPILOT_AUTH_RATE_LIMIT_PER_MINUTE`,
`ZONEPILOT_API_RATE_LIMIT_PER_MINUTE`, and `ZONEPILOT_EXPENSIVE_RATE_LIMIT_PER_MINUTE`.

Move to a shared managed limiter before running more than one API replica, or earlier if staging
shows deliberate multi-process bypass, sustained traffic above 50 requests/second, or a need for
tenant-wide quotas. Preserve the same structured `429 RATE_LIMITED` contract during migration.
