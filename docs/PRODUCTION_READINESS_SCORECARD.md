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
| RLS (multi-tenant) | 🟢 | 🟡 | RLS **enabled and enforced with verified tenant isolation** (16-check `npm run test:rls` matrix passes). Profiles locked to own+admin; safe display views expose no phone/email; merchant/partner/customer order isolation proven; anonymous denied. Prod still needs the broader hardening below (rate limiting, audit logging). |
| Testing | 🟢 | 🟡 | 18 unit/vitest + 12 pytest + Playwright e2e (smoke, core flows, ride flow, role security, negative/edge, idempotency, session) green on Chromium. Full cross-browser/mobile matrix not gated. |
| Performance | 🟡 | 🟡 | Next 16 build, RSC, indexed queries, admin RPC. No load/SLO budget enforced in CI; see LOAD_TEST_REPORT.md. |
| Observability | 🟡 | 🔴 | `ml_pipeline_runs` MLOps log + healthcheck script. No APM, structured logs, tracing, or alerting. |
| Deployment | 🟡 | 🔴 | Vercel preview checklist, rollback plan, smoke checklist, `deploy/env.example` (no secrets). No prod IaC, no blue/green, no DB migration gating. |
| Realtime | 🟢 | 🟡 | Supabase Realtime for merchant/partner order updates; verified manually. Needs reconnection/backpressure hardening for scale. |
| Data quality | 🟢 | 🟡 | `debug:data-integrity` (10 checks) + SQL quality checks + pipeline DQ all green. No automated freshness/volume anomaly alerting. |
| ML readiness | 🟡 | 🟡 | Deterministic, explainable baselines with offline evaluation (MODEL_EVALUATION_REPORT) + feature registry (FEATURE_STORE_DESIGN) + lineage. No trained models, online store, or drift monitor. |

## RLS hardening — DONE (verified)

The previously-flagged RLS items are now **fixed and verified** by the 16-check
`npm run test:rls` matrix (applied via `supabase/fixes/2026_rls_hardening.sql`,
reproducible with `npm run db:harden-rls`):

1. **`profiles` locked to own-profile + admin.** A customer now reads only their
   own profile row (was 293). Phone/email are no longer broadly readable.
   Display names are served by **safe views** (`safe_profile_cards`,
   `safe_partner_cards`, `safe_merchant_cards`) that expose only
   `id, display_name, role, avatar_url` (and merchant `rating/category`). The
   customer order/ride detail pages were repointed to these views.
2. **Merchant order isolation verified.** A merchant reads orders/order_items/
   payments **only** for stores they own (`merchants.owner_id`); cross-merchant
   reads = 0. (The earlier "merchant can read other merchants' orders" finding
   was a *false positive in the old probe*, which compared a store id to a user
   id — the policy was always correct. The probe is now correct and proves it.)
3. **Anonymous denied** on orders/profiles/payments; **partner** sees only
   assigned/available jobs; **admin** retains platform-wide access.

> By design (not a gap): customers can read the `merchants` catalog and the
> `safe_*_cards` display views — needed to browse and to show names without PII.

## What would move production from ⛔ to ✅

- Add rate limiting + audit logging + secret rotation.
- Add APM / structured logging / alerting.
- Gate CI on the full cross-browser + mobile e2e matrix and a load/SLO budget.
- Add DB migration gating and prod IaC.

Until then: **localhost demo = GO, production = NOT YET APPROVED.**
