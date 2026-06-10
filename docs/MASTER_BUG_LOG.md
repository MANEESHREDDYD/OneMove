# Master Bug Log

Phase 4 Status: GO for private localhost portfolio review.
Production Status: NOT YET APPROVED.
Known Limitation: Mobile Playwright experiment simulation may exceed default timeout under local hardware constraints; desktop flow and backend simulation pass.


## Resolved Bugs during Phase 4
1. **Ops Insights Slicing Error:** `generate-ops-insights.ts` crashed due to `TypeError: Cannot read properties of undefined (reading 'slice')` when `order_id` in `risk_checks` was null (applies to customer-level risk checks). **Fix:** Added optional chaining `risk.order_id?.slice() || risk.customer_id?.slice() || 'Unknown'`.
2. **Missing UI Imports:** Several imports were initially missed or incorrect. Fixed during Playwright UI runs.
3. **Database Null Check:** The `experiment_metrics` table required a specific unique constraint `(experiment_id, variant_id)` to handle upserts safely via the script. Fixed via schema adjustment.
4. **Environment Variables via Server Action:** Background tasks inside `score_all` were hanging or dropping if run directly in server actions. Fixed by using detached processes or synchronous node spawning with `.unref()`.

## Known Issues (Deferred)
- Playwright tests run via CLI currently fail on Phase 4 tests *if* global `.auth` setup is wiped. Requires `npm run test:e2e` from scratch to build auth files. This is standard behavior but impacts targeted isolated test runs.
- MLOps `score_all` background spawn in the UI doesn't provide real-time UI loading state feedback (user must refresh).

## Phase 5 Bug Log
No new critical bugs. Minor design tweaks applied to architecture page for mobile responsiveness. Known limitation regarding Playwright Mobile timeout on Experiments simulation documented.

## BUG-008: Leaflet Map Tiles Fragmented
**Status:** Fixed
**Description:** Map tiles rendered as disjointed squares; map did not fill container on /customer/rides.
**Root Cause:** Missing leaflet.css and improper parent width/height constraints on mobile views.
**Resolution:** Injected CSS via client import, removed hidden lg:flex wrapper to enforce standard flex rendering, and invoked map.invalidateSize() after mount.

---

# Phase 6 — Final Product Audit (2026-06-10)

Full audit pass. Every bug below has reproduction, root cause, fix and retest.

## BUG-009 — Ride booking fails for every customer
- **Severity:** Critical
- **Route/file:** `app/customer/rides/actions.ts` (`requestRide`)
- **Steps to reproduce:** Log in as a customer → `/customer/rides` → pick pickup + dropoff → click "Request Economy".
- **Expected:** Order is created and the customer is redirected to `/customer/rides/{id}`.
- **Actual:** Page shows "Failed to request ride. Please try again."; no redirect. Server logged Postgres `22P02 invalid input syntax for type numeric`.
- **Root cause:** `finalPrice` was set to `estimate.prices.economy` — the **whole `FareBreakdown` object** `{base,distance,time,platform,tax,total}` — and inserted into the numeric `total_amount` column. It also ignored the `comfort`/`xl` classes.
- **Fix applied:** Select the correct class key and persist its numeric `.total`: `estimate.prices[priceKey].total`, where `priceKey` is validated against `economy|comfort|xl|premium` (defaults to economy).
- **Retest result:** `onemove-core-flows` (book a ride) and the cross-role `onemove-ride-flow` pass; booking redirects to the order page.
- **Final status:** ✅ Fixed.

## BUG-010 — `.gitignore` corrupted (UTF-16 mid-file); ignore rules dead
- **Severity:** High
- **Route/file:** `.gitignore`
- **Steps to reproduce:** `git ls-files test-results | wc -l` → 175 tracked files (~119 MB of videos/traces).
- **Expected:** `test-results/`, `playwright-report/`, Python caches are git-ignored.
- **Actual:** The file switched to UTF-16LE at the `test-results/` line, so git read those patterns as garbled bytes and ignored nothing; 119 MB of generated artifacts were committed.
- **Root cause:** A previous append wrote UTF-16 into a UTF-8 file.
- **Fix applied:** Rewrote `.gitignore` in clean UTF-8 (adds `playwright/.auth/`, `*.tsbuildinfo`, `*.egg-info/`, `Assist/`); `git rm --cached` the generated trees.
- **Retest result:** `git ls-files test-results playwright-report` → 0; ignores effective.
- **Final status:** ✅ Fixed.

