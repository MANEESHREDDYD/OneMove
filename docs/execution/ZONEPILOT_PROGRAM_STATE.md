# ZonePilot Program State

Updated: `2026-08-13T11:50:00Z`

This is a restart ledger, not runtime proof. GitHub checks, generated manifests, deployed health signals, and test output remain authoritative. The JSON companion contains the complete machine-readable state.

## Candidate

- PR `#1` remains open and unmerged on `ws/phase1-measurement`.
- Last audited remote SHA: `483c8e1f6d256c39987d3780ffdb342f935f7ac2`.
- The integrated worktree is locally green but not yet represented by that remote SHA.
- Base: `ef09d0f652148011944fff52eb2b822434077fc2`.

## Product state

| Milestone | Status | Evidence |
|---|---|---|
| R0.5 | **NO-GO / OWNER BLOCKED** | Private scheduled execution and hosted least-privilege credentials are unavailable. |
| R1 | **INTEGRATED LOCALLY / REMOTE GATE PENDING** | Real auth, protected artifact APIs, evidence-bearing map layers, provider health, Gold/OSRM evidence, and required persistent E2Es pass locally. No completion claim is made before the new exact SHA is green remotely. |
| R2 | **FOUNDATIONS PARTIAL** | UTC temporal contracts, point-in-time joins, chronological splits, and prediction/outcome records are tested. No real traffic history, trained model, or prospective result exists. |
| R3-R9 | **NOT STARTED or scaffold-only** | Scenario and optimizer APIs retain typed `NOT_IMPLEMENTED`; no research/result claim is made. |

Conservative whole-product estimates: implemented `32%`, verified `29%`, release-ready `16%`.

## Local integrated evidence

- Python: `107 passed, 1 optional C-integration skip`, including live RLS, OSRM, and destructive DB concurrency.
- Root frontend: lint, typecheck, 62-route production build, and Vitest (`11 passed, 2 skipped`) pass.
- Observatory: clean install, lint, typecheck, and 6-route production build pass.
- Persistent Playwright: marketplace `5/5`; volunteer `5/5`, with real login/session, browser restart, offline IndexedDB assertion, explicit sync response, and database row proof.
- Dependency audit: zero critical/high findings. Three moderate findings remain in the dev-only `autocannon -> hyperid -> uuid` load-test chain; the suggested automated fix is a breaking downgrade.
- R1 data: Geofabrik checksum verified; `65,459` OSM nodes, `20,344` highway ways, `9,163` POIs, `94` H3 R8 cells; 27-file OSRM bundle; route `2,255.4 m / 259.4 s`; finite `3x3` matrix.

## Open release failure

`RELEASE-REMOTE-001` is the only P0: no remote workflow has evaluated the integrated worktree. Historical Release Validation runs `31388230404` and `31388225519` remain failed against the pre-fix SHA and must not be cited as current success.

## Owner-controlled blockers

- Create or grant access to the approved private execution repository.
- Provide the approved traffic-provider credential if TomTom remains selected.
- Link hosted staging/production Supabase, frontend, API, routing, Sentry/alerting, and secret-store accounts.
- Authorize merge only after every first-gate workflow is green on the exact candidate.

## Immediate resume sequence

1. Commit and push the integrated batch without local credentials, private artifacts, or scratch files.
2. Monitor Node, Python, SQL, Polyglot, Release Validation, and R1 Evidence on the exact SHA.
3. Retrieve logs and repair every failure; repeat until the complete remote matrix is green.
4. Persist the verified run IDs and request owner merge authorization.
