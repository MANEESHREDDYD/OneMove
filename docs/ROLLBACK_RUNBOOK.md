# Rollback Runbook

Audit date: 2026-06-10

This rollback runbook is a documented process, not proof of automated one-click rollback.

## Trigger Conditions

Rollback if any production-preview deployment shows:

- 500s on core role dashboards.
- Authentication loops or broken sign out.
- Cross-tenant data exposure.
- Failed `npm run test:rls`.
- Failed healthcheck required checks.
- Broken customer checkout or ride booking smoke.
- Broken merchant order queue.
- Broken partner jobs flow.

## Application Rollback

1. Identify the last known good commit.
2. Redeploy the last known good build artifact or commit.
3. Confirm environment variables remain rotated.
4. Run smoke checks for `/showcase`, `/customer/rides`, `/merchant`, `/partner`, `/admin/command-center`, and `/admin/system-health`.
5. Run `npm run healthcheck`.
6. Run `npm run test:rls`.
7. Record the incident in the bug log with severity and root cause.

## Database Rollback

1. Do not run destructive rollback commands against production data without a verified backup.
2. Prefer forward fixes for schema/data migrations.
3. If rollback is required, restore from a verified Supabase backup or point-in-time recovery snapshot.
4. Re-run RLS tests after restore.
5. Re-run data integrity checks after restore.

## Demo Data Reset

For local synthetic data only:

- Run `npm run demo:reset`.
- Scope: rows marked `is_demo=true` and demo auth accounts.
- Do not use this command as a production data rollback.

