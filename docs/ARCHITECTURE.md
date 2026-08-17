# ZonePilot Architecture

**Scope:** the real, layered architecture of ZonePilot and the honest status of each layer.

**Reference commit:** all "executed" claims are anchored to `main` at
`666ade66f965df76097c557cdf419501b683db75`.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| **WORKING** | Executed against real inputs, output verified, covered by a green CI job |
| **PARTIAL** | Executes and produces something real, but incomplete or unverified in production terms |
| **SCAFFOLD** | Code exists and imports, but has never produced a verified result |
| **MISSING** | Does not exist |

---

## Layer map

```
                                  ZonePilot pipeline
  ┌──────────┐  ┌─────────────┐  ┌─────┐  ┌────────┐  ┌───────────────┐  ┌────────┐  ┌──────┐
  │ sources  │->│ acquisition │->│ raw │->│ bronze │->│ DQ/quarantine │->│ silver │->│ gold │
  └──────────┘  └─────────────┘  └─────┘  └────────┘  └───────────────┘  └────────┘  └──────┘
                                                                                        |
        ┌───────────────────────────────────────────────────────────────────────────────┘
        v
  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌───────────┐
  │ temporal │->│ forecast │->│ scenario │->│ resilience │->│ optimizer │
  └──────────┘  └──────────┘  └──────────┘  └────────────┘  └───────────┘
                                                                  |
        ┌─────────────────────────────────────────────────────────┘
        v
  ┌────────────────┐  ┌───────────┐  ┌────────────────┐  ┌─────────────┐  ┌────────────────────┐
  │ counterfactual │->│ economics │->│ decision ledger│->│ shadow ops  │->│ API / Observatory  │
  └────────────────┘  └───────────┘  └────────────────┘  └─────────────┘  └────────────────────┘
```

Only one path through this diagram has ever executed end to end:

```
sources (Geofabrik OSM) -> acquisition -> raw -> gold -> API
```

The temporal spine (bronze -> DQ -> silver -> temporal) has **never processed a real observation**,
because no acquisition of observational data has ever succeeded.

---

## Layer-by-layer status

### 1. Sources — PARTIAL

| Source | Status | Notes |
| --- | --- | --- |
| Geofabrik OSM (`asia/india/southern-zone-latest.osm.pbf`) | **WORKING** | Downloaded, MD5-verified, clipped |
| TomTom traffic (`services/collectors/traffic/tomtom`) | **SCAFFOLD** | No data ever collected |
| Open-Meteo weather (`services/collectors/context/openmeteo.py`, `openmeteo_real.py`) | **SCAFFOLD** | No data ever collected |
| ONDC (`services/collectors/context/ondc.py`) | **SCAFFOLD** | No data ever collected |
| Platform collectors (`services/collectors/platforms/{swiggy,zomato}`) | **SCAFFOLD** | No data ever collected |

Only the geographic source has produced verified bytes.

### 2. Acquisition — PARTIAL

| Component | Status | Notes |
| --- | --- | --- |
| `services/collectors/context/osm.py` | **WORKING** | Curl download with retries, MD5 checksum verification against the published `.md5`, then clip via a digest-pinned `stefda/osmium-tool` container to bbox `77.58,12.90,77.65,12.98` (~68 km² of central Bengaluru) |
| `services/collectors/scheduler.py`, `scheduler_midnight.py`, `scheduler_intraday.py` | **SCAFFOLD** | Module code exists; nothing schedules it |
| Scheduled acquisition workflows | **DELETED** | The four workflows that used to run these (`zonepilot-midnight-acquisition.yml`, `zonepilot-intraday-acquisition.yml`, `zonepilot-midnight-catchup.yml`, `zonepilot-data-maintenance.yml`) **failed 113 / 113 runs and have been removed from this public repository.** |

**The public repository no longer schedules provider acquisition at all.** Removing the four
workflows ended the failing runs; it did not produce any data, and no replacement exists here.
`tests/execution/test_ci_contracts.py` now enforces that no public workflow may invoke an acquisition
scheduler, read a private provider secret, write to the repository on a schedule, or manage
`data/rolling` state — so the class of workflow that failed 113 times cannot be reintroduced here by
accident.

