# ZonePilot

**Network Intelligence, Resilience & Decision Optimization for Physical Commerce.**

> Model the network. Break it. Optimize it. Explain the decision.

ZonePilot exists to answer one question:

> **How should a physical commerce network position capacity and react to uncertainty so customer service remains reliable at the lowest defensible cost?**

ZonePilot is **not** a food-delivery marketplace, **not** a Swiggy/Zomato clone, and **not** a generic
AI dashboard. It is a decision system for the operator of a physical network: build a verifiable model
of the road/zone network, stress it with scenarios, optimize capacity placement under uncertainty, and
attach an auditable evidence trail to every number it shows.

---

## Honest status

ZonePilot is **early**. One vertical slice — the R1 geospatial evidence pipeline — is real, executed,
hash-verified, and green in CI. Most of the product surface described in the architecture is scaffold
or missing. This README documents only what has actually been executed. Everything else is listed
under [Current Limitations](#current-limitations).

- **No backend is deployed.** The Observatory frontend is live at
  <https://zonepilot-observatory.vercel.app>, but there is no hosted ZonePilot API behind it.
- **No temporal observations have ever been collected.** Every scheduled acquisition run failed, and
  those workflows have since been removed from this public repository.
- **No forecasting model exists.**

Program-level tracking lives in [`docs/execution/ZONEPILOT_PROGRAM_STATE.md`](docs/execution/ZONEPILOT_PROGRAM_STATE.md).

### A note on this repository

This repository also still contains a **legacy application called "OneMove"** — a Next.js multi-sided
marketplace demo (`app/`, `analytics/`, `python/`, `java/`, `c/`, and most of `docs/*_REPORT.md`).
OneMove is being **progressively retired**. It is not part of ZonePilot, its documentation does not
describe ZonePilot, and its claims should not be read as ZonePilot capabilities.

Two Vercel deployments exist and they are **not** the same application:

| URL | Serves |
| --- | --- |
| <https://zonepilot-observatory.vercel.app> | The ZonePilot Observatory (`apps/observatory`), title `ZonePilot Observatory` |
| `onemove-zonepilot.vercel.app` | The **legacy OneMove marketplace** |

The Observatory deployment was cut from `666ade66f965df76097c557cdf419501b683db75` and recorded as
GitHub Deployment `5941546097` (`production`). All four routes — `/`, `/capture`, `/qc`,
`/system-health` — answer `200`. It is a **frontend only**: there is no ZonePilot API deployed behind
it, and Vercel is **not** connected to GitHub, so the deploy was a manual upload rather than a
push-to-deploy. See [`docs/operations/DEPLOYMENT_STATE.md`](docs/operations/DEPLOYMENT_STATE.md).

---

## The problem

An operator of a physical commerce network (couriers, riders, stores, dark stores, service techs)
continuously makes capacity decisions: where to position supply, how much buffer to hold, what to do
when a corridor degrades. Those decisions are usually made on:

- **Averages instead of distributions** — no representation of uncertainty, so the plan is tuned to a
  demand day that never actually happens.
- **Dashboards instead of decisions** — a chart tells you utilization was 71%; it does not tell you
  where to move three riders at 18:40.
- **Untraceable numbers** — a KPI cannot be traced back to the observation, the dataset version, the
  graph version, and the code SHA that produced it, so it cannot be defended or audited.
- **No counterfactual** — nobody can say what would have happened under the alternative plan, so no
  decision is ever really evaluated.

ZonePilot's design premise is that a capacity decision is only trustworthy if the network model, the
uncertainty, the optimization, and the evidence chain are all first-class and versioned together.

---

## Architecture overview

```
sources -> acquisition -> raw -> bronze -> DQ/quarantine -> silver -> gold
        -> temporal -> forecast / scenario / resilience / optimizer
        -> counterfactual -> economics -> decision ledger -> shadow ops
        -> API / Observatory
```

Only the geographic path through this pipeline (`sources -> raw -> gold -> API`) has ever executed
end to end with verified output. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the
layer-by-layer status (WORKING / PARTIAL / SCAFFOLD / MISSING).

| Component | Path | What it is |
| --- | --- | --- |
| API | `services/api/` | FastAPI app (`services.api.main:app`), read-only Observatory routes over verified artifacts |
| Geospatial collectors | `services/collectors/context/osm.py`, `services/collectors/gold.py` | Geofabrik OSM acquisition, pilot clip, canonical graph, H3 R8 Gold dataset |
| Routing | `services/routing/osrm_pipeline.py` | Digest-pinned OSRM graph build + route/matrix smoke |
| Evidence | `services/evidence/r1.py` | Re-hashes every R1 artifact and emits a sanitized evidence manifest |
| Temporal contracts | `services/temporal/contracts.py` | Availability-aware feature/prediction/outcome contracts |
| Optimizer engine | `services/zonepilot/optimization/` | Deterministic OR-Tools CP-SAT robust facility optimizer — **not reachable from the API** |
| Observatory UI | `apps/observatory/` | Next.js client with 4 routes (`/`, `/capture`, `/qc`, `/system-health`) |

---

## Verified capabilities

Everything in this section is traceable to an executed CI run on `main` at commit
**`666ade66f965df76097c557cdf419501b683db75`**.

### 1. R1 geospatial pipeline (executed, hash-verified)

Real data, not fixtures. `services/collectors/context/osm.py` downloads
`asia/india/southern-zone-latest.osm.pbf` from Geofabrik, verifies the published MD5 checksum, and
clips it with a digest-pinned `osmium` container to the pilot bounding box:

```
77.58, 12.90, 77.65, 12.98
```

That is roughly **68 km² of central Bengaluru** (HSR / Koramangala / Indiranagar corridor).
**It is not the whole city**, and no claim in this repository should be read as city-scale coverage.

### 2. R1 evidence manifest

Produced by `services/evidence/r1.py` in the `ZonePilot R1 Evidence` workflow. Values at
`666ade66f965df76097c557cdf419501b683db75`:

| Field | Value |
| --- | --- |
| `dataset_version` | `osm-bc92c2e263d3.code-666ade66f965` |
| `graph_version` | `1.1.0+c0f22beaa7f2` |
| `gold_schema_version` | `1.0.0` |
| `osm_nodes` | 65,479 |
| `osm_highway_ways` | 20,353 |
| `pois` | 9,161 |
| `h3_cells` | 94 (H3 resolution 8) |
| `dq_status` | `PASS` |
| OSRM image | pinned by digest `sha256:af5d4a83fb90086a43b1ae2ca22872e6768766ad5fcbb07a29ff90ec644ee409` |

Executed routing smoke over the built graph:

| Metric | Value |
| --- | --- |
| Route distance | 2,958.1 m |
| Route duration | 332.3 s |
| Matrix | 3 x 3 |
| Finite cells | 9 |
| Null cells | 0 |

The evidence builder **re-hashes the artifacts itself** and refuses to emit a manifest if any hash,
DQ status, or candidate code SHA fails to line up. See
[`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md).

> These counts and versions are **per-run, not fixed constants.** `dataset_version` embeds the source
> extract hash and the candidate code SHA, `graph_version` embeds the derived graph topology hash, and
> the OSM counts track whatever Geofabrik published that day. They change on every rebuild; only the
> hash chain binding them together is invariant.

### 3. Authenticated read APIs

Working, authenticated `GET` routes under `/api/v1` (`services/api/routers/observatory.py`):

- `/api/v1/zones`
- `/api/v1/zones/{zone_id}/state`
- `/api/v1/network/snapshots`
- `/api/v1/network/map-layers`
- `/api/v1/datasets`
- `/api/v1/data-health`
- `/api/v1/evidence/{entity_type}/{entity_id}`

Plus the release-identity gate in `services/api/routers/version.py`:

- `/api/v1/version` — authenticated. Returns `200` **only** when the deployed application identity
  (`ZONEPILOT_APP_VERSION`, a 40-hex `ZONEPILOT_GIT_SHA`, a semantic `ZONEPILOT_SCHEMA_VERSION`) is
  tied to Gold and OSRM artifacts whose SHA-256 hashes it **recomputes and compares** on every
  request. Placeholder, abbreviated, or floating identifiers are rejected. Every failure — missing
  config, stale manifest, hash mismatch, failed DQ — is the same opaque, retryable `503
  RELEASE_IDENTITY_UNAVAILABLE`, disclosing no path or value.
  See [`docs/operations/RELEASE_IDENTITY.md`](docs/operations/RELEASE_IDENTITY.md).

They serve the verified Gold/OSRM artifacts, not synthetic data. Full route reference, including the
routes that deliberately return `501`, is in [`docs/API.md`](docs/API.md).

### 4. Auth and operational hardening

- Supabase **JWKS-based** JWT verification with an `ES256` / `RS256` / `HS256` algorithm allowlist,
  issuer and audience validation, and key selection driven by the header algorithm so a public key
  can never be swapped for a shared secret. **No mock JWT path and no fallback signing secret.**
- Per-principal, per-bucket **rate limiting** (auth / expensive / authenticated) with a `429`
  `RATE_LIMITED` envelope and `retry-after`.
- **Request-ID / correlation-ID middleware**, JSON structured logs with sensitive-field redaction, and
  a **consistent error envelope** (`error.code`, `error.message`, `error.request_id`,
  `error.retryable`, `error.details`) on every failure path.
- `/healthz` (liveness), `/readyz` (checks the DB), and `/metrics` — token-gated and **disabled by
  default** (`ZONEPILOT_METRICS_ENABLED`).

Details and known gaps: [`docs/SECURITY.md`](docs/SECURITY.md).

### 5. Temporal contracts

`services/temporal/contracts.py` defines strict, frozen Pydantic contracts with:

- a **9-value evidence class enum**, and
- an enforced **`information_available_at <= decision_time`** leakage invariant (plus
  `issued_at <= information_available_at <= retrieved_at`),

covered by **10 tests** in `tests/temporal/test_temporal_foundations.py`. These are contracts only —
no temporal data has ever been written through them.

The same enum is the **single** evidence vocabulary in the system: `services/api/contracts/observatory.py`
imports it rather than redefining it, and `apps/observatory/src/lib/api/types.ts` mirrors it as a
closed TypeScript union. There is no second vocabulary anywhere in `services/api/`.

### 6. Deterministic optimizer engine

`services/zonepilot/optimization/` holds a deterministic OR-Tools CP-SAT robust facility-location
solver (`contracts.py`, `_cp_sat.py`, `_worker.py`, `solver.py`). It runs CP-SAT in a subprocess
worker, fails closed to a `SOLVER_ERROR` result rather than raising, and is covered by **23 tests** in
`tests/optimization/test_facility_optimizer.py`, including brute-force optimality checks and a timeout
path.

**The engine is not wired to anything.** On `main` at `666ade66`, `POST /api/v1/optimizations` still
returns `501 NOT_IMPLEMENTED`, and no optimization has ever been executed through the product.
Work to connect the engine to that route (R3) is **in flight and not merged**; until it lands, this
README describes the engine as unreachable because that is what `main` does.

### 7. CI

The public repository has **exactly seven workflows**, and all seven are green on `main` at
`666ade66`:

| Workflow | File | Result at `666ade66` |
| --- | --- | --- |
| Node.js CI | `ci.yml` | green — Vitest 11 passed, 2 skipped (legacy OneMove) |
| Python CI | `python-ci.yml` | green — ruff clean, **176 passed, 18 skipped, 1 deselected** |
| SQL Quality | `sql-quality.yml` | green |
| Polyglot CI | `polyglot-ci.yml` | green (Java / C legacy subsystems) |
| ZonePilot Release Validation | `zonepilot-release.yml` | green — **193 passed, 1 skipped, 1 deselected**, Vitest **18 passed**, Playwright **10 passed** |
| ZonePilot R1 Evidence | `zonepilot-r1-evidence.yml` | green — real pipeline executed, hash chain audited |
| CodeQL Security | `codeql.yml` | green, 0 open alerts |

The two pytest numbers differ for a real reason and neither is wrong: `Python CI` installs the
reviewed runtime manifests only, so the 18 tests that need optional extras (chiefly `ortools`) skip;
`ZonePilot Release Validation` installs the full stack and runs **193**. Security posture at the same
commit: **0 open CodeQL alerts, 0 secret-scanning alerts, 1 medium Dependabot alert.**

**There are no scheduled acquisition workflows in this repository.** The four that used to exist
(`zonepilot-midnight-acquisition.yml`, `zonepilot-intraday-acquisition.yml`,
`zonepilot-midnight-catchup.yml`, `zonepilot-data-maintenance.yml`) were deleted; the seven above are
the complete set.

`tests/execution/test_ci_contracts.py` enforces the public-repository boundary as a test, not a
convention. Its four boundary invariants: no public workflow may read a private provider secret,
invoke an acquisition scheduler, hold `contents: write` or push while running on a schedule, or
manage `data/rolling` state. Three further tests pin R1 OSRM smoke ownership, CodeQL language
coverage with SHA-pinned actions, and the exact runtime manifests the Python gates install.

`tests/execution/test_dependency_consistency.py` enforces the other half: Python dependencies have a
**single source**. `services/api/requirements.txt` includes the root set with
`-r ../../requirements.txt` instead of duplicating pins, so a package can no longer be pinned to two
different versions across manifests and make the combined install unsatisfiable.

---

## Evidence model

Every ZonePilot number is meant to carry its provenance. Nine evidence classes distinguish an
observation from a provider estimate from an assumption from a simulation, and staging/test classes
are explicitly non-usable for decisions:

`OBSERVED` · `PUBLIC_OFFICIAL` · `PUBLIC_GEOGRAPHIC` · `PROVIDER_ESTIMATED` · `DERIVED` ·
`SIMULATED` · `ASSUMPTION` · `STAGING_DO_NOT_USE` · `TEST_ONLY`

R1 artifacts are chained by SHA-256: source PBF -> clip -> roads/POIs -> Gold parquet -> OSRM graph
bundle, with every link tied to the candidate code SHA.

**Enforcement today is Python-only.** These classes are enforced by Pydantic contracts and by the
API response types that import the same enum — but **not by any database constraint**. There is no
`evidence_class` column, `CHECK`, enum type, or trigger in any merged migration. See
[`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md) for the full model and the enforcement gaps.

---

## How to run

Requirements: **Python >= 3.10** (CI uses 3.11), Node.js 22, and Docker (required for the OSM/OSRM
pipeline — `osmium` and OSRM both run as digest-pinned containers).

### API

```bash
python -m pip install -e ".[dev]"
PYTHONPATH=services/api python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```

Then:

```bash
curl http://127.0.0.1:8000/healthz
```

The `/api/v1` routes require a valid Supabase JWT and a mounted artifact root. Relevant environment
variables:

| Variable | Purpose |
| --- | --- |
| `SUPABASE_URL` | Derives the expected issuer and the JWKS URL |
| `SUPABASE_JWT_ISSUER` / `SUPABASE_JWT_AUDIENCE` | Override issuer / audience (audience defaults to `authenticated`) |
| `SUPABASE_JWKS_URL` / `SUPABASE_JWT_PUBLIC_KEY` | Asymmetric key source |
| `SUPABASE_JWT_SECRET` | Legacy `HS256` secret (only used when the token header says `HS256`) |
| `SUPABASE_JWT_ALGORITHMS` | Narrow the algorithm allowlist |
| `ZONEPILOT_DATA_ROOT` | Root of the mounted artifact tree (`<root>/private/official/...`) |
| `ZONEPILOT_ALLOWED_ORIGINS` | CORS allowlist |
| `ZONEPILOT_DB_URL` | Checked by `/readyz` |
| `ZONEPILOT_RATE_LIMIT_ENABLED`, `ZONEPILOT_API_RATE_LIMIT_PER_MINUTE`, `ZONEPILOT_AUTH_RATE_LIMIT_PER_MINUTE`, `ZONEPILOT_EXPENSIVE_RATE_LIMIT_PER_MINUTE` | Rate limiting |
| `ZONEPILOT_METRICS_ENABLED`, `ZONEPILOT_METRICS_TOKEN` | `/metrics` exposure (off by default) |

Without a mounted artifact root the Observatory routes return `503 DATASET_NOT_READY` — that is the
designed fail-closed behaviour, not a bug.

### R1 geospatial pipeline

Requires Docker and downloads a multi-hundred-megabyte PBF. This is what the
`ZonePilot R1 Evidence` workflow runs:

```bash
export ZONEPILOT_DATA_ROOT="$PWD/.zonepilot-r1-data"
python -m services.collectors.context.osm      # download, checksum, clip, roads + POIs
python -m services.collectors.gold             # canonical graph, H3 R8, Gold parquet
python -m services.routing.osrm_pipeline       # digest-pinned OSRM graph build
python -m pytest tests/pipeline/test_osrm_smoke.py -v
python -m services.evidence.r1 \
  --data-root "$ZONEPILOT_DATA_ROOT" \
  --output artifacts/r1_evidence_manifest.json
```

Outputs land under `$ZONEPILOT_DATA_ROOT/private/official/` and are git-ignored.

### Observatory UI

```bash
cd apps/observatory
npm install
npm run dev
```

---

## How to test

```bash
# Full Python suite. 176 passed / 18 skipped / 1 deselected with the base runtime manifests
# (as `Python CI` runs it); 193 passed / 1 skipped / 1 deselected with the full stack installed
# (as `ZonePilot Release Validation` runs it). Both were green on main @ 666ade66.
python -m pytest -m "not r1_evidence" -q

# Focused suites
python -m pytest tests/temporal/ -q       # 10 temporal contract tests
python -m pytest tests/api/ -q            # auth, JWT security, middleware, role attacks
python -m pytest tests/evidence/ -q       # R1 evidence manifest validation
python -m pytest tests/optimization/ -q   # 23 optimizer tests (needs ortools)
python -m pytest tests/execution/ -q      # program state, CI boundary, dependency consistency

# Lint
python -m ruff check .
```

Python dependencies are single-sourced: install with
`pip install -r requirements.txt -r services/api/requirements.txt`, where the second file includes the
first. Do not add a duplicate pin to both.

The `r1_evidence` marker is deselected by default because those tests require Docker and a mounted
artifact root; the `ZonePilot R1 Evidence` workflow is what runs them.

Node-side checks (`npm run lint`, `npm run typecheck`, `npm test`) currently cover the **legacy
OneMove** application. The 18 Vitest tests and 10 Playwright tests in `ZonePilot Release Validation`
are all OneMove tests — `apps/observatory` has **zero tests of its own**, including for the live
`/system-health` route.

---

## Current Limitations

These are limitations, not roadmap items. Nothing here is partially working.

**Data acquisition**
- **No data acquisition has ever succeeded. Zero temporal observations exist.** Every scheduled
  acquisition run failed (113 of 113) before those four workflows were **removed from this public
  repository** — the public repo no longer schedules private provider acquisition at all. Removing
  them ended the failing runs; it did not produce any data.
- **No traffic data and no weather data have been collected.** Collector modules exist
  (`services/collectors/traffic/tomtom`, `services/collectors/context/openmeteo.py`,
  `services/collectors/platforms/`) but have never produced a verified dataset.
- **No temporal observations exist at all.** The bronze/silver/DQ/quarantine path has never processed
  a real observation.

**Intelligence**
- **No forecasting model.** Status: `ZONEPILOT_FORECAST_MODEL_NOT_TRAINED`.
- **No uncertainty quantification and no conformal calibration.**
- **The optimizer engine is on `main` but unreachable from the product.**
  `services/zonepilot/optimization/` is real, deterministic, and tested (23 tests), yet
  `POST /api/v1/optimizations` still returns `501 NOT_IMPLEMENTED`. No optimization has ever been run
  through the API. Shipping the engine did not ship the capability. **R3 is not done**, and the work
  to wire the engine to the route is in flight but unmerged.
- **No resilience engine, no counterfactual engine, no economics engine.**
- **No decision ledger, no shadow operations, no experiment registry.**
- **No LLM tool layer.**
- Scenario routes are `501` / `404` stubs.

**Deployment and durability**
- **No backend is deployed anywhere, so the live Observatory has no API to talk to.** Railway has no
  usable token, so the FastAPI app has never been hosted. Its release gate `GET /api/v1/version` has
  therefore never run against a deployment, and the proxy in the deployed frontend still defaults to
  `http://127.0.0.1:8000`.
- The Observatory frontend **is** deployed at <https://zonepilot-observatory.vercel.app> (cut from
  `666ade66`, GitHub Deployment `5941546097`), but **Vercel has no GitHub connection** for this
  project — there is no push-to-deploy, and every deploy is a manual upload. The deployment record is
  written by hand after the fact, so the deployed bundle is **asserted** to match a commit, not
  **proven** to; the next merge to `main` will silently leave production behind.
