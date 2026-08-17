# ZonePilot API Reference

**App:** `services.api.main:app` — FastAPI, title `ZonePilot API`, version `1.5.1`.
**Reference commit:** `main` at `666ade66f965df76097c557cdf419501b683db75`.

> **This API is not deployed.** There is no hosted base URL. The Observatory frontend *is* live at
> <https://zonepilot-observatory.vercel.app>, but it has no API behind it — see
> [`operations/DEPLOYMENT_STATE.md`](operations/DEPLOYMENT_STATE.md). All examples below assume a
> locally run instance at `http://127.0.0.1:8000`.

```bash
PYTHONPATH=services/api python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```

---

## Route index

### `/api/v1` — Observatory (`services/api/routers/observatory.py`)

| Method | Route | Auth | Status |
| --- | --- | --- | --- |
| GET | `/api/v1/zones` | required | **WORKING** |
| GET | `/api/v1/zones/{zone_id}/state` | required | **WORKING** |
| GET | `/api/v1/network/snapshots` | required | **WORKING** |
| GET | `/api/v1/network/snapshots/{snapshot_id}` | required | **WORKING** |
| GET | `/api/v1/network/map-layers` | required | **WORKING** |
| GET | `/api/v1/datasets` | required | **WORKING** |
| GET | `/api/v1/data-health` | required | **WORKING** |
| GET | `/api/v1/evidence/{entity_type}/{entity_id}` | required | **WORKING** |
| POST | `/api/v1/scenarios` | required | **501 NOT_IMPLEMENTED** |
| GET | `/api/v1/scenarios/{scenario_id}` | required | **404 stub** (always) |
| POST | `/api/v1/optimizations` | required | **501 NOT_IMPLEMENTED** |
| GET | `/api/v1/optimizations/{opt_id}` | required | **404 stub** (always) |

### `/api/v1` — Release identity (`services/api/routers/version.py`)

| Method | Route | Auth | Status |
| --- | --- | --- | --- |
| GET | `/api/v1/version` | required | **WORKING** — fails closed to `503` |

### Operational (`services/api/routers/health.py`)

| Method | Route | Auth | Status |
| --- | --- | --- | --- |
| GET | `/healthz` | none | **WORKING** |
| GET | `/readyz` | none | **WORKING** |
| GET | `/metrics` | bearer token | **WORKING**, disabled by default |

### Legacy / non-ZonePilot

| Method | Route | Auth | Status |
| --- | --- | --- | --- |
| POST | `/v1/events` | required | **LEGACY** — field-study Supabase write |
| POST | `/v1/probes` | required | **LEGACY** — field-study Supabase write |

> **The `/governance/*` router has been deleted.** `POST /governance/consent`, `/withdraw`,
> `/activate`, and `GET /governance/retention` were unauthenticated stubs returning hardcoded strings.
> They no longer exist: `services/api/routers/governance.py` is gone and `services/api/main.py`
> mounts exactly four routers — `events`, `observatory`, `version`, `health`. **ZonePilot has no
> governance API surface at all**, which is the honest state; it previously had one that looked like a
> capability and was not.

---

## Conventions

### Authentication

`Authorization: Bearer <supabase-jwt>` on every `/api/v1` route. Verification is JWKS-based with an
`ES256`/`RS256`/`HS256` allowlist and issuer + audience validation — see
[`SECURITY.md`](SECURITY.md).

> **All authenticated callers have identical access.** Role enforcement exists in code but is never
> activated (`required_role` is only ever set in a test), and workspace scoping is inert because
> `workspace_id` exists in no migration.

### Headers

| Header | Direction | Notes |
| --- | --- | --- |
| `x-request-id` | in / out | Accepted if it matches `^[A-Za-z0-9._:-]{1,128}$`, else replaced with a UUID4 |
| `x-correlation-id` | in / out | Same validation; defaults to the request ID |
| `x-workspace-id` | in | Accepted by CORS and compared against a `workspace_id` claim — **inert**, since no such claim is ever issued |
| `retry-after` | out | On `429` |

### Error envelope

Every failure returns:

```json
{
  "error": {
    "code": "DATASET_NOT_READY",
    "message": "Required artifact manifest is missing: manifests/gold_manifest.json",
    "request_id": "b0f2...",
    "retryable": true,
    "details": {}
  }
}
```

| Code | Status | Meaning |
| --- | --- | --- |
| `UNAUTHORIZED` | 401 | Missing / invalid / expired token |
| `FORBIDDEN` | 403 | Workspace or role assertion failed (currently unreachable) |
| `NOT_FOUND` | 404 | Entity or artifact does not exist |
| `HTTP_409` / `ARTIFACT_INTEGRITY_ERROR` | 409 | Artifact hash mismatch, or duplicate client event |
| `PAYLOAD_TOO_LARGE` | 413 | Body exceeds 4 MiB |
| `VALIDATION_ERROR` | 422 | Request body/params invalid; `details.errors[]` carries `{location, type, message}` |
| `INVALID_ARGUMENT` | 422 | Argument rejected by the service layer |
| `RATE_LIMITED` | 429 | Rate limit exceeded; `details.{bucket, limit_per_minute}` |
| `NOT_IMPLEMENTED` | 501 | Route exists but the engine behind it is not built |
| `DATASET_NOT_READY` | 503 | Required artifact is not mounted — **fail-closed, not a bug** |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled exception; details are logged, never returned |

`retryable` is `true` for `408`, `429`, `500`, `502`, `503`, `504`.

### Rate limits

| Bucket | Matches | Default/min |
| --- | --- | --- |
| `auth` | path contains `/auth` | 10 |
| `expensive` | path contains `/scenarios`, `/optimizer`, `/jobs` | 20 |
| `authenticated` | any authenticated request | 120 |

### Artifact dependency

All working `/api/v1` routes read from a locally mounted immutable artifact tree at
`$ZONEPILOT_DATA_ROOT/private/official/`. Without it every one of them returns `503
DATASET_NOT_READY`. There is no database-backed or synthetic fallback.

### Provenance fields

Every Observatory response object carries the same five provenance fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `evidence_class` | `EvidenceClass` | The real enum, not a free string — see [`EVIDENCE_MODEL.md`](EVIDENCE_MODEL.md) |
| `source` | string | Origin of the value |
| `source_version` | string \| null | `graph_version`, image digest, or provider version |
| `observed_at` | datetime \| null | When the backing artifact was generated |
| `artifact_hash` | string \| null | Re-derived SHA-256 of the backing artifact |

**`evidence_class` and availability are separate vocabularies.** `evidence_class` is typed as the
`EvidenceClass` enum imported from `services/temporal/contracts.py`; an unknown string is rejected at
serialization. Availability lives in a distinct `state` field (`AVAILABLE` / `UNAVAILABLE`, or the
provider-health states). An object with nothing behind it carries `state: "UNAVAILABLE"` and
`evidence_class: null` — it does not borrow a non-enum value like `UNAVAILABLE` to fill the slot.
`MapLayer` enforces the pairing with a model validator: `UNAVAILABLE` must not claim an evidence
class, `AVAILABLE` must declare one.

---

## Working routes

### `GET /api/v1/zones`

Lists the H3 cells present in the verified Gold artifact. At `666ade66` this is **94 cells at H3
resolution 8**, covering the ~68 km² pilot bbox `77.58,12.90,77.65,12.98` in central Bengaluru.

**200** — `{"data": [ZoneSummary]}` where `ZoneSummary` is a `Provenance` plus:

| Field | Type |
| --- | --- |
| `zone_id` | string (H3 index) |
| `resolution` | int (8) |
| `boundary` | list of `[lat, lng]` pairs |

Evidence class: `PUBLIC_GEOGRAPHIC`.

**503** `DATASET_NOT_READY` if the Gold manifest is not mounted.
**409** `ARTIFACT_INTEGRITY_ERROR` if the parquet hash does not match the manifest.

### `GET /api/v1/zones/{zone_id}/state`

Static, evidence-bearing state for one real Gold H3 cell.

**200** — `{"data": ZoneState}`:

| Field | Notes |
| --- | --- |
| `zone_id`, `resolution`, `boundary` | as above |
| `static` | eight `FieldEvidence` objects, each with its own `value`, `unit`, and full provenance |
| `unavailable_dynamic_layers` | list of `{layer, state: "UNAVAILABLE", reason, evidence_class: null}` — availability lives in `state`; the evidence class is explicitly absent |

`static` fields: `cell_area_km2`, `road_length_km`, `intersection_count`, `restaurant_count`,
`grocery_count`, `commercial_poi_count`, `road_density_km_per_sqkm`,
`intersection_density_per_sqkm`.

**All state here is static geography.** There is no demand, traffic, weather, or service-level state,
because none has ever been collected. `unavailable_dynamic_layers` is the honest, explicit
representation of that — the API declares the absence rather than substituting a placeholder value.

**404** `NOT_FOUND` for an unknown `zone_id`.

### `GET /api/v1/network/snapshots`

Lists immutable versioned network snapshots derived from the OSRM graph build. Returns zero or one
snapshot today.

**200** — `{"data": [NetworkSnapshot]}`:

| Field | Notes |
| --- | --- |
| `snapshot_id` | the OSRM graph-bundle hash |
| `graph_version` | `1.1.0+c0f22beaa7f2` at `666ade66` |
| `h3_resolution` | 8 |
| `status` | always `"AVAILABLE"` (the list omits unavailable snapshots) |
| `metrics` | `{graph_vertices, graph_directed_edges, intersections, connected_components, largest_component_vertices}` |

Evidence class `DERIVED`, source `OSRM`, `source_version` = the pinned image digest
`sha256:af5d4a83fb90086a43b1ae2ca22872e6768766ad5fcbb07a29ff90ec644ee409`.

### `GET /api/v1/network/snapshots/{snapshot_id}`

Single snapshot by ID. **200** `{"data": NetworkSnapshot}`, **404** if the ID does not match the
mounted snapshot, **503** if no snapshot is mounted.

### `GET /api/v1/network/map-layers`

Bounded, evidence-bearing GeoJSON overlays for the R1 map.

**200** — `{"data": [MapLayer]}` for `layer` in `roads`, `intersections`, `pois`:

| Field | Notes |
| --- | --- |
| `state` | `"AVAILABLE"` or `"UNAVAILABLE"` |
| `complete` | `false` when the layer was truncated |
| `total_feature_count` / `returned_feature_count` | the truncation is always disclosed |
| `selection_policy` | human-readable description of what was selected and how |
| `geojson` | the FeatureCollection |

Caps: **roads 3,000**, **intersections 1,500**, **POIs 1,500**. Above the cap features are evenly
sampled, never silently head-truncated, and `complete` becomes `false`.

Evidence classes: `PUBLIC_GEOGRAPHIC` for roads/POIs, `DERIVED` for the canonical-graph intersection
layer.

Unlike other routes this one **degrades rather than fails**: if artifacts are missing it returns
layers with `state: "UNAVAILABLE"` and a `reason`.

### `GET /api/v1/datasets`

Dataset versions discovered from immutable manifests.

**200** — `{"data": [DatasetRecord]}`:

| Field | Notes |
| --- | --- |
| `dataset_id` | from the manifest's `dataset_id` |
| `provider` | `osm` for the Gold record; the provider name for collection runs |
| `version` | for the Gold record this is the **parquet SHA-256**, i.e. content identity |
| `schema_version` | the Gold manifest's **own `schema_version`** (`1.0.0`), or `null` when the manifest declares none. It is no longer populated from `graph_version`, so the field name and its contents now agree |
| `availability` | `AVAILABLE` \| `EMPTY` \| `FAILED` \| `UNAVAILABLE` |
| `record_count` | rows — 94 for the Gold H3 dataset at `666ade66` |
| `run_id` | collection run, when applicable |

The Gold dataset is always first, followed by any per-provider collection runs.

> **In practice only the Gold dataset is ever `AVAILABLE`.** The `openmeteo`, `tomtom`, and `ondc`
> providers have never produced a successful collection run.