This remains the single largest structural gap in the system: everything downstream of observational
acquisition is starved of input by construction.

### 3. Raw — PARTIAL (geographic only)

Artifacts land under `$ZONEPILOT_DATA_ROOT/private/official/raw/`:

| Artifact | Status |
| --- | --- |
| `raw/osm/southern-zone-latest.osm.pbf` | **WORKING** — checksum-verified source |
| `raw/osm/pilot_corridor.osm.pbf`, `pilot_roads.osm.pbf`, `pilot_pois.osm.pbf` | **WORKING** — hashed and recorded in `raw/osm/manifest.json` |
| `raw/osrm/pilot_roads.osrm*` | **WORKING** — digest-pinned OSRM graph bundle |
| Raw traffic / weather / platform payloads | **MISSING** — never written |

The raw tree is git-ignored (`data_root/`, `*.pbf`, `*.parquet`); artifacts never enter the public
repository.

### 4. Bronze — SCAFFOLD

`services/pipeline/bronze/builder.py` exists. It has never run against real observational input,
because none exists. No bronze artifact has ever been produced or verified.

### 5. DQ / quarantine — PARTIAL

Two distinct things share the name "DQ":

| Component | Status | Notes |
| --- | --- | --- |
| Geospatial DQ gate | **WORKING** | The OSM and Gold manifests carry `dq_status`, and `services/evidence/r1.py` refuses to emit a manifest unless both are `PASS`. `dq_status = PASS` at `666ade66`. |
| `services/pipeline/dq/framework.py`, `services/collectors/dq.py` | **SCAFFOLD** | Generic DQ / quarantine framework for observational records; never exercised on real data |

There is no operating quarantine flow, because no records flow.

### 6. Silver — SCAFFOLD

`services/pipeline/silver/builder.py` exists. One geographic intermediate is produced by the OSM
pipeline (`raw/osm/silver_pois.geojson`), but the general silver conformance layer has never run.

### 7. Gold — WORKING (geographic slice only)

`services/collectors/gold.py` is the strongest link in the system:

1. Exports `pilot_roads.osm.pbf` to GeoJSON via the digest-pinned `osmium` container.
2. Builds a **canonical directed graph** with `networkx`, applying `oneway` semantics
   (`yes` / `true` / `1` forward-only, `-1` reversed), and derives vertex, directed-edge, and
   intersection (degree >= 3) counts.
3. Aggregates to **H3 resolution 8** cells.
4. Writes `gold/gold_network_h3_8.parquet` plus `manifests/gold_manifest.json`.

Verified output at `666ade66`:

| Field | Value |
| --- | --- |
| `dataset_version` | `osm-bc92c2e263d3.code-666ade66f965` |
| `graph_version` | `1.1.0+c0f22beaa7f2` |
| `schema_version` (gold) | `1.0.0` |
| `osm_nodes` | 65,479 |
| `osm_highway_ways` | 20,353 |
| `pois` | 9,161 |
| `h3_cells` (rows) | 94 |
| `dq_status` | `PASS` |

These counts move on every rebuild — they track whatever Geofabrik published that day. Only the hash
chain binding them together is invariant.

The Gold layer is **static and geographic**. It has no time dimension, no demand, and no observed
service metrics.

### 8. Routing / network snapshot — WORKING

`services/routing/osrm_pipeline.py` builds an OSRM graph from `pilot_roads.osm.pbf` using an image
pinned by digest `sha256:af5d4a83fb90086a43b1ae2ca22872e6768766ad5fcbb07a29ff90ec644ee409`, and
`tests/pipeline/test_osrm_smoke.py` executes a real route and matrix against it:

| Metric | Value |
| --- | --- |
| Route distance | 2,958.1 m |
| Route duration | 332.3 s |
| Matrix dimensions | 3 x 3 |
| Finite cells | 9 |
| Null cells | 0 |

The graph bundle is hashed as a **file set** (`sha256_file_set` in `services/evidence/r1.py`) so a
multi-file OSRM artifact has one identity.

### 9. Temporal — PARTIAL (contracts only)

