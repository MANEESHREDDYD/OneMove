# OneMove Final QA Master Report

## Executive Summary

This report concludes the **Phase 6 Final Product Audit** (2026-06-10), building on
the Phase 4/5 validations. OneMove underwent a full validation gauntlet, a local
production smoke + core-flow pass, a data/ML/analytics audit, and targeted
hardening additions.

The audit found and fixed **1 Critical**, **3 High**, and **4 Medium** issues,
plus test-suite maintenance. No Critical/High/Medium issues remain open. Two
RLS items are documented as production-hardening (synthetic data, Low for the
localhost demo). Full per-bug detail is in
[MASTER_BUG_LOG.md](MASTER_BUG_LOG.md).

The platform is approved for **private localhost portfolio demonstration only**.

## Verdict

- **Private localhost portfolio demo: GO** ✅
- **Public production deployment: NOT YET APPROVED** ⛔

See [PRODUCTION_READINESS_SCORECARD.md](PRODUCTION_READINESS_SCORECARD.md).

## Test execution (this audit)

| Check | Command | Result |
|---|---|---|
| Env validation | `npm run validate:env` | ✅ pass |
| Lint | `npm run lint` | ✅ 0 errors (was 277) |
| Types | `npm run typecheck` | ✅ 0 errors |
| Unit/integration | `npm test` | ✅ 18 passed |
| Production build | `npm run build` | ✅ success |
| Python lint | `npm run py:lint` (ruff) | ✅ pass |
| Python tests | `npm run py:test` (pytest) | ✅ 12 passed (was 3) |
| ML scoring | `npm run py:ml` | ✅ deterministic |
| Data quality | `npm run py:dq` | ✅ 3/3 checks |
| Model evaluation | `npm run py:evaluate` | ✅ deterministic, reproducible |
| Intelligence refresh | `npm run intelligence:refresh` | ✅ pipeline + ML + experiments |
| Data integrity | `npm run debug:data-integrity` | ✅ 10/10 checks |
| Intelligence data | `npm run debug:intelligence` | ✅ all tables populated |
| RLS probe | `npm run test:rls` | ✅ 16/16 — tenant isolation verified |
| Healthcheck | `npm run healthcheck` | ✅ all required green |
| E2E (Chromium) | Playwright | ✅ smoke, core flows, ride flow, role security, negative/edge, idempotency, session, intelligence, maps |

> E2E scope: validated on the Chromium project (with the auth `setup` project).
> The full 6-device matrix (incl. mobile/tablet) is **not** gated in CI — the
> documented mobile experiment-simulation timeout makes it flaky on local
> hardware (see Known Limitations).

## Highlighted fixes (this audit)

- **Critical — ride booking restored:** every booking failed (`22P02`) because the
  numeric `total_amount` was being given the full fare-breakdown object; now persists
  `prices[class].total` and honours all service classes.
- **High — repo hygiene:** rewrote UTF-16-corrupted `.gitignore`/`.gitattributes`,
  untracked ~119 MB of generated artifacts + an embedded `Assist/` repo + demo
  session-token files; GitHub language stats now reflect real source (no artificial
  manipulation — only genuine generated files excluded).
- **High — lint/types green:** 277 → 0 lint errors via proper typing (no blanket
  `any` suppression in app code) + scoped CommonJS-script override.
- **Medium — tooling:** fixed the RLS probe (queried a non-existent `profiles.email`);
  rewrote the UTF-16-corrupted bug log.

## New portfolio-strengthening additions (Phase 5)

All real, tested, documented and wired into OneMove:

- **Model evaluation** — `python/.../evaluation/model_evaluation.py`, `npm run py:evaluate`,
  5 pytest cases, [MODEL_EVALUATION_REPORT.md](MODEL_EVALUATION_REPORT.md).
- **Feature store** — `python/.../features/feature_store.py`, `npm run py:features`,
  4 pytest cases, [FEATURE_STORE_DESIGN.md](FEATURE_STORE_DESIGN.md).
- **Data lineage** — [`analytics/lineage.yml`](../analytics/lineage.yml) (validated) +
  [DATA_LINEAGE_REPORT.md](DATA_LINEAGE_REPORT.md).
- **Healthcheck** — `scripts/healthcheck.ts`, `npm run healthcheck`,
  [LOCAL_HEALTHCHECK_REPORT.md](LOCAL_HEALTHCHECK_REPORT.md).
- **Production readiness scorecard** — [PRODUCTION_READINESS_SCORECARD.md](PRODUCTION_READINESS_SCORECARD.md).

## RLS isolation hardening (Phase 6.1)

- **Profiles locked** to own-row + admin; `safe_profile_cards` / `safe_partner_cards`
  / `safe_merchant_cards` views serve display names with **no phone/email**. The
  two customer pages that showed a driver name were repointed to the safe view.
- **Tenant isolation verified** by a rewritten 16-check `npm run test:rls`:
  customer→own only, merchant→own-store orders/items/payments only (0 cross-tenant),
  partner→assigned/available only, admin→platform-wide, anonymous→denied.
- The old "merchant can read other merchants' orders" finding was a **false
  positive** in the previous probe (compared store id to user id); the policy was
  always correct and is now proven so.
- Applied via `supabase/fixes/2026_rls_hardening.sql` (`npm run db:harden-rls`).

## Known limitations & risks

1. **No cross-tenant data leakage** — RLS-001/002 are fixed/verified (above).
2. **E2E matrix not fully gated:** "Simulate Traffic" can exceed strict Playwright
   mobile timeouts on local hardware; cross-browser/mobile not gated in CI.
3. **Deterministic intelligence:** ETAs, demand and scores use deterministic
   rules+statistics baselines for presentation, not trained ML models.
4. **No production observability:** no APM/structured logging/alerting yet.
5. **Public deployment pending:** DB strings must not be exposed to a public
   Vercel deployment until the above are addressed.

## Recommendation

✅ **APPROVED FOR LOCALHOST PORTFOLIO REVIEW** — no open Critical/High/Medium bugs.
❌ **NOT APPROVED FOR PUBLIC PRODUCTION DEPLOYMENT.**
