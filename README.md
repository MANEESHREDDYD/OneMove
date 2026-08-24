# OneMove

Physical-commerce network decision intelligence.

[![Python CI](https://github.com/MANEESHREDDYD/OneMove/actions/workflows/python-ci.yml/badge.svg)](https://github.com/MANEESHREDDYD/OneMove/actions/workflows/python-ci.yml)
[![Node.js CI](https://github.com/MANEESHREDDYD/OneMove/actions/workflows/ci.yml/badge.svg)](https://github.com/MANEESHREDDYD/OneMove/actions/workflows/ci.yml)
[![CodeQL Security](https://github.com/MANEESHREDDYD/OneMove/actions/workflows/codeql.yml/badge.svg)](https://github.com/MANEESHREDDYD/OneMove/actions/workflows/codeql.yml)
[![Terraform CI](https://github.com/MANEESHREDDYD/OneMove/actions/workflows/terraform-ci.yml/badge.svg)](https://github.com/MANEESHREDDYD/OneMove/actions/workflows/terraform-ci.yml)

Those badges report the repository default branch, `main`. This branch
(`hotfix/onemove-p0-security-incident`) is 85 commits ahead of `main` and 0 behind, so the
badge state does not describe the code you are reading. See [Limitations](#limitations).

> **Naming.** The product is OneMove. The Python package namespace is still `zonepilot`,
> and so are the Terraform resource names. Renaming it is deferred work, not a hidden second
> system.

---

## Problem

A company that moves physical goods through a city has to decide where to put capacity —
dark stores, depots, hubs, staging points — before it knows what the week will look like.
The decision is expensive, slow to reverse, and made against a network that changes: roads
congest, monsoon rain inflates travel times, a corridor closes.

Two failure modes are common. Either the decision is made from a spreadsheet of averages
that hides tail behaviour, or it is made by a model nobody can interrogate afterwards. In
both cases, when the decision is later challenged — by a regulator, a board, or the next
quarter — the organisation cannot reconstruct what was known at the time it was made.

## What OneMove Does

OneMove takes a city network, a set of candidate facility locations, and an explicitly
declared set of assumptions, and produces a facility-placement decision that can be
re-derived later from the same inputs.

Three properties matter more than the optimizer itself:

1. **Every number carries an evidence class.** A road length measured from OpenStreetMap
   and a cost-per-facility someone chose are not presented the same way.
2. **A decision is frozen.** The solver result, the input snapshot, the assumption-set
   digest, and the release identity are recorded together as one immutable record.
3. **A frozen decision can be replayed at its own decision time**, using only information
   that existed then. If the replay does not reproduce the frozen hash, it says so.

What OneMove is not: it is not a dashboard, not a demand forecaster, and not a dispatch
system. It answers one question — where should capacity sit, and can that answer be
defended six months later.

## Operate / Simulate / Decide

**Operate.** Read the current network state: 94 H3 resolution-8 cells over the Bengaluru
pilot area, each with road length, intersection count, and commercial POI counts derived
from a public OpenStreetMap extract. Every field is returned with its provenance; a field
with no observation behind it is returned as `UNAVAILABLE` with a reason, never defaulted
to zero.

**Simulate.** Apply a counterfactual to the authentic baseline — a travel-time inflation, a
corridor cut, a heavy-rain scenario. The resulting matrix is classified `SIMULATED` (or
`SIMULATED_FAILURE`) at the structural level, so a simulation cannot be relabelled as an
observation by editing an assumption.

**Decide.** Submit an optimization, wait for the solver, freeze the result as a decision
record, and replay it later. The freeze reads from the completed solver result — an
operator cannot type plausible metrics and have them stored as solver output. Caller-supplied
figures are retained separately as `UNVERIFIED` operator claims.

## Example Decision

The pilot problem as currently configured:

| Element | Value | Evidence class |
|---|---|---|
| Demand zones | 94 H3 r8 cells, bbox `77.58,12.90 → 77.65,12.98` | `PUBLIC_GEOGRAPHIC` |
| Demand signal | `3 × commercial_poi_count + 1 × intersection_count`, floor 1 | `PUBLIC_GEOGRAPHIC` proxy under an `ASSUMPTION` weighting |
| Candidate facilities | 12, the highest-POI zones, ranked deterministically | `DERIVED` |
| Facilities opened | at most 4 | decision variable |
| Travel matrix | OSRM over `pilot_roads.osm.pbf` | `PUBLIC_GEOGRAPHIC` |
| Scenario ladder | 1.0× at 60%, 1.4× at 30%, 1.6× at 10% | `ASSUMPTION` (subjective prior) |
| Solver | OR-Tools CP-SAT `9.15.6755` | — |

A run over that problem returned `OPTIMAL` with all 94 zones served, in 7.6–8.7 seconds
across five repeat runs, producing an identical facility set, assignment hash, and
objective each time. The optimum was independently certified by exhaustively enumerating
all 793 permitted facility subsets (0.08 s); CP-SAT agrees exactly.

The resulting decision `dec-7d1f361ac3c9a368` carries an eight-node evidence chain —
decision → result → snapshot → matrix → network → assumption set → release identity — and
replays to `EXACT_MATCH` on hash `32124ab6b7c7bdfc`.

Read that table honestly: the geometry and road network are real public data; the demand
signal is a geographic proxy, not orders; the scenario probabilities are a declared guess.

## Architecture

```
Next.js frontends  ->  FastAPI (services/api)  ->  PostgreSQL
                             |
                             +-- Pub/Sub job queue --> CP-SAT worker --> PostgreSQL
```

- `services/api` — FastAPI. The operator surface is the `/observatory` router: zones,
  network snapshots, map layers, datasets, optimizations, scenarios, decisions, replay,
  shadows, forecast, evidence, and a schema-grounded assistant.
- `services/zonepilot/optimization` — problem construction (`r1_network.py`), the CP-SAT
  model (`_cp_sat.py`), the Pub/Sub worker, and the outbox dispatcher.
- `services/zonepilot/assumptions` — the sealed assumption registry. Every business number
  the optimizer uses is reachable from a set digest; the request handler contains none.
- `services/zonepilot/decisions` — the decision ledger and point-in-time replay.
- `services/collectors` — OSM, TomTom, and Open-Meteo collectors. See [Limitations](#limitations)
  for what actually runs.
- `apps/observatory` — the operator frontend (network, optimize, decisions, replay,
  evidence, resilience, data-health, system-health).
- Root `app/` — a legacy marketplace-era Next.js surface plus the demo route. It is not the
  product; see [Limitations](#limitations).

## Live Data & Evidence

Evidence classes are a closed enum, defined in `services/temporal/contracts.py` and mirrored
in `apps/observatory/src/lib/api/types.ts`:

| Class | Meaning |
|---|---|
| `OBSERVED` | A real observation from a sensor or provider at a point in time. |
| `PUBLIC_OFFICIAL` | Official government or registry data. |
| `PUBLIC_GEOGRAPHIC` | OpenStreetMap road network, H3 cell geometry, POI counts. |
| `PROVIDER_ESTIMATED` | A third-party provider's own estimate, not a raw measurement. |
| `DERIVED` | Computed deterministically from other evidence (e.g. an OSRM matrix). |
| `SIMULATED` | Produced by an injected counterfactual. |
| `ASSUMPTION` | A declared number chosen by a human, sealed in the assumption set. |
| `STAGING_DO_NOT_USE` | Non-production marker; must never back a decision. |
| `TEST_ONLY` | Non-production marker; must never back a decision. |

`UNAVAILABLE` is **not** an evidence class. It is an availability state: a map layer or a
field in that state is required by contract to carry no evidence class at all, which is what
prevents an absent value from acquiring borrowed authority.

Two independent sources are actually mounted today:

- `pilot_roads.osm.pbf` — a public OpenStreetMap extract of the pilot bbox, 11,285 drivable
  ways, named Bengaluru arterials. This is the road basemap and the routing graph.
- `gold_network_h3_8.parquet` — 94 rows, H3 resolution 8, all inside the road extract,
  verified by coordinate range rather than by filename.

Traffic and weather are **not** ingested continuously. See [Limitations](#limitations).

## Optimization

Google OR-Tools CP-SAT. The model chooses which candidate facilities to open and assigns
every demand zone, minimising a weighted objective with five components: expected travel,
P95 travel, facility cost, failure exposure, and coverage loss. Components are normalised to
basis points against declared reference values so that they are commensurate, and the five
reconcile exactly to the weighted total.

Two properties are worth stating precisely:

- **The published objective is the objective CP-SAT minimised.** A single shared coefficient
  function feeds both the model and the recorded result, so the displayed number cannot
  drift from the solved one.
- **Capacity is `NOT_MODELED` by default.** No throughput constraint is posted unless
  `capacity_mode` is explicitly set to `ASSUMPTION`. This is deliberate: the demand signal is
  commercial POI counts — a `PUBLIC_GEOGRAPHIC` proxy, not orders — and a capacity limit in
  units of that proxy would be a constraint on a quantity nobody has measured. `NOT_MODELED`
  says so out loud rather than fabricating a plausible limit.

Determinism holds under parallel search via canonical assignment reconstruction. The
optimization policy is versioned (`OPTIMIZATION_POLICY_VERSION = 2.0.0`) and included in the
problem fingerprint, so a policy change cannot silently masquerade as the same decision.

## Decision Provenance

A frozen decision record carries:

- the authoritative solver result it was derived from, including `solver_objective_total`
- the input snapshot hash and the problem fingerprint
- the assumption-set reference and digest (`r1-pilot-proxy@1.0.0`)
- the release identity — code SHA, app version, schema version
- the optimization policy version
- a per-node evidence chain, each node with its own evidence class and real identifier

A decision that a human authored must declare itself. A `MANUAL_OPERATOR_DECISION` is
persisted as such and cannot be stored as `OPTIMIZER_DECISION`; the two replay to different
typed states.

## Point-in-Time Replay

`POST /observatory/decisions/{id}/replay` re-derives the decision using only information
whose `information_available_at` is at or before the decision time. Forecasts and
observations issued after that instant are invisible to the replay, and the temporal
isolation is asserted by adversarial tests.

The verdict is computed, not stored. The frozen hash and the recomputed hash are both
returned; when they agree the verdict is `EXACT_MATCH`, and a divergence surfaces as `DRIFT`.
Replay verifies the objective the solver minimised, not a display projection of it.

Replaying a decision recorded under an older optimization policy is refused with a typed
state rather than being reported as drift — with one gap noted in [Limitations](#limitations).

## Security

This branch exists because of a P0 incident: a live database password was committed to a
public repository as a hard-coded fallback inside the DSN resolver, and the same resolver
discarded correctly-configured environment overrides. The incident record is
`docs/security/incidents/P0_DATABASE_CREDENTIAL_EXPOSURE_2026-08-19.md`. Its status is
**OPEN** — containment is done, eradication is blocked on credential rotation in the
provider console, which requires owner action. The credential is in git history and cannot
be removed by a code change.

Controls landed on this branch:

- The DSN resolver never falls back to a literal. Under the test runner it requires
  `TEST_DATABASE_URL` and refuses to start without it, so CI can no longer reach production.
- JWT verification requires `exp` and `sub`, verifies the issuer, and fails closed when auth
  configuration is missing outside local and test environments.
- The workspace predicate is mandatory on tenant reads; cross-workspace IDOR is denied and
  asserted by test.
- Blanket `GRANT ALL` replaced with least privilege; an RLS gap closed at the DB layer.
- Distributed PostgreSQL rate limiting, with a rate-limit store outage returning a typed
  `503 DEPENDENCY_UNAVAILABLE` rather than an opaque 500.
- Secret scanning runs as its own blocking CI job; CI tokens are least-privilege.

Threat model and authorization model live in `docs/security/`.

## Testing

Running the Python suite on this branch (`b035749`) with **no database configured**:

```
$ python -m pytest tests/ -q -p no:randomly
543 passed, 66 failed, 4 skipped, 5 errors in 73s
```

That is a real measured run, not a target, and it needs two caveats to be useful.

First, 64 of the 67 failing blocks trace directly to the absent database — either
`DatabaseConfigurationError: TEST_DATABASE_URL is required when running the test suite`, or a
typed `503 DEPENDENCY_UNAVAILABLE` because the PostgreSQL-backed rate-limit store cannot be
reached. Both refusals are the security fix working as designed: nothing falls back to a
literal DSN, and no request is served unmetered when the limiter is down. The remaining
handful are stale fixtures asserting pre-hardening behaviour — for example a worker test
whose frozen job lineage omits `assumption_version`, which the worker now refuses to persist
rather than inventing provenance. Those are tracked as open entries in
`docs/readiness/failure_ledger.jsonl`.

Second, test order is randomized by default, so the counts move slightly between runs. Pass
`-p no:randomly` to reproduce the numbers above.

**The suite has not been observed fully green anywhere, on any branch, from this session.**
To exercise the database-backed tests, point `TEST_DATABASE_URL` at a local or ephemeral
PostgreSQL instance — never at staging or production:

```bash
export TEST_DATABASE_URL=postgresql://...localhost.../onemove_test
python -m pytest tests/ -q
```

Notable suites: `tests/optimization/` (zone accounting, exact oracle, solver determinism),
`tests/decisions/` (ledger, replay, PIT temporal isolation), `tests/geo/` (Bengaluru lineage
verified by coordinates, not filename), `tests/security/`, `tests/adversarial/`.

Frontend: `npm run test` (Vitest), `npm run typecheck`, `npm run test:e2e` (Playwright).

## Deployment

Terraform under `infra/gcp/environments/{staging,production}` defines the deployment target:
Cloud Run v2 services `zonepilot-api-<env>` (public ingress) and `zonepilot-worker-<env>`
(internal ingress only, scale 0–5), a Pub/Sub topic for optimization jobs with a
dead-letter queue, Artifact Registry in `asia-south1`, versioned Cloud Storage buckets, and
Workload Identity Federation scoped to this repository. Container builds are defined in
`docker/` and `cloudbuild.yaml`.

**No running deployment was verified while writing this document.** No environment was
reachable from this session and no endpoint was smoke-tested, so this section describes what
the infrastructure code declares, not what is live. `docs/DEPLOYMENT.md` describes a
different topology (Vercel plus Railway) and is stale relative to the Terraform in this
repository; treat the Terraform as authoritative and that document as needing rewrite.

## Limitations

This section is the honest inventory. Everything here is a known gap, evidenced in
`docs/readiness/readiness_matrix.yaml` and `docs/audit/CTO_REVIEW_BASELINE.md`.

**Data**

- **Traffic and weather are not acquired at runtime.** The TomTom and Open-Meteo collectors
  are real code, but nothing schedules them — there is no Cloud Scheduler job in the
  Terraform — and `traffic_observations` and `weather_observations` both contain **0 rows**.
  Every live-looking value shown so far was fetched by a demo script at record time and
  baked in. Do not read any part of this system as a live telemetry pipeline.
- Data freshness and degradation handling are computed only inside the demo route, from a
  captured JSON file. There is no product-wide freshness surface.
- No historical backtest exists. There is no backtest code and no identified historical
  traffic archive, so the decision quality has never been evaluated against outcomes.

**Product surface**

- **The map is not interactive.** It is a pre-rendered raster basemap (roads, plus a traffic
  tile layer captured before the run) with a live SVG overlay for H3 cells and facilities.
  There is no pan, no zoom, no vector tiles, and no map attribution.
- The repository still carries a large marketplace-era frontend. The root `app/` directory
  holds 67 page routes: 28 under `admin/`, 30 marketplace (`customer/` 15, `merchant/` 8,
  `partner/` 7), 4 auth, and a handful of everything else. The default navigation is still
  Rides/Eats/Grocery/Courier. The actual operator product is `apps/observatory`, which has
  14 routes. A reader landing on the root application does not find this product.
- The demo route `/demo/network-intelligence` renders state pushed by a recording harness. It
  is a scripted walkthrough, not an unscripted product tour.

**Decision quality**

- **There is no do-nothing baseline.** The system tells you what it chose but not whether
  that beats changing nothing.
- **There is no structured why-this-decision record.** Objective components exist in the
  result document, but there is no human-facing explanation of which constraint bound and
  why a facility opened.
- Sensitivity analysis exists in `services/zonepilot/assumptions/sensitivity.py` but is not
  exposed through any API route.
- There is no human review or override lifecycle for a frozen decision.
- Determinism currently rests on the pilot optimum being unique. That uniqueness is certified
  for this problem instance; it is not guaranteed in general.
- A `DecisionRecord` written under an older optimization policy does not yet carry enough
  version information for every cross-policy replay path to return a typed legacy state.
- One field name still overstates its unit: the P95 figure carries `demand_units × seconds`.
  The API response was renamed to `p95_scenario_total_travel_demand_seconds`, but the
  decision record, ledger, and lineage still carry the old name pending a versioned migration.

**Operations and repository**

- **`main` is not the product.** This branch is 85 commits ahead of `main` and 0 behind.
  Anyone cloning the default branch does not get this system.
- CI on `main` is stale: recent runs there are Dependabot and CodeQL only. Nine workflows
  exist on disk for one product; consolidation is unfinished.
- Tenant isolation is proven at the application layer. The database-layer RLS migration is
  still blocked on rows with a NULL workspace.
- No load, soak, or chaos test has been run. There are no measured performance limits.
- Single city. Bengaluru is embedded in domain constants; there is no multi-city
  configuration.
- No cost model and no provider licensing review for OSM, TomTom, or Open-Meteo yet.
- The P0 credential incident remains OPEN pending rotation (see [Security](#security)).

## Local Development

Requirements: Python 3.10+ (CI runs 3.11 and 3.12), Node.js 20+, PostgreSQL 15, and
Terraform 1.5+ if you touch infrastructure.

```bash
# Backend
pip install -e ".[dev]"
uvicorn services.api.main:app --reload --port 8000

# Optimization worker (consumes the Pub/Sub job queue)
python -m services.zonepilot.optimization.pubsub_worker

# Frontend
npm install
npm run dev
```

Configuration is environment-only. There are no credential fallbacks in code — the process
will refuse to start rather than guess a DSN. Tests require `TEST_DATABASE_URL`; see
[Testing](#testing).

Health endpoints: `/health` and `/health/live` for liveness, `/ready` for readiness (which
validates cloud configuration), `/metrics` for operational metrics.

## Demo

`docs/demo/SWIGGY_DEMO_NARRATION.md` is the narration for the recorded walkthrough, and its
framing is the correct framing for this system: everything shown is public geographic
evidence or an explicitly labelled simulation. There is no operational data from any
company in this repository. The right phrasing is "we simulate a 60% travel-time increase",
never "demand rose 60%".

The demo route is `/demo/network-intelligence`. Supporting scripts are in `scripts/demo/`
(basemap build, traffic capture, mission fetch, local worker). The demo renders state pushed
by that harness rather than polling a live system.
