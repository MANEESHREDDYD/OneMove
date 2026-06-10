# Master Bug Log

Audit date: 2026-06-10

Final bug status:

- Open Critical: 0
- Open High: 0
- Open Medium: 0
- Open Low/documented limitations: yes
- No known cross-tenant data leaks open.
- No known broken customer, merchant, partner, or admin core flows open after focused final retest.

## BUG-019

Severity: Medium

Route/file: `tests/e2e/helpers/finalAuditHelpers.ts`, demo order rows in Supabase.

Steps to reproduce: Run final cross-role e2e fixtures, then run `npm run debug:data-integrity`.

Expected: Final audit demo orders include order items, payment rows, and status events.

Actual: Two final audit demo orders were missing payment/order item lineage.

Root cause: The helper inserted direct `orders` rows without the full demo order lineage required by the integrity checks.

Fix applied: Updated `createDemoOrderForMerchant` and `createDemoOrderForPartner` to insert order items where applicable, demo payments, and status events. Repaired the two already-created final-audit demo rows.

Retest result: `npm run debug:data-integrity` passed.

Final status: Fixed.

## BUG-020

Severity: Medium

Route/file: `app/merchant/actions.ts`, `app/customer/checkout/actions.ts`, `app/admin/orders/[id]/actions.ts`, `tests/e2e/helpers/finalAuditHelpers.ts`.

Steps to reproduce: Trigger order status writes from merchant/admin/checkout flows against the live schema.

Expected: Status event insert succeeds and lifecycle history is recorded.

Actual: Code attempted to write a non-existent `changed_by` column on `order_status_events`.

Root cause: Code/schema drift. The live `order_status_events` table has `id`, `order_id`, `status`, `notes`, `is_demo`, `seed_run_id`, `created_at`, and `idempotency_key`, but not `changed_by`.

Fix applied: Removed `changed_by` from status event inserts and preserved actor context in `notes` where useful.

Retest result: `npm run debug:data-integrity`, `npm run test:rls`, and focused final e2e passed.

Final status: Fixed.

## BUG-021

Severity: High

Route/file: `/admin/command-center`, `app/admin/command-center/AdminDashboardClient.tsx`.

Steps to reproduce: Run strict Playwright audit against the admin command center.

Expected: No hydration mismatch, console error, or blank page.

Actual: React reported a hydration mismatch.

Root cause: Server and client rendered locale-specific timestamps with `toLocaleString()`, producing different text.

Fix applied: Replaced locale formatting with deterministic UTC formatting for the command center history output.

Retest result: Focused final Playwright suite passed, 15/15.

Final status: Fixed.

## BUG-022

Severity: Medium

Route/file: `/admin/mlops`, `app/admin/mlops/page.tsx`, `components/layout/AppShell.tsx`.

Steps to reproduce: Run final mobile responsive audit at 390px width and open `/admin/mlops`.

Expected: Mobile page has no meaningful horizontal overflow and remains usable.

Actual: The page overflowed horizontally by hundreds of pixels.

Root cause: The shell main region lacked `min-w-0`, and the MLOps header/table layout did not constrain wide content on mobile.

Fix applied: Added `min-w-0` to the shell main region, made the MLOps header responsive, wrapped the table in a contained horizontal scroller, and used deterministic UTC timestamps.

Retest result: Final mobile audit passed; manual measurement showed 0px overflow at 390px width.

Final status: Fixed.

## BUG-023

Severity: Medium

Route/file: `/partner/jobs`, `app/partner/jobs/JobsClient.tsx`.

Steps to reproduce: Create a final audit partner ride job, log in as partner, and try to identify/accept that specific job.

Expected: Partner can see assigned/available jobs only, identify the target job, accept it, and update status.

Actual: Available job cards did not display a stable order ID, and UI state depended on realtime updates after actions.

Root cause: The available job card omitted the order ID and action handlers did not refresh the route after server actions.

Fix applied: Added order ID display, action error state, and `router.refresh()` after accept/update actions.

Retest result: Focused final cross-role suite passed.

Final status: Fixed.

## BUG-024

Severity: Low

Route/file: `tests/e2e/final-cross-role-flows.spec.ts`.

Steps to reproduce: Run final merchant flow immediately after creating a merchant fixture order.

Expected: Test waits for the next state button after each server action.

Actual: Test could reload before the server action completed and read stale card state.

Root cause: Test race in the final audit spec.

Fix applied: Wait for the next expected action button before proceeding.

Retest result: Final cross-role suite passed.

Final status: Fixed.

## BUG-025

Severity: Low

Route/file: `tests/e2e/final-cross-role-flows.spec.ts`.

Steps to reproduce: Run the full final customer journey under local hardware conditions.

Expected: Customer journey has enough time for map, checkout, order detail, recommendations, and support ticket checks.

Actual: The default Playwright test timeout was too tight for the full role flow.

Root cause: Final audit journey intentionally covers many route transitions and data writes in one test.

Fix applied: Set the final cross-role suite timeout to 120 seconds.

Retest result: Final cross-role suite passed.

Final status: Fixed.

## BUG-026

Severity: Low

Route/file: `tests/performance/local-load-smoke.js`.

Steps to reproduce: Run `npm run lint` after adding the local performance smoke test.

Expected: Lint passes with no errors.

Actual: ESLint reported three `@typescript-eslint/no-require-imports` errors for the CommonJS performance script.

Root cause: The new performance script intentionally uses CommonJS for direct Node execution, but the file was not covered by the existing CommonJS script override.

Fix applied: Added a narrow file-level ESLint directive for `@typescript-eslint/no-require-imports`.

Retest result: `npm run lint` passed with 0 errors.

Final status: Fixed.

## BUG-027

Severity: Low

Route/file: `scripts/reset-demo-state.ts`.

Steps to reproduce: Run `npm run demo:reset -- --dry-run` on Windows.

Expected: The reset command previews the synthetic demo reset scope and exits 0 without deleting data.

Actual: The wrapper failed during the preview step.

Root cause: The wrapper used `spawnSync('npx.cmd', ...)`, which failed to resolve reliably from Node on this Windows environment.

Fix applied: Replaced the `npx` wrapper with a direct `process.execPath` call to the local `tsx` CLI, and added clearer child-process error reporting.

Retest result: `npm run demo:reset -- --dry-run` passed and previewed only demo profile reset scope.

Final status: Fixed.

## Low Documented Limitations

- Full cross-browser/multi-project Playwright matrix is slower than the focused final Chromium audit and previously timed out locally; grouped final suites were run and documented.
- Recharts can emit non-breaking sizing warnings while responsive charts settle; strict tests fail on console errors and fatal patterns, not harmless warnings.
- Production APM, real rate limiting, real payments, real KYC, native mobile apps, and multi-region operations are not implemented.

## Final Rule

No known Critical/High/Medium issues open. Low documented limitations remain.
