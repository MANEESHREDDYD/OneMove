# Repository Cleanup Plan

| File/path | Category | Reason for removal | Reference check result | Risk level | Action |
| --- | --- | --- | --- | --- | --- |
| `tests/e2e/final-cross-role-flows.spec.ts` | duplicate e2e spec | Superseded by `onemove-realtime-marketplace.spec.ts` | No references outside final-*.spec | Low | Delete |
| `tests/e2e/final-error-boundary.spec.ts` | duplicate e2e spec | Superseded by `onemove-error-handling.spec.ts` | No references outside final-*.spec | Low | Delete |
| `tests/e2e/final-map-and-realtime-fallback.spec.ts` | duplicate e2e spec | Superseded by `onemove-map-rendering.spec.ts` | No references outside final-*.spec | Low | Delete |
| `tests/e2e/final-mobile-responsive.spec.ts` | duplicate e2e spec | Superseded by `onemove-mobile.spec.ts` | No references outside final-*.spec | Low | Delete |
| `tests/e2e/final-production-preview-audit.spec.ts` | duplicate e2e spec | Superseded by `onemove-local-production-smoke.spec.ts` | No references outside final-*.spec | Low | Delete |
| `tests/e2e/final-security-isolation.spec.ts` | duplicate e2e spec | Superseded by `onemove-role-security.spec.ts` | No references outside final-*.spec | Low | Delete |
| `tests/e2e/helpers/finalAuditHelpers.ts` | unused e2e helper | Only used by duplicate specs | 0 outside references | Low | Delete |
| `docs/*_FIX_REPORT.md` (e.g. `MAPS_CRASH_FIX_REPORT.md`) | stale fix report | Old one-off fix artifacts | No references | Low | Delete |
| `docs/*_QA_REPORT.md` (except `QA_MASTER_FINAL_REPORT.md`) | old QA report | Superseded by final master report | No references | Low | Delete |
| `docs/LOCALHOST_*.md` | old validation report | Superseded by final audit | No references | Low | Delete |
| `docs/BUG_REPORT.md`, `SIGNOUT_BUG_REPORT.md`, etc. | stale bug reports | Merged into `MASTER_BUG_LOG.md` | No references | Low | Delete |
| `docs/SUPABASE_*.md` | old setup outputs | Old one-off outputs | No references | Low | Delete |

**Files explicitly Kept (Risk: High / Required for final portfolio):**
- Core `.ts/.tsx` and Next.js setup files.
- `onemove-*.spec.ts` (Active E2E tests referenced in package.json)
- `python/`, `java/`, `c/`, `data/demo_exports`
- Final documentation (`QA_MASTER_FINAL_REPORT.md`, `DEPLOYMENT_RUNBOOK.md`, `POLYGLOT_ARCHITECTURE_REPORT.md`, etc.)