## BUG-011 — `.gitattributes` corrupted (UTF-16); GitHub language stats polluted
- **Severity:** High
- **Route/file:** `.gitattributes`
- **Steps to reproduce:** Inspect bytes — file begins with a UTF-16 BOM; `linguist-generated` markers unreadable.
- **Expected:** Generated Playwright report JS/CSS excluded from GitHub language stats.
- **Actual:** Markers were UTF-16 so linguist ignored them; committed report bundles skewed language stats.
- **Root cause:** UTF-16 encoding of the attributes file.
- **Fix applied:** Rewrote `.gitattributes` in UTF-8 and removed the generated report from tracking (see BUG-010), so stats reflect real source.
- **Retest result:** Attributes parse as UTF-8; generated trees untracked.
- **Final status:** ✅ Fixed. (No artificial language manipulation — only genuine generated files are excluded.)

## BUG-012 — `npm run lint` failing (277 → 0 errors)
- **Severity:** High
- **Route/file:** `eslint.config.mjs` + ~20 source files
- **Steps to reproduce:** `npm run lint`.
- **Expected:** Lint passes.
- **Actual:** 3158 problems (277 errors): eslint was linting committed minified Playwright bundles, plus real `no-explicit-any`, `no-require-imports`, `react/no-unescaped-entities`, `prefer-const`, `set-state-in-effect` errors in shipped code.
- **Root cause:** Generated dirs not ignored by eslint; loose typing/JSX text in app code.
- **Fix applied:** Ignored `playwright-report/`, `test-results/`, `coverage/`; added a scoped override for CommonJS `scripts/`; replaced `any` with precise types (Supabase row/JSON shapes, `OrderStatus`, accumulator interfaces), escaped JSX entities, justified mount-effect `setState` disables.
- **Retest result:** `npm run lint` → 0 errors; `npm run typecheck` → 0 errors; `npm run build` → success.
- **Final status:** ✅ Fixed.

## BUG-013 — `docs/MASTER_BUG_LOG.md` corrupted (UTF-16)
- **Severity:** Medium
- **Route/file:** `docs/MASTER_BUG_LOG.md`
- **Steps to reproduce:** Open the file — BUG-008 onward rendered as spaced garbage.
- **Expected:** Readable portfolio bug log.
- **Actual:** Appended section was UTF-16, unreadable in editors/GitHub.
- **Root cause:** UTF-16 append into a UTF-8 file.
- **Fix applied:** Decoded prior content and rewrote the file in clean UTF-8 (this document).
- **Retest result:** No NUL bytes; renders correctly.
- **Final status:** ✅ Fixed.

## BUG-014 — Generated junk & embedded git repo committed
- **Severity:** Medium
- **Route/file:** `Assist/` (gitlink), `test-results/`, `playwright-report/`, `**/__pycache__/`, `*.egg-info/`
- **Steps to reproduce:** `git ls-files` shows an `Assist` gitlink (no `.gitmodules`) plus ~330 generated files.
- **Expected:** Only source is tracked.
- **Actual:** A nested project gitlink and ~119 MB of generated artifacts/caches were tracked.
- **Root cause:** Broken ignores (BUG-010) + an accidentally-added embedded repo.
- **Fix applied:** `git rm -r --cached Assist test-results playwright-report **__pycache__** *.egg-info`; added them to `.gitignore`. Files remain on disk; only tracking removed.
- **Retest result:** Tracking counts are 0 for all of the above.
- **Final status:** ✅ Fixed.

## BUG-015 — Demo session tokens committed
- **Severity:** Medium
- **Route/file:** `playwright/.auth/{admin,customer,merchant,partner}.json`
- **Steps to reproduce:** Files contain base64 JWT access/refresh tokens for demo users.
- **Expected:** Auth state files are local-only.
- **Actual:** Demo-user session tokens were tracked (no real PII, but bad practice).
- **Root cause:** `playwright/.auth/` not ignored.
- **Fix applied:** `git rm --cached` the files; added `playwright/.auth/` to `.gitignore`. They are regenerated locally by `global.setup.ts`.
- **Retest result:** Untracked; e2e still authenticates (regenerates the files).
- **Final status:** ✅ Fixed.

## BUG-016 — `npm run test:rls` crashes (queries non-existent column)
- **Severity:** Medium
- **Route/file:** `scripts/test-rls-security.js`
- **Steps to reproduce:** `npm run test:rls` → "Failed to list profiles" then a libuv crash.
- **Expected:** The RLS probe runs.
- **Actual:** `select('id, email, role')` on `profiles` errored — `column profiles.email does not exist` (email lives in `auth.users`).
- **Root cause:** Script referenced a column not present on `public.profiles`.
- **Fix applied:** Changed the select to `id, role` (the only fields used).
- **Retest result:** Script runs and reports RLS results (see RLS-001/002 below).
- **Final status:** ✅ Fixed.