- `onemove-zonepilot.vercel.app` still serves the **legacy OneMove marketplace**, not ZonePilot.
- A hosted Supabase project exists (ref `puygqvnhwsjkspoprfkb`, `ACTIVE_HEALTHY`, `ap-southeast-1`,
  JWKS serving `ES256`). It is provisioned, not integrated into a running ZonePilot deployment.
- A Sentry org (`onemove`) exists and a test event was proven received, but **the Observatory has zero
  Sentry instrumentation** — no `@sentry/nextjs` dependency and no config — so **no real frontend
  error will ever reach Sentry.** Only the FastAPI app has a Sentry path
  (`services/api/core/telemetry.py`, gated on `SENTRY_DSN`), and that app is not deployed.
- **No durable artifact storage.** R1 evidence lives only in **GitHub Actions artifacts with 30-day
  retention**. After 30 days the evidence for a given commit is gone unless it was regenerated.

**Coverage and correctness gaps**
- Pilot coverage is **~68 km² of central Bengaluru**, not a city and not multiple cities.
- Observatory UI has only **4 routes** (`/`, `/capture`, `/qc`, `/system-health`) and **zero tests**.
- **Role checks are inert** — `required_role` is only ever set in a test, never in application code.
- **`workspace_id` exists in no merged migration**, so multi-tenant isolation is not enforceable at
  the API layer. See [`docs/SECURITY.md`](docs/SECURITY.md).
- Evidence classes are enforced by **Python and TypeScript contracts only, not by database
  constraints**.

---

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layered architecture with per-layer WORKING / PARTIAL / SCAFFOLD / MISSING status |
| [`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md) | The 9 evidence classes, how they are enforced, and the R1 hash chain |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Auth model, JWKS verification, rate limiting, repo boundary, known gaps |
| [`docs/API.md`](docs/API.md) | Route-by-route `/api/v1` reference, working vs `501` |
| [`docs/operations/RELEASE_IDENTITY.md`](docs/operations/RELEASE_IDENTITY.md) | The `GET /api/v1/version` release gate and its required deployment configuration |
| [`docs/operations/DEPLOYMENT_STATE.md`](docs/operations/DEPLOYMENT_STATE.md) | What is actually deployed, what is only provisioned, and what is not wired |
| [`docs/execution/ZONEPILOT_PROGRAM_STATE.md`](docs/execution/ZONEPILOT_PROGRAM_STATE.md) | Live program state and blockers |

Files matching `docs/*_REPORT.md` are **legacy OneMove** artifacts retained for history. They do not
describe ZonePilot and are not maintained.
