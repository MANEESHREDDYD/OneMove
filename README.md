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

- **Nothing is deployed.** No hosted backend exists.
- **No temporal observations have ever been collected.** Every scheduled acquisition run has failed.
- **No forecasting model exists.**

Program-level tracking lives in [`docs/execution/ZONEPILOT_PROGRAM_STATE.md`](docs/execution/ZONEPILOT_PROGRAM_STATE.md).

### A note on this repository

This repository also still contains a **legacy application called "OneMove"** — a Next.js multi-sided
marketplace demo (`app/`, `analytics/`, `python/`, `java/`, `c/`, and most of `docs/*_REPORT.md`).
OneMove is being **progressively retired**. It is not part of ZonePilot, its documentation does not
describe ZonePilot, and its claims should not be read as ZonePilot capabilities. The public URL
`onemove-zonepilot.vercel.app` serves the **legacy OneMove marketplace**, not ZonePilot.

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
| Observatory UI | `apps/observatory/` | Next.js client with 3 routes (`/`, `/capture`, `/qc`) |

---

## Verified capabilities

Everything in this section is traceable to an executed CI run on `main` at commit
**`502e20817d4319d6867090b7765fe35326973e67`**.

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
`502e20817d4319d6867090b7765fe35326973e67`:

| Field | Value |
| --- | --- |
| `dataset_version` | `osm-b87981dd6e64.code-502e20817d43` |
| `graph_version` | `1.1.0+fa711557c25b` |
| `gold_schema_version` | `1.0.0` |
| `osm_nodes` | 65,463 |
| `osm_highway_ways` | 20,349 |
| `pois` | 9,165 |
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

### 3. Authenticated read APIs

Working, authenticated `GET` routes under `/api/v1` (`services/api/routers/observatory.py`):

- `/api/v1/zones`
- `/api/v1/zones/{zone_id}/state`
- `/api/v1/network/snapshots`
- `/api/v1/network/map-layers`
- `/api/v1/datasets`
- `/api/v1/data-health`
- `/api/v1/evidence/{entity_type}/{entity_id}`

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

covered by **9 tests** in `tests/temporal/test_temporal_foundations.py`. These are contracts only —
no temporal data has ever been written through them.

### 6. CI

All green on `main` at `502e2081`:

`Node.js CI` · `Python CI` · `SQL Quality` · `Polyglot CI` · `ZonePilot Release Validation` ·
`ZonePilot R1 Evidence` · `CodeQL`

**116 pytest tests passing** on that commit. Security posture at the same point: **0 open CodeQL
alerts, 0 secret-scanning alerts, 2 medium Dependabot alerts.**

---

## Evidence model

Every ZonePilot number is meant to carry its provenance. Nine evidence classes distinguish an
observation from a provider estimate from an assumption from a simulation, and staging/test classes
are explicitly non-usable for decisions:

`OBSERVED` · `PUBLIC_OFFICIAL` · `PUBLIC_GEOGRAPHIC` · `PROVIDER_ESTIMATED` · `DERIVED` ·
`SIMULATED` · `ASSUMPTION` · `STAGING_DO_NOT_USE` · `TEST_ONLY`

R1 artifacts are chained by SHA-256: source PBF -> clip -> roads/POIs -> Gold parquet -> OSRM graph
bundle, with every link tied to the candidate code SHA.

**Enforcement today is Python-only.** These classes are enforced by Pydantic contracts, not by
database constraints. See [`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md) for the full model and
the enforcement gaps.

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
# Full Python suite (116 passing on main @ 502e2081)
python -m pytest -q

# Focused suites
python -m pytest tests/temporal/ -q       # 9 temporal contract tests
python -m pytest tests/api/ -q            # auth, JWT security, middleware, role attacks
python -m pytest tests/evidence/ -q       # R1 evidence manifest validation
python -m pytest tests/execution/ -q      # program-state and CI contract assertions

# Lint
python -m ruff check .
```

Node-side checks (`npm run lint`, `npm run typecheck`, `npm test`) currently cover the **legacy
OneMove** application. `apps/observatory` has **zero tests**.

---

## Current Limitations

These are limitations, not roadmap items. Nothing here is partially working.

**Data acquisition**
- **No data acquisition has ever succeeded.** The scheduled acquisition workflows have failed
  **113 out of 113 runs**.
- **No traffic data and no weather data have been collected.** Collector modules exist
  (`services/collectors/traffic/tomtom`, `services/collectors/context/openmeteo.py`,
  `services/collectors/platforms/`) but have never produced a verified dataset.
- **No temporal observations exist at all.** The bronze/silver/DQ/quarantine path has never processed
  a real observation.

**Intelligence**
- **No forecasting model.** Status: `ZONEPILOT_FORECAST_MODEL_NOT_TRAINED`.
- **No uncertainty quantification and no conformal calibration.**
- **Optimizer engine code exists, but `POST /api/v1/optimizations` returns `501 NOT_IMPLEMENTED`.**
  No optimization has ever been run through the API.
- **No resilience engine, no counterfactual engine, no economics engine.**
- **No decision ledger, no shadow operations, no experiment registry.**
- **No LLM tool layer.**
- Scenario routes are `501` / `404` stubs.

**Deployment and durability**
- **Nothing is deployed.** No ZonePilot backend is hosted anywhere.
- `onemove-zonepilot.vercel.app` serves the **legacy OneMove marketplace**, not ZonePilot.
- **No durable artifact storage.** R1 evidence lives only in **GitHub Actions artifacts with 30-day
  retention**. After 30 days the evidence for a given commit is gone unless it was regenerated.

**Coverage and correctness gaps**
- Pilot coverage is **~68 km² of central Bengaluru**, not a city and not multiple cities.
- Observatory UI has only **3 routes** (`/`, `/capture`, `/qc`) and **zero tests**.
- **Role checks are inert** — `required_role` is only ever set in a test, never in application code.
- **`workspace_id` exists in no migration**, so multi-tenant isolation is not enforceable at the API
  layer. See [`docs/SECURITY.md`](docs/SECURITY.md).
- Evidence classes are enforced by **Python contracts only, not by database constraints**.

---

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layered architecture with per-layer WORKING / PARTIAL / SCAFFOLD / MISSING status |
| [`docs/EVIDENCE_MODEL.md`](docs/EVIDENCE_MODEL.md) | The 9 evidence classes, how they are enforced, and the R1 hash chain |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Auth model, JWKS verification, rate limiting, repo boundary, known gaps |
| [`docs/API.md`](docs/API.md) | Route-by-route `/api/v1` reference, working vs `501` |
| [`docs/execution/ZONEPILOT_PROGRAM_STATE.md`](docs/execution/ZONEPILOT_PROGRAM_STATE.md) | Live program state and blockers |

Files matching `docs/*_REPORT.md` are **legacy OneMove** artifacts retained for history. They do not
describe ZonePilot and are not maintained.