`services/temporal/contracts.py` defines three strict, frozen, `extra="forbid"` Pydantic contracts:

| Contract | Purpose |
| --- | --- |
| `TemporalFeatureRecord` | Availability-aware feature record. Distinguishes `event_time`, `issued_at`, `information_available_at`, `valid_at`, `retrieved_at`. Enforces `issued_at <= information_available_at <= retrieved_at`, UTC-aware timestamps, finite feature values, and a unit for every feature. |
| `PointInTimeQuery` | Carries `decision_time` and optional `as_of_valid_at`; `validity_cutoff` is the effective leakage boundary, giving the enforced `information_available_at <= decision_time` invariant. |
| `PredictionRecord` / `OutcomeRecord` | Immutable prediction snapshots and their prospective outcomes, with `target_time == prediction_time + horizon`, `prediction_time <= frozen_at < target_time`, bound ordering, and a 40-hex `code_sha`. `prediction_fingerprint()` gives a stable content hash for detecting rewritten predictions. |

Covered by **10 tests** in `tests/temporal/test_temporal_foundations.py`.

**Status is PARTIAL, not WORKING: no temporal record has ever been written.** These are the shape of
the future data, enforced in Python only — there is no database schema behind them.

### 10. Forecast — MISSING

No forecasting model exists. Program status: `ZONEPILOT_FORECAST_MODEL_NOT_TRAINED`. There is also
**no uncertainty quantification and no conformal calibration**, so `PredictionRecord.lower_bound` /
`upper_bound` have no producer.

### 11. Scenario — SCAFFOLD

`POST /api/v1/scenarios` returns `501 NOT_IMPLEMENTED` ("Scenario builder not yet active") and
`GET /api/v1/scenarios/{id}` returns `404`. No scenario has ever been constructed or executed.

### 12. Resilience — MISSING

No resilience engine exists. The "break it" half of the product thesis (corridor failure, depot loss,
surge stress) is not implemented.

### 13. Optimizer — PARTIAL (engine real, not reachable)

A **real deterministic optimizer engine is on `main`** at `services/zonepilot/optimization/`
(`contracts.py`, `_cp_sat.py`, `_worker.py`, `solver.py`): an OR-Tools CP-SAT robust
facility-location solver that runs CP-SAT in a subprocess worker, fails closed to a `SOLVER_ERROR`
result rather than raising, and is covered by **23 tests** in
`tests/optimization/test_facility_optimizer.py` including brute-force optimality checks and a timeout
path. This is not scaffold — it computes correct answers.

**It is not reachable from the product.** `POST /api/v1/optimizations` returns `501 NOT_IMPLEMENTED`
and `GET /api/v1/optimizations/{id}` returns `404`. **No optimization has ever been executed through
the API, and R3 is not done.** Work to connect the engine to the route is in flight and unmerged;
this document describes `main` as it is.

Note that the rate limiter already reserves an `expensive` bucket for `/scenarios`, `/optimizer`, and
`/jobs` paths (default 20/min) in anticipation of this layer.

### 14. Counterfactual — MISSING

No counterfactual engine. Nothing can currently answer "what would the alternative plan have done".

### 15. Economics — MISSING

No economics engine. There is no cost model, so no decision can currently be expressed as
"lowest defensible cost".

### 16. Decision ledger — MISSING

No decision ledger. Decisions are not recorded, versioned, or replayable.

### 17. Shadow operations — MISSING

No shadow operations mode and no experiment registry. There is no way to run ZonePilot alongside a
live operation and compare outcomes without acting.

### 18. API — WORKING (read-only slice)

`services/api/main.py` builds a FastAPI app (`ZonePilot API`, version `1.5.1`) with:

- `RequestIdMiddleware` — request/correlation IDs, rate limiting, a 4 MiB payload cap, latency
  metrics, structured access logs, and central `500` formatting.
- A CORS allowlist from `ZONEPILOT_ALLOWED_ORIGINS`.
- Exception handlers that guarantee the error envelope shape for both `HTTPException` and
  `RequestValidationError`.

Routers:

`services/api/main.py` mounts **exactly four routers**:

