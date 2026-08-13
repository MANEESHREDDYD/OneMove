# ZonePilot Program State

Updated: `2026-08-13T19:19:49Z`

This is a restart ledger, not runtime proof. GitHub checks, generated manifests, deployed health signals, and test output remain authoritative. The JSON companion contains the complete machine-readable state.

Repository boundary: `MANEESHREDDYD/OneMove` is the **public source repository**. Provider payloads, credentials, scheduled acquisition state, and private execution artifacts belong in a separate private repository or private managed storage and must never be committed here.

## Candidate

- PR `#1` remains open and unmerged on `ws/phase1-measurement`.
- Last fully audited remote SHA: `45153cf986e81aeac0083fdb3b4556f2a7735ab4`.
- Node, Python, SQL, Polyglot, Release Validation, and R1 Evidence all pass on that exact SHA.
- Base: `ef09d0f652148011944fff52eb2b822434077fc2`.

## Product state

| Milestone | Status | Evidence |
|---|---|---|
| R0.5 | **NO-GO / OWNER BLOCKED** | Private scheduled execution and hosted least-privilege credentials are unavailable. |
| R1 | **FIRST MAJOR GATE GREEN / OWNER MERGE PENDING** | Real auth, protected artifact APIs, evidence-bearing map layers, provider health, current-SHA Gold/OSRM evidence, and required persistent E2Es pass remotely. |
| R2 | **FOUNDATIONS PARTIAL** | UTC temporal contracts, point-in-time joins, chronological splits, and prediction/outcome records are tested. No real traffic history, trained model, or prospective result exists. |
| R3 | **NOT STARTED** | Optimizer API retains typed `NOT_IMPLEMENTED`; no solver result is claimed. |
| R4 | **NOT STARTED** | No resilience experiments or counterfactual result is claimed. |
| R5 | **NOT STARTED** | No ZonePilot economics or experiment registry result is claimed. |
| R6 | **PARTIAL / OWNER BLOCKED** | API logging, metrics, readiness, optional Sentry activation, safe errors, CORS, and rate limiting exist; hosted environments, alerts, restore proof, and measured load budgets do not. |
| R7 | **NOT STARTED** | No shadow decision freeze/outcome loop is claimed. |
| R8 | **SCAFFOLD ONLY** | No authoritative ZonePilot LLM layer or fine-tuning result is claimed. |
| R9 | **NOT STARTED** | Final product gate is not met. |

Conservative whole-product estimates: implemented `32%`, verified `31%`, release-ready `18%`.

## Local integrated evidence

- Python: `107 passed, 1 optional C-integration skip`, including live RLS, OSRM, and destructive DB concurrency.
- Root frontend: lint, typecheck, 62-route production build, and Vitest (`11 passed, 2 skipped`) pass.
- Observatory: clean install, lint, typecheck, and 6-route production build pass.
- Persistent Playwright: marketplace `5/5`; volunteer `5/5`, with real login/session, browser restart, offline IndexedDB assertion, explicit sync response, and database row proof.
- Dependency audit: zero critical/high findings. Three moderate findings remain in the dev-only `autocannon -> hyperid -> uuid` load-test chain; the suggested automated fix is a breaking downgrade.
- R1 remote data: Geofabrik checksum verified; `65,463` OSM nodes, `20,349` highway ways, `9,165` POIs, `94` H3 R8 cells; 27-file OSRM bundle; route `2,958.1 m / 332.3 s`; finite `3x3` matrix.

## First major gate

P0 is zero. Exact-SHA runs are green: Node `31698148020`, Python `31698148012`, SQL `31698148069`, Polyglot `31698148072`, Release Validation `31698148097`, and R1 Evidence `31698148033`. The PR remains unmerged pending owner authorization.

The later documentation head `9e88061f78bc835abfcd71e19a46530af801f219` also passed the complete exact-SHA matrix: Node `31698786881`, Python `31698786691`, SQL `31698786788`, Polyglot `31698786735`, Release Validation `31698786988`, and R1 Evidence `31698786726`.

## Public exposure and account readiness

- Current-tree personal email and obsolete Supabase project identifiers are redacted. `OneMove.env` is explicitly ignored and its ACL now permits only the owner, SYSTEM, and administrators.
- No supplied credential appears in reachable remote Git history. GitHub reports zero open secret-scanning alerts. Historical JWT-shaped values are synthetic fixtures, and archived browser tokens target localhost test services.
- A personal email and obsolete project identifiers remain in already-published `main` history and tag `v1.0.0-polyglot-local-portfolio-go`. Purging them requires an owner-authorized coordinated history rewrite; PR `#1` remains unmerged pending that decision.
- Vercel account/team access and a read-only Supabase PostgreSQL transaction authenticate. Supabase app keys return 401; Vercel has zero projects; Railway lacks an API token; Sentry has no management token; GitHub has no deployment environments, secrets, or variables.

## Owner-controlled blockers

- Create or grant access to the approved private execution repository.
- Provide the approved traffic-provider credential if TomTom remains selected.
- Link hosted staging/production Supabase, frontend, API, routing, Sentry/alerting, and secret-store accounts.
- Authorize merge only after every first-gate workflow is green on the exact candidate.

## Immediate resume sequence

1. Verify the current-tree exposure remediation on the new exact PR SHA.
2. Obtain an explicit owner decision to rewrite published history/tag or accept the residual historical PII; do not merge before that decision.
3. After a safe merge and green `main`, create smaller release-identity, R2 temporal, R3 optimizer, and R6 production-platform branches.
