# Secrets Rotation Checklist

Audit date: 2026-06-10

Status: public or preview deployment is blocked until Supabase database password and all shared secrets are rotated and verified. The Supabase DB password was previously shared in chat, so the current secret set must be treated as exposed.

## Repository Checks

Current repository checks performed before the final audit:

- `git pull origin main` completed; branch was already up to date.
- `git status --short --branch` reviewed the dirty worktree before changes.
- `.env.local` is local and ignored; it is not tracked.
- `.env`, `.env.local`, `.env*.local`, `.venv/`, `test-results/`, `playwright-report/`, and `playwright/.auth/` are covered by ignore rules.
- `git ls-files .env.local .env .venv test-results playwright-report` returned no tracked files.
- Secret-pattern scan found demo credentials/placeholders and environment variable names, not staged private Supabase keys or database passwords.

## Required Before Any Preview/Public Deployment

1. Rotate the Supabase database password.
2. Rotate Supabase service role key if it was shared or copied outside local private storage.
3. Rotate Supabase anon key if the project policy requires key replacement after exposure.
4. Rotate any shared JWT secrets, webhook secrets, map/provider keys, payment keys, or CI tokens.
5. Replace local `.env.local` values with the rotated values.
6. Update the deployment environment variables with the rotated values.
7. Verify the old DB password no longer connects.
8. Verify old service keys no longer work if rotated.
9. Run `npm run validate:env`.
10. Run `npm run healthcheck`.
11. Run `npm run test:rls`.
12. Confirm `git status --short` does not show `.env.local`, `.env`, `.venv`, `test-results`, `playwright-report`, or `playwright/.auth`.

## Staging Rules

Before commit or push:

- Do not stage `.env.local`.
- Do not stage private credentials.
- Do not stage Supabase service keys.
- Do not stage a DB password.
- Do not stage `.venv`.
- Do not stage `test-results` or `playwright-report`.
- Do not stage Playwright auth session files.
- Do not stage generated junk.

## Final Deployment Gate

Production-preview readiness can only be marked GO after secrets are rotated and the final validation suite passes with the rotated credentials. Public real marketplace production remains NOT APPROVED even after rotation because real payments, compliance, observability, rate limiting, and incident operations are not implemented.