Provider evidence classes come from `PROVIDER_EVIDENCE_CLASS` in
`services/api/services/observatory.py` and are all real `EvidenceClass` members. `openmeteo` and
`ondc` map to **`PUBLIC_OFFICIAL`**, because both are public/authoritative published sources. The
earlier non-enum string `OFFICIAL_API_REAL` no longer exists anywhere in the codebase.

### `GET /api/v1/data-health`

Provider freshness and DQ state computed from collection manifests.

**200** — `{"data": [ProviderHealth], "evaluated_at": datetime}`:

| Field | Notes |
| --- | --- |
| `provider` | e.g. `osm`, `osrm`, `openmeteo`, `tomtom`, `ondc` |
| `state` | `FRESH` \| `DEGRADED` \| `STALE` \| `UNAVAILABLE` |
| `last_successful_collection` | datetime \| null |
| `expected_freshness_seconds` / `observed_freshness_seconds` | SLA vs actual |
| `dq_result` | `PASS` \| `FAIL` \| `UNKNOWN` |
| `latest_run_status`, `dataset_ids` | run linkage |

> This endpoint is currently the most honest surface in the system: for every observational provider
> it reports `UNAVAILABLE` with a null `last_successful_collection`, because **acquisition has failed
> 113/113 runs.**

### `GET /api/v1/evidence/{entity_type}/{entity_id}`

Resolves an entity to its provenance envelope.

`entity_type` must be one of **`dataset`**, **`zone`**, **`network`** — anything else is `422
INVALID_ARGUMENT` ("entity_type must be one of: dataset, network, zone").

**200** — `{"data": EvidenceRecord}` = the five provenance fields plus `entity_type`, `entity_id`, and
a scalar-valued `metadata` map:

| `entity_type` | `metadata` keys |
| --- | --- |
| `dataset` | `version`, `availability`, `record_count`, `run_id` |
| `zone` | `h3_resolution`, `road_length_km`, `intersection_count` |
| `network` | `graph_version`, `h3_resolution`, `graph_vertices`, `graph_directed_edges` |

**404** `NOT_FOUND` if the entity is not present.

### `GET /api/v1/version`

The authenticated release-identity gate (`services/api/routers/version.py`). **It exists and it
works** — it is not a stub, and it is not unauthenticated. It returns `200` only when the deployed
application identity is bound to Gold and OSRM artifacts whose SHA-256 hashes it **recomputes on every
request**.

Required deployment configuration:

| Variable | Requirement |
| --- | --- |
| `ZONEPILOT_APP_VERSION` | immutable semantic release version |
| `ZONEPILOT_GIT_SHA` | exact lowercase **40-hex** commit; abbreviated, floating, or placeholder values are rejected |
| `ZONEPILOT_SCHEMA_VERSION` | semantic Gold schema version expected by that release |
| `ZONEPILOT_DATA_ROOT` | mounted private artifact root |

**200** — `{"data": ReleaseIdentity}`:

| Field | Contents |
| --- | --- |
| `app_version`, `git_sha`, `schema_version` | the deployed application identity |
| `gold` | `{dataset_id, dataset_version, schema_version, artifact_sha256, record_count}` |
| `graph` | `{graph_version, topology_sha256, bundle_sha256}` |

The response contains identifiers and hashes only — never filesystem paths, environment values,
credentials, or partial data.

**503 `RELEASE_IDENTITY_UNAVAILABLE`** — **every** failure mode collapses to this one retryable
envelope: missing configuration, malformed identifiers, absent artifacts, a stale manifest, a hash
mismatch, a schema or commit mismatch, failed DQ, or invalid routing-smoke evidence. The endpoint
never discloses which check failed and never returns a partially trusted identity. **401** precedes
all of it for an unauthenticated caller.

`/healthz` and `/readyz` are orchestration probes and must not be used as release identity. Full
contract: [`operations/RELEASE_IDENTITY.md`](operations/RELEASE_IDENTITY.md).

> This gate has **never run against a deployment**, because the API is not deployed anywhere. The
> Observatory `/system-health` page consumes it through the session proxy and, with no backend, can
> only render it as unavailable.