| Router | Prefix | Status |
| --- | --- | --- |
| `observatory` | `/api/v1` | **WORKING** for the 8 read routes; scenario/optimization routes are `501`/`404` stubs |
| `version` | `/api/v1` | **WORKING** — `GET /api/v1/version`, the authenticated release-identity gate; fails closed to an opaque `503 RELEASE_IDENTITY_UNAVAILABLE` |
| `health` | — | **WORKING** — `/healthz`, `/readyz`, `/metrics` (token-gated, off by default) |
| `events` | `/v1` | **PARTIAL / legacy** — `POST /v1/events`, `POST /v1/probes` write to Supabase tables (`volunteer_order_events`, `probe_observations`, `assignments`) belonging to the earlier field-study design, not to the ZonePilot pipeline |

The `governance` router has been **deleted**. It exposed four unauthenticated stubs under
`/governance` that returned hardcoded strings; `services/api/routers/governance.py` no longer exists
and nothing replaced it.

Read routes are served by `ObservatoryService` over `ArtifactCatalogRepository`, a **read-only**
repository over locally mounted immutable artifacts with path-escape protection. When artifacts are
not mounted the routes fail closed with `503 DATASET_NOT_READY`.

See [`API.md`](API.md) for the route-by-route reference.

### 19. Observatory (UI) — PARTIAL (deployed, no backend)

`apps/observatory/` is a Next.js client with exactly **4 routes**:

| Route | Purpose |
| --- | --- |
| `/` | Network map (`src/components/map/network-map.tsx`) |
| `/capture` | Field capture |
| `/qc` | Quality control |
| `/system-health` | Release identity (`GET /api/v1/version`) + provider health (`GET /api/v1/data-health`) |

It has a Supabase auth gate, a proxy route (`src/app/api/zonepilot/[...path]/route.ts`), and an
offline outbox (`src/lib/outbox.ts`). It has **zero tests** of its own — the two Playwright specs
under `apps/observatory/tests/e2e/` cover the legacy marketplace/volunteer offline flows.

**It is deployed** at <https://zonepilot-observatory.vercel.app> from `666ade66` (GitHub Deployment
`5941546097`); all four routes answer `200`. **It has no API behind it** — the proxy defaults to
`http://127.0.0.1:8000`, and no ZonePilot backend is hosted anywhere, so `/system-health` can only
render both of its surfaces as unavailable. Vercel is not connected to GitHub, so deploys are manual
uploads. See [`operations/DEPLOYMENT_STATE.md`](operations/DEPLOYMENT_STATE.md).

### 20. Deployment — PARTIAL

| Component | State |
| --- | --- |
| Observatory frontend | **DEPLOYED** — Vercel, manual upload from `666ade66` |
| ZonePilot API | **NOT DEPLOYED** — no host; Railway has no usable token |
| Supabase `puygqvnhwsjkspoprfkb` | **PROVISIONED ONLY** — `ACTIVE_HEALTHY`, JWKS `ES256`, not wired to any running process |
| Sentry org `onemove` | **PROVISIONED, NOT INSTRUMENTED** — the Observatory has no `@sentry/nextjs` and reads no DSN, so no frontend error can ever reach it |
| Evidence artifacts | **EPHEMERAL** — GitHub Actions artifacts, 30-day retention |

The consequence worth stating plainly: **the live Observatory has no API to call**, and nothing that
is actually running is error-monitored. Details in
[`operations/DEPLOYMENT_STATE.md`](operations/DEPLOYMENT_STATE.md).

---

## Cross-cutting: evidence and versioning

Every artifact in the working path is bound to three identities simultaneously:

- **`dataset_version`** — content identity of the source extract plus the code SHA
  (`osm-bc92c2e263d3.code-666ade66f965`)
- **`graph_version`** — identity of the derived canonical graph (`1.1.0+c0f22beaa7f2`)
- **`code_sha`** — the exact 40-hex candidate commit, pinned in CI via `ZONEPILOT_CANDIDATE_SHA`

`services/evidence/r1.py` re-derives every hash from bytes on disk and cross-checks manifests against
each other and against the candidate SHA. Details in [`EVIDENCE_MODEL.md`](EVIDENCE_MODEL.md).

