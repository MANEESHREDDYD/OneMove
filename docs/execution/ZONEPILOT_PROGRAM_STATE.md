# ZonePilot Program State

Updated: `2026-08-13T19:28:00Z`

This is a restart ledger, not runtime proof. GitHub checks, generated manifests, deployed health signals, and test output remain authoritative. The JSON companion contains the complete machine-readable state.

Repository boundary: `MANEESHREDDYD/OneMove` is the **public source repository**. Provider payloads, credentials, scheduled acquisition state, and private execution artifacts belong in a separate private repository or private managed storage and must never be committed here.

## Candidate

- PR `#1` remains open and unmerged on `ws/phase1-measurement`.
- Last fully green remote SHA: `9e88061f78bc835abfcd71e19a46530af801f219`.
- Current remote remediation SHA: `15ceedf2cd142e53587648fe791ccee9de9ddcce`. Node, SQL, Polyglot, and R1 Evidence pass; Python and Release Validation fail because their generic suites incorrectly invoke the OSRM smoke test without first generating its private execution artifacts.
- A local correction marks the OSRM smoke as `r1_evidence`, keeps its explicit hard-failing invocation in the evidence workflow, and adds a CI ownership regression test. Remote proof is pending a new commit.
- Base: `ef09d0f652148011944fff52eb2b822434077fc2`.

## Product state

| Milestone | Status | Evidence |
|---|---|---|
| R0.5 | **NO-GO / OWNER BLOCKED** | Private scheduled execution and hosted least-privilege credentials are unavailable. |
| R1 | **NO-GO / CURRENT REMEDIATION SHA RED** | The last product candidate was green, but the current public-boundary remediation SHA has a failed generic Python check. The dedicated current-SHA R1 Evidence job remains green. |
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

- Python source-boundary profile: `96 passed, 18 environment-dependent skips, 1 R1 evidence test deselected`; the OSRM smoke separately passes locally (`1 passed`). The earlier integrated environment remains `107 passed, 1 optional C-integration skip`, including live RLS and destructive DB concurrency.
- Root frontend: lint, typecheck, 62-route production build, and Vitest (`11 passed, 2 skipped`) pass.
- Observatory: clean install, lint, typecheck, and 6-route production build pass.
- Persistent Playwright: marketplace `5/5`; volunteer `5/5`, with real login/session, browser restart, offline IndexedDB assertion, explicit sync response, and database row proof.
- Dependency audit: zero critical/high findings. Three moderate findings remain in the dev-only `autocannon -> hyperid -> uuid` load-test chain; the suggested automated fix is a breaking downgrade.
- R1 remote data: Geofabrik checksum verified; `65,463` OSM nodes, `20,349` highway ways, `9,165` POIs, `94` H3 R8 cells; 27-file OSRM bundle; route `2,958.1 m / 332.3 s`; finite `3x3` matrix.

## First major gate

P0 is not zero on the current remediation SHA. At `15ceedf2cd142e53587648fe791ccee9de9ddcce`, Node `31735581378`, SQL `31735581418`, Polyglot `31735581409`, and R1 Evidence `31735581384` pass; Python `31735581415` and Release Validation `31735581428` fail because their clean checkouts have no generated OSRM graph. The PR remains unmerged.

The later documentation head `9e88061f78bc835abfcd71e19a46530af801f219` also passed the complete exact-SHA matrix: Node `31698786881`, Python `31698786691`, SQL `31698786788`, Polyglot `31698786735`, Release Validation `31698786988`, and R1 Evidence `31698786726`.

## Public exposure and account readiness

- Current-tree personal email and obsolete Supabase project identifiers are redacted. `OneMove.env` is explicitly ignored; both it and `.env.local` now permit only the owner, SYSTEM, and administrators.
- Static HMAC test fixtures are removed from the current tree. Tests use a cryptographically random per-process fallback unless the local Supabase environment supplies its own secret.
- No supplied credential appears in reachable remote Git history. GitHub reports zero open secret-scanning alerts, but code scanning has no analysis and Dependabot alerts are disabled.
- A personal email, obsolete project identifiers, local credential-shaped JWT fixtures, and raw/generated artifacts remain in already-published history. Purging them requires an owner-authorized coordinated rewrite of `main`, the PR branch, and tag `v1.0.0-polyglot-local-portfolio-go`; PR `#1` remains unmerged pending that decision.
- Vercel account/team access and a read-only Supabase PostgreSQL transaction authenticate. Supabase app keys return 401; Vercel has zero projects; Railway lacks an API token; Sentry has no management token; GitHub has no deployment environments, secrets, or variables.

## Owner-controlled blockers

- Create or grant access to the approved private execution repository.
- Provide the approved traffic-provider credential if TomTom remains selected.
- Link hosted staging/production Supabase, frontend, API, routing, Sentry/alerting, and secret-store accounts.
- Authorize merge only after every first-gate workflow is green on the exact candidate.

## Immediate resume sequence

1. Commit and verify the OSRM CI ownership correction on a new exact PR SHA; require every first-gate workflow to pass.
2. Obtain an explicit owner decision to rewrite published history/tag or accept the residual historical PII; do not merge before that decision.
3. After a safe merge and green `main`, create smaller release-identity, R2 temporal, R3 optimizer, and R6 production-platform branches.