## BUG-017 — Stale e2e selectors after UI redesign
- **Severity:** Low (test-suite maintenance; product unaffected)
- **Route/file:** `tests/e2e/onemove-core-flows`, `onemove-ride-flow`, `onemove-negative-flows`, `onemove-error-handling`, `onemove-idempotency`, `onemove-session-hardening`
- **Steps to reproduce:** Run the specs on Chromium — failures on `Confirm Economy`, `Add $`, `View Cart & Checkout`, `Book Ride`, `text=Menu`, `Invalid login credentials`, plus post-login navigation races.
- **Expected:** Selectors match the current UI.
- **Actual:** Selectors referenced a previous design; some tests navigated before auth completed.
- **Root cause:** UI text/structure changed (`Request Economy`, icon-only add button, `Go to Checkout`, `Enter Destinations`, graceful invalid-order redirect, `Could not authenticate user`) without test updates.
- **Fix applied:** Updated selectors to the live UI and added `waitForURL` after login; asserted the real graceful behaviours.
- **Retest result:** All listed specs pass on Chromium.
- **Final status:** ✅ Fixed.

## BUG-018 — Console-error assertion flags benign RSC prefetch aborts
- **Severity:** Low
- **Route/file:** `tests/e2e/helpers/assertNoConsoleErrors.ts`
- **Steps to reproduce:** Multi-page flows reported `net::ERR_ABORTED` on `?_rsc=` requests.
- **Expected:** Only genuine errors fail the assertion.
- **Actual:** Next.js cancels in-flight RSC prefetches on navigation; those aborts were treated as failures.
- **Root cause:** `requestfailed` handler did not exclude `ERR_ABORTED`.
- **Fix applied:** Ignore `ERR_ABORTED` (still flags real failures, 5xx responses and uncaught exceptions).
- **Retest result:** `onemove-ride-flow` passes its console-error gate.
- **Final status:** ✅ Fixed.

---

---

# Phase 6.1 — RLS isolation hardening (2026-06-10)

Applied `supabase/fixes/2026_rls_hardening.sql` (reproducible via
`npm run db:harden-rls`). Verified by the rewritten 16-check
`npm run test:rls` matrix (all pass).

## RLS-001 — `profiles` broadly readable (incl. phone) — ✅ FIXED
- **Severity:** was Low (localhost) / High (production)
- **Route/file:** `public.profiles` policies; `app/customer/orders/[id]/page.tsx`, `app/customer/rides/[id]/page.tsx`
- **Steps to reproduce (before):** as a customer, `SELECT * FROM profiles` returned 293 rows incl. 41 phone numbers.
- **Expected:** a customer reads only their own profile; no broad phone/email exposure.
- **Actual (before):** a permissive `USING (auth.role() = 'authenticated')` SELECT policy exposed all profile columns to every authenticated user.
- **Root cause:** legacy MVP-permissive profiles policy (+ a `role IN ('merchant','driver')` policy) left in place.
- **Fix applied:** dropped the broad policies; `profiles` SELECT is now own-row (`id = auth.uid()`) + `is_admin()` only. Added safe display views `safe_profile_cards` / `safe_partner_cards` / `safe_merchant_cards` exposing only `id, display_name, role, avatar_url` (and merchant `rating/category`) — **no phone/email**. Repointed the two customer pages that showed a driver name to read from `safe_profile_cards`.
- **Retest result:** customer now sees **1** profile (own); `safe_profile_cards` has no phone/email column; driver name still renders. `test:rls` green; e2e (incl. ride-flow → customer ride detail) green.
- **Final status:** ✅ Fixed.

## RLS-002 — "Merchant can read other merchants' orders" — ✅ FALSE POSITIVE, isolation verified
- **Severity:** was reported Low/High; actual product impact: **none**.
- **Route/file:** `scripts/test-rls-security.js`; `public.orders` policies.
- **Root cause:** the **old probe** compared `orders.merchant_id` (a *store* id) to the merchant's *user* id, which never matches — so it reported "cross-merchant" even though the policy (`merchants.owner_id = auth.uid()`) was correct. Empirical check: merchant saw 2 orders, **0** cross-tenant.
- **Fix applied:** rewrote `test:rls` to compute the merchant's owned store ids and assert tenancy correctly; reasserted the merchant `orders`/`order_items` policies and **added** a scoped `merchant_select_payments` policy (own orders only). Added anonymous-denied + partner-scope checks.
- **Retest result:** merchant reads only own-store orders/items/payments (0 cross-tenant); anonymous denied; partner sees only assigned/available jobs. `test:rls` 16/16 green.
- **Final status:** ✅ Fixed/verified (no cross-tenant order visibility).

> Not a defect: customers can read the `merchants` catalog + `safe_*_cards` views — **by design** (browse stores / show names without PII).

## Final bug status
- **Open Critical:** 0
- **Open High:** 0
- **Open Medium:** 0
- **No known cross-tenant order/data visibility bugs.**
- **Open Low / documented limitations:** full cross-browser/mobile e2e matrix not gated in CI; no production APM/alerting/rate-limiting. None can cause cross-tenant data leakage. Consistent with "localhost demo: GO / production: NOT YET APPROVED".