---

## Not-implemented routes

These exist so the contract is visible and so callers get a precise machine-readable refusal instead
of a 404 or a fabricated result.

### `POST /api/v1/scenarios` — 501

```json
{"error": {"code": "NOT_IMPLEMENTED", "message": "Scenario builder not yet active.",
           "request_id": "...", "retryable": false, "details": {}}}
```

No scenario has ever been constructed. Intended to be idempotent when built.

### `GET /api/v1/scenarios/{scenario_id}` — 404

Unconditional `404 NOT_FOUND` ("Scenario not found."). No storage exists behind it.

### `POST /api/v1/optimizations` — 501

```json
{"error": {"code": "NOT_IMPLEMENTED", "message": "Robust optimization not yet active.",
           "request_id": "...", "retryable": false, "details": {}}}
```

**A real optimizer engine exists on `main` at `services/zonepilot/optimization/` — a deterministic
OR-Tools CP-SAT robust facility solver with 23 tests — but it is not reachable through the API and no
optimization has ever been executed.** Wiring it to this route (R3) is in flight and unmerged; on
`main` at `666ade66` the route is `501`.

### `GET /api/v1/optimizations/{opt_id}` — 404

Unconditional `404 NOT_FOUND` ("Optimization not found.").

### Not present at all

There is **no route** for forecasting, resilience/stress, counterfactual analysis, economics, the
decision ledger, shadow operations, the experiment registry, or an LLM tool layer — those layers do
not exist. See [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Operational endpoints

### `GET /healthz`

Unauthenticated liveness. Always `200 {"status": "ok"}`.

### `GET /readyz`

Unauthenticated readiness. Attempts `SELECT 1` against `ZONEPILOT_DB_URL` with a 3-second timeout.

| Condition | Response |
| --- | --- |
| DB reachable | `200 {"status": "ready", "db_connected": true}` |
| DB unreachable or `ZONEPILOT_DB_URL` unset | `503 {"status": "unready", "db_connected": false}` |

Error detail is logged, never returned.

### `GET /metrics`

Prometheus text exposition (`text/plain; version=0.0.4`). **Disabled by default** and hidden from the
OpenAPI schema.

| Condition | Response |
| --- | --- |
| `ZONEPILOT_METRICS_ENABLED` not truthy | `404` |
| Enabled, `ZONEPILOT_METRICS_TOKEN` set, token mismatched | `401` |
| Enabled and authorized | `200` with request counters and latency observations |

Token comparison uses `hmac.compare_digest`. **If the token env var is unset while metrics are
enabled, the check is skipped** — set both together.

---

## Legacy routes

### `POST /v1/events`, `POST /v1/probes`

From the earlier field-study design, not the ZonePilot pipeline. They write to Supabase tables
(`volunteer_order_events`, `probe_observations`, `assignments`), stamp `provenance: "OBSERVED"`
server-side, and implement semantic idempotency via a SHA-256 `client_payload_hash` (an exact replay
returns `{"idempotent_replay": true}`; a conflicting reuse of `client_event_id` is `409`).

`POST /v1/probes` parses the `Authorization` header manually instead of using the auth dependency and
uses a **service-role** Supabase client (bypassing RLS) for assignment lookup and idempotency checks.
Flagged in [`SECURITY.md`](SECURITY.md).

### `/governance/*` — removed

These four unauthenticated stubs no longer exist. `services/api/routers/governance.py` was deleted
and the router is no longer mounted. Nothing replaced them: **ZonePilot has no governance API.**

---

## Quick reference

```bash
# Liveness
curl -s http://127.0.0.1:8000/healthz

# Zones (94 H3 R8 cells when artifacts are mounted)
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/zones

# Provider freshness — expect UNAVAILABLE for every observational provider
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/data-health

# Provenance for a dataset (take the dataset_id from /api/v1/datasets)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/v1/evidence/dataset/$DATASET_ID"

# Release identity — 200 only with a fully verified deployment, else 503
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/version

# 501
curl -s -X POST -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/optimizations
```
