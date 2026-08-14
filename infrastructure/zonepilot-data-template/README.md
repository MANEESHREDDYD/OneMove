# ZonePilot Private Data Repository - Bootstrap Template

This directory contains the canonical templates required to bootstrap the private `MANEESHREDDYD/ZonePilot-Data` repository once provisioned.

## Required Secrets & Variables (GitHub Actions)

### Secrets
1. `ZONEPILOT_DB_URL`: Production Supabase Pooler URL for the `zonepilot_collector` role.
2. `TOMTOM_API_KEY`: TomTom API Key.
3. `OPENMETEO_API_KEY`: (Optional) If commercial API tier is used.

### Variables
1. `ZONEPILOT_CODE_SHA`: The pinned SHA from `MANEESHREDDYD/OneMove` that all data collection workflows must execute against.

## Security Checklist
- [ ] Repository visibility is set to **Private**.
- [ ] No database passwords are hardcoded in the repo.
- [ ] Workflows are restricted from running external PRs.
- [ ] Artifact retention is configured to 365 days for Midnight bundles.
- [ ] Artifact retention is configured to 2 days for Intraday bundles.

## Bootstrapping Steps
1. Create `MANEESHREDDYD/ZonePilot-Data`.
2. Configure Secrets and Variables.
3. Copy `.github/workflows/*.yml` from this template to the private repo.
4. Trigger the `zonepilot-smoke-test.yml` via `workflow_dispatch`.
