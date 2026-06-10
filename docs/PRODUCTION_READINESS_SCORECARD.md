# OneMove Production Readiness Scorecard

**Verdict**

- **Private localhost portfolio demo: GO** ✅
- **Public production deployment: NOT YET APPROVED** ⛔

This scorecard is deliberately honest. OneMove is a feature-complete, tested
portfolio demo on localhost; it is **not** a hardened production system. The gaps
below are the reason production is not approved — not an oversight.

Scoring: 🟢 ready · 🟡 partial / demo-grade · 🔴 not production-ready

| Area | Localhost demo | Production | Notes |
|---|---|---|---|
| Security (authn/z) | 🟢 | 🟡 | Supabase Auth + middleware route guards; role-based access verified by e2e (`onemove-role-security`). Needs rate limiting, audit logging, secret rotation for prod. |
| RLS (multi-tenant) | 🟡 | 🔴 | RLS is **enabled and enforced** (customers cannot read others' orders/tickets; admin-only tables blocked). **Two hardening gaps remain** (see below). |
| Testing | 🟢 | 🟡 | 18 unit/vitest + 12 pytest + Playwright e2e (smoke, core flows, ride flow, role security, negative/edge, idempotency, session) green on Chromium. Full cross-browser/mobile matrix not gated. |
| Performance | 🟡 | 🟡 | Next 16 build, RSC, indexed queries, admin RPC. No load/SLO budget enforced in CI; see LOAD_TEST_REPORT.md. |
| Observability | 🟡 | 🔴 | `ml_pipeline_runs` MLOps log + healthcheck script. No APM, structured logs, tracing, or alerting. |
| Deployment | 🟡 | 🔴 | Vercel preview checklist, rollback plan, smoke checklist, `deploy/env.example` (no secrets). No prod IaC, no blue/green, no DB migration gating. |
| Realtime | 🟢 | 🟡 | Supabase Realtime for merchant/partner order updates; verified manually. Needs reconnection/backpressure hardening for scale. |
| Data quality | 🟢 | 🟡 | `debug:data-integrity` (10 checks) + SQL quality checks + pipeline DQ all green. No automated freshness/volume anomaly alerting. |
| ML readiness | 🟡 | 🟡 | Deterministic, explainable baselines with offline evaluation (MODEL_EVALUATION_REPORT) + feature registry (FEATURE_STORE_DESIGN) + lineage. No trained models, online store, or drift monitor. |

## RLS hardening gaps (must-fix before production)

Surfaced by `npm run test:rls` (probes policies as the `authenticated` role).
Data is **synthetic** (`is_demo = true`, faker-generated); there is no real PII,
so the localhost-demo impact is **Low**. For production these are **High**:

1. **`profiles` is broadly readable by any authenticated user** (incl. a `phone`
   column). The marketplace legitimately needs cross-user *name* visibility
   (e.g. a customer seeing their driver's name), but `phone` and the full table
   should not be exposed. *Fix:* expose names via a restricted view / column
   grants; scope row access.
2. **A merchant can read orders belonging to other merchants.** *Fix:* tighten
   the `orders` SELECT policy so merchants only see rows where
   `merchant_id = their merchant`.

> Not a gap: customers can read the `merchants` catalog table — this is **by
> design** (customers must browse restaurants/stores to order).

These are intentionally **not** patched against the hosted demo database in this
QA pass, because the changes are schema/policy-level, outward-facing, and the
demo is explicitly localhost-only. They are tracked here and in
[MASTER_BUG_LOG.md](MASTER_BUG_LOG.md) as production blockers.

## What would move production from ⛔ to ✅

- Close the two RLS gaps above and re-run `npm run test:rls` to green.
- Add rate limiting + audit logging + secret rotation.
- Add APM / structured logging / alerting.
- Gate CI on the full cross-browser + mobile e2e matrix and a load/SLO budget.
- Add DB migration gating and prod IaC.

Until then: **localhost demo = GO, production = NOT YET APPROVED.**
