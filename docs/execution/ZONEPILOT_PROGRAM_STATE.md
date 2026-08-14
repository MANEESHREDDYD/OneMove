# ZonePilot Program State

Updated: `2026-08-14T08:46:21Z`

This ledger is a restart aid, not runtime proof. Exact GitHub checks, provider health, immutable manifests, and test output remain authoritative.

## Current public release

- PR `#1` is merged.
- Main is `43b96185fd8754a959d365b6a202eb673e7b0b9d`.
- Node `31783549508`, Python `31783549482`, SQL `31783549531`, Polyglot `31783549517`, Release Validation `31783549521`, R1 Evidence `31783549514`, and CodeQL `31783549525` all succeeded on that exact SHA.
- Main requires pull requests and strict current-base checks across all seven gate families. Admin bypass, force pushes, and branch deletion are disabled.
- Secret scanning and push protection are enabled. Open secret-scanning alerts: zero.

## Public-history remediation

A private verified recovery bundle and fingerprint-only rewrite manifest were created before filtering. Main, the feature branch, the public tag, and pull refs were surgically rewritten. A fresh remote mirror found zero audited generated/private paths, known bad objects, JWTs, personal consumer-email metadata, obsolete project refs, static signing literals, or exact locally supplied credential values.

Old objects are no longer reachable from advertised refs. GitHub can still serve some old objects by exact object ID until garbage collection or Support cleanup; immediate provider-side purge remains open.

## Milestone state

| Milestone | Status | Evidence |
|---|---|---|
| R0.5 | **SCAFFOLD GREEN / EXECUTION NO-GO** | Private `MANEESHREDDYD/ZonePilot-Data` exists at `41e6fe18141f2c44a333fa9584defe1667fa0547`; validation is green and the exact public SHA contract is enforced. The executor intentionally exits 78 until real least-privilege DB/storage/provider credentials and adapters exist. |
| R1 | **MERGED / EXACT GATES GREEN** | Authenticated artifact-backed product, OSM/Gold/OSRM evidence, map, provider health, and truthful traffic-unavailable state passed the dedicated main workflow. |
| R2 | **ENGINEERING COMPLETE / EVIDENCE ACCUMULATING** | UTC contracts, PIT joins, temporal splits, prospective freeze, prediction records, and outcome records are tested. No fabricated history or outcome superiority is claimed. |
| R3-R5 | **NOT COMPLETE** | Deterministic optimizer, resilience, and economics outcome evidence remain to be built and observed. |
| R6 | **PARTIAL** | GitHub controls and local API hardening exist. Hosted Supabase, Railway, Sentry, backups/restores, alerts, and rollback evidence are blocked by unavailable management access. Vercel provisioning is active. |
| R7 | **FOUNDATION ONLY** | Private immutable manifest and reconciliation contracts exist; real shadow operations have not run. |
| R8 | **SCAFFOLD ONLY** | Deterministic engines remain the priority. Fine-tuning is not justified. |
| R9 | **PARTIAL** | Public history, CI, security gates, and execution ledger are materially improved; hosted product proof is incomplete. |

Conservative whole-product estimates: implemented `36%`, verified `35%`, release-ready `20%`.

## Active security follow-up

Main has one medium CodeQL finding in the legacy admin MLOps route and 25 Dependabot alerts, including 10 high Python findings. The protected follow-up branch:

- removes server-side shell execution;
- enforces authenticated admin access and returns a structured fail-closed `503` until a durable executor exists;
- pins patched PyJWT, cryptography, pyarrow, pytest, pydantic, Supabase, and H3-compatible versions;
- makes root and API requirement sets resolve together;
- declares API runtime dependencies that were previously supplied only by CI;
- adds weekly grouped Dependabot configuration.

Local evidence: Ruff passes; root lint has zero errors; root typecheck passes; a clean virtual environment reports `99 passed, 17 skipped, 1 R1 evidence test deselected`.

## Private execution boundary

Private scheduled execution and licensed/provider data belong only in `MANEESHREDDYD/ZonePilot-Data` or approved private managed storage. The private repository has staging and production environments plus the approved public SHA/repository variables. It has no runtime secrets. Private branch protection and environment wait timers are unavailable on the current GitHub plan.

## External capability blockers

- Supabase project creation requires a valid management access token. The configured hosted ref is NXDOMAIN; direct DB/application credentials cannot create separate staging and production projects.
- The supplied Railway candidate returns `AUTH_REJECTED` in every documented token mode. A workspace-scoped `RAILWAY_API_TOKEN` is required.
- Sentry project and alert management require an organization auth token; a DSN is ingestion-only.
- Immediate GitHub deletion of unreachable old objects requires Support cleanup because no repository API exposes that operation.
- GitHub private-repository branch protection and protected wait timers require a supporting paid plan.

TomTom is separately owned and is not a blocker for the deterministic main program.

## Resume sequence

1. Push the security/dependency baseline, require all exact-SHA checks, clear the CodeQL finding and high dependency alerts, merge, and reverify main.
2. Complete Vercel Preview/Production provisioning and hosted smoke evidence.
3. Provision distinct hosted staging/production data and API infrastructure as soon as valid provider management access exists.
4. Implement the private acquisition/state/object/manifest executor using least-privilege identities and prove restore/reconciliation.
5. Continue deterministic R3-R7 engineering without fake traffic or business-outcome claims.