**Durability gap:** the resulting manifest is uploaded as a **GitHub Actions artifact with 30-day
retention**. There is no durable object store, so evidence for an old commit expires.

---

## Cross-cutting: CI

The public repository has **exactly seven workflows** and all seven are green at `666ade66`:

| Workflow | Purpose | Status at `666ade66` |
| --- | --- | --- |
| `ci.yml` (Node.js CI) | Legacy OneMove frontend checks | green — Vitest 11 passed, 2 skipped |
| `python-ci.yml` (Python CI) | Ruff + pytest on the reviewed runtime manifests | green — **176 passed, 18 skipped, 1 deselected** |
| `sql-quality.yml` (SQL Quality) | SQL lint/quality | green |
| `polyglot-ci.yml` (Polyglot CI) | Java / C legacy subsystems | green |
| `zonepilot-release.yml` (ZonePilot Release Validation) | Full gate: Supabase stack, ruff, pytest, Node checks, Vitest, Playwright, live uvicorn | green — **193 passed, 1 skipped, 1 deselected**, Vitest **18**, Playwright **10** |
| `zonepilot-r1-evidence.yml` (ZonePilot R1 Evidence) | Executes the real R1 pipeline and audits the hash chain | green |
| `codeql.yml` (CodeQL Security) | Static analysis, SHA-pinned action, every product language | green, 0 open alerts |

**There is no eighth workflow.** The four scheduled acquisition workflows were deleted; see layer 2.

The two pytest numbers differ because `Python CI` installs only the reviewed runtime manifests, so 18
tests needing optional extras (chiefly `ortools`) skip, while `ZonePilot Release Validation` installs
the full stack and runs 193. Both are real; neither contradicts the other.

Two execution-contract suites keep this shape from drifting:

| Suite | Enforces |
| --- | --- |
| `tests/execution/test_ci_contracts.py` | The four public-boundary invariants (no private provider secret, no acquisition scheduler, no scheduled `contents: write`/push, no `data/rolling` management), plus R1 OSRM smoke ownership, CodeQL language coverage with pinned actions, and the exact manifests the Python gates install |
| `tests/execution/test_dependency_consistency.py` | One authoritative Python dependency set — `services/api/requirements.txt` includes the root with `-r ../../requirements.txt` rather than duplicating pins, so the same package can never be pinned to two versions and make the combined install unsatisfiable |

---

## Legacy OneMove subsystem

The repository still contains the legacy **OneMove** marketplace: `app/`, `components/`, `lib/`,
`analytics/`, `python/`, `java/`, `c/`, `supabase/`, and the `docs/*_REPORT.md` corpus. It is a
separate product being **progressively retired** and is architecturally unrelated to the pipeline
above. The deployed URL `onemove-zonepilot.vercel.app` serves that legacy application. The ZonePilot
Observatory is a different deployment at `zonepilot-observatory.vercel.app`; **no ZonePilot backend
is deployed anywhere.**

---

## Summary table

| Layer | Status |
| --- | --- |
| Sources | PARTIAL (geographic only) |
| Acquisition | PARTIAL (OSM only; scheduled acquisition 113/113 failed) |
| Raw | PARTIAL (geographic only) |
| Bronze | SCAFFOLD |
| DQ / quarantine | PARTIAL (geospatial gate works; record-level framework unexercised) |
| Silver | SCAFFOLD |
| Gold | WORKING (static geographic slice) |
| Routing / network snapshot | WORKING |
| Temporal | PARTIAL (contracts only, no data) |
| Forecast | MISSING |
| Scenario | SCAFFOLD (501) |
| Resilience | MISSING |
| Optimizer | PARTIAL (real engine on main, 23 tests; API route still 501) |
| Counterfactual | MISSING |
| Economics | MISSING |
| Decision ledger | MISSING |
| Shadow operations | MISSING |
| LLM tool layer | MISSING |
| API | WORKING (8 read routes + the `/api/v1/version` release gate) |
| Observatory UI | PARTIAL (4 routes, 0 tests, deployed with no backend) |
| Deployment | PARTIAL (frontend deployed manually; no backend deployed anywhere) |
