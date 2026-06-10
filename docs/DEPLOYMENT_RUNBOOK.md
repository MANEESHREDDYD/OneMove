# Deployment Runbook

Audit date: 2026-06-10

This runbook covers a production-preview deployment only. It does not approve public real marketplace production.

## Pre-Deployment

1. Pull latest `main`.
2. Confirm the deployment branch and commit.
3. Rotate Supabase DB password and all shared secrets.
4. Update local and deployment environment variables.
5. Run `npm run validate:env`.
6. Run `npm run lint`.
7. Run `npm run typecheck`.
8. Run `npm test`.
9. Run `npm run build`.
10. Run `npm run py:lint`.
11. Run `npm run py:test`.
12. Run `npm run py:ml`.
13. Run `npm run py:dq`.
14. Run `npm run py:evaluate`.
15. Run `npm run healthcheck`.
16. Run `npm run intelligence:refresh`.
17. Run `npm run debug:data-integrity`.
18. Run `npm run debug:intelligence`.
19. Run `npm run test:rls`.
20. Run the focused final e2e suite or full e2e suite where time allows.

## Deploy

1. Deploy the exact audited commit.
2. Do not deploy from an uncommitted working tree.
3. Confirm environment variables use rotated values.
4. Confirm the deployment does not expose service-role credentials to the browser.
5. Confirm Supabase RLS is enabled for protected tables.

## Post-Deployment Smoke

1. Open `/showcase`.
2. Log in as the customer demo user and verify `/customer/rides` and `/customer/orders`.
3. Log in as the merchant demo user and verify `/merchant` and `/merchant/orders`.
4. Log in as the partner demo user and verify `/partner` and `/partner/jobs`.
5. Log in as the admin demo user and verify `/admin/command-center`, `/admin/system-health`, `/admin/analytics`, `/admin/mlops`, and `/admin/experiments`.
6. Run `npm run healthcheck` against the preview environment if configured.
7. Run `npm run test:rls`.

## Go/No-Go

Preview GO requires:

- Build pass.
- Env validation pass.
- Rotated secrets verified.
- RLS pass.
- Healthcheck pass.
- Core e2e pass.
- No known Critical/High/Medium bugs open.

Public production remains NOT APPROVED.

