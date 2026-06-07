# Master Bug Log (Phase 4)

Phase 4 Status: GO for private localhost portfolio review after validation.
Production Status: NOT YET APPROVED.


## Resolved Bugs during Phase 4
1. **Ops Insights Slicing Error:** `generate-ops-insights.ts` crashed due to `TypeError: Cannot read properties of undefined (reading 'slice')` when `order_id` in `risk_checks` was null (applies to customer-level risk checks). **Fix:** Added optional chaining `risk.order_id?.slice() || risk.customer_id?.slice() || 'Unknown'`.
2. **Missing UI Imports:** Several imports were initially missed or incorrect. Fixed during Playwright UI runs.
3. **Database Null Check:** The `experiment_metrics` table required a specific unique constraint `(experiment_id, variant_id)` to handle upserts safely via the script. Fixed via schema adjustment.
4. **Environment Variables via Server Action:** Background tasks inside `score_all` were hanging or dropping if run directly in server actions. Fixed by using detached processes or synchronous node spawning with `.unref()`.

## Known Issues (Deferred)
- Playwright tests run via CLI currently fail on Phase 4 tests *if* global `.auth` setup is wiped. Requires `npm run test:e2e` from scratch to build auth files. This is standard behavior but impacts targeted isolated test runs.
- MLOps `score_all` background spawn in the UI doesn't provide real-time UI loading state feedback (user must refresh).
