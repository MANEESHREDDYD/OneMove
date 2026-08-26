# OneMove Provider Licence Register

**Readiness row:** DOC-03
**Owner:** Compliance / Data Licensing
**Terms last verified:** 2026-08-25 (every URL in this document was fetched on that date)
**Scope:** every *external* data source with a call site in this repository.

This document supersedes the previous "Data Licenses & Artifact Supply Chain Audit", which
inventoried *tracked files* rather than *providers*, asserted blanket "publicly redistributable —
YES" verdicts with no evidence, and omitted TomTom entirely even though TomTom raster tiles and
routing geometry are committed to `public/demo/` and rendered in the flagship demo. The artifact
inventory it contained is preserved in §9 with corrected verdicts.

Every verdict below cites `file:line`. A verdict of **NOT_COMPLIANT** means the obligation exists
and no code or UI satisfies it — not that it is hard to satisfy.

> **Credential handling.** No provider key value appears in this document or in the repository.
> Keys are referenced by variable name only (`TOMTOM_API_KEY`, `SWIGGY_CLIENT_ID`,
> `SWIGGY_CLIENT_SECRET`). `.env.local` and `OneMove.env` are gitignored
> (`.gitignore:13`, `.gitignore:15`) and neither is tracked.

---

## 1. Provider inventory — what is actually in use

| # | Provider / source | Status | Primary call sites |
|:--|:--|:--|:--|
| 1 | **OpenStreetMap** via Geofabrik extract | **ACTIVE** — data in repo, rendered in UI | `services/collectors/context/osm.py:12`, `scripts/demo/build_basemap.py:19` |
| 2 | **OpenStreetMap Foundation tile servers** (`tile.openstreetmap.org`) | **ACTIVE** — live tile requests | `components/maps/CityCommandMap.tsx:98`, `apps/observatory/src/components/map/network-map.tsx:113` |
| 3 | **CARTO basemaps** (`basemaps.cartocdn.com`) | **ACTIVE** — live tile requests | `components/maps/SafeLeafletMap.tsx:121`, `components/maps/MapComponent.tsx:55` |
| 4 | **TomTom** — Traffic Flow tiles, Flow Segment Data, Routing | **ACTIVE** — responses committed to `public/demo/` and rendered | `scripts/demo/fetch_traffic.py:65,91`, `scripts/demo/fetch_mission.py:35`, `services/collectors/traffic/tomtom/client.py:22-23` |
| 5 | **Open-Meteo** — forecast + historical archive | **ACTIVE** — live API, results persisted | `services/collectors/execution/openmeteo_forecast.py:57-58`, `services/api/core/collectors/weather.py:15`, `services/collectors/context/openmeteo.py:30,46`, `services/collectors/openmeteo_real.py:52`, `services/api/core/collectors/openmeteo.py:14` |
| 6 | **Project OSRM** (self-hosted engine) | **ACTIVE** — self-hosted, no third-party server called | `services/zonepilot/optimization/r1_network.py:146,160` |
| 7 | **Uber H3** (library) | **ACTIVE** — library, not a data service | `services/collectors/gold.py`, `services/zonepilot/optimization/r1_network.py`, `scripts/demo/build_basemap.py:15` |
| 8 | **Leaflet / react-leaflet** (library) | **ACTIVE** | `package.json` (`leaflet ^1.9.4`, `react-leaflet ^5.0.0`) |
| 9 | **Swiggy Partner MCP API** | **WIRED BUT DORMANT** — fails closed, no credentials, no agreement on file | `services/collectors/platforms/swiggy/mcp_client.py:8-9`, `services/collectors/platforms/swiggy/food.py:74` |
| 10 | **Mappls / MapmyIndia** | **DEAD — CONFIRMED REMOVED** | Zero matches for `mappls` across `*.py *.ts *.tsx *.js *.yml *.yaml`. The only surviving references are notes in the gitignored `OneMove.env`. **No code path calls Mappls.** |

Sources searched and found *not* to be in use: `router.project-osrm.org` (public demo server),
`nominatim.openstreetmap.org`, Overpass API, Mapbox, MapTiler, Google Maps, HERE, GraphHopper,
Valhalla, Ola Maps — zero call sites in `services/`, `scripts/`, `app/`, `components/`, `apps/`.

---

## 2. OpenStreetMap (via Geofabrik extract)

- **Source:** `https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf` — `services/collectors/context/osm.py:12`, downloaded with MD5 verification (`osm.py:42,47`), clipped to the Bengaluru pilot as `data/private/official/raw/osrm/pilot_roads.osm.pbf`.
- **Licence:** Open Database License (ODbL) 1.0 for the data; database contents under DbCL 1.0.
- **URLs (checked 2026-08-25):**
  - https://opendatacommons.org/licenses/odbl/summary/
  - https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
  - https://www.openstreetmap.org/copyright
- **Geofabrik note:** Geofabrik redistributes OSM under ODbL and adds no licence of its own; its
  download server is a courtesy service. The repo fetches it once per CI run
  (`.github/workflows/zonepilot-r1-evidence.yml:45`), which is well within acceptable use.

### Obligations

| # | Obligation (ODbL / OSMF attribution guidelines) | Verdict | Evidence |
|:--|:--|:--|:--|
| O-1 | Attribution must read **"OpenStreetMap"**, linked to `openstreetmap.org/copyright`, and must be visible on any map that displays the data | **NOT_COMPLIANT** | `components/demo/BengaluruMap.tsx:130-135` renders `/demo/bengaluru-roads.png` — geometry extracted straight from the PBF (`scripts/demo/build_basemap.py:41-64`) — with the only mention of OpenStreetMap in the `alt` attribute (line 132). An `alt` string is not a visible credit. `app/demo/network-intelligence/page.tsx` renders no attribution anywhere in 599 lines. **This is the map shown to the external audience.** |
| O-2 | Attribution may be collapsed but must remain reachable ("one click away") | **NOT_COMPLIANT** | Nothing to collapse — no attribution element exists in `components/demo/BengaluruMap.tsx`. |
| O-3 | Attribution must make the ODbL licence discoverable | **NOT_COMPLIANT** | No licence link in the demo UI. |
| O-4 | Share-alike: a publicly used **Derivative Database** must itself be offered under ODbL | **NOT_COMPLIANT** | `public/demo/bengaluru-basemap.json` (1.0 MB, git-tracked) is road *geometry* extracted from the PBF — a Derivative Database, not merely a Produced Work. It carries a `"source"` and `"evidence_class"` field (`scripts/demo/build_basemap.py:107-110`) but no `"license"` field and no ODbL notice, and the repository has no LICENSE covering `public/demo/`. |
| O-5 | Keep notices intact on the original database | **COMPLIANT** | The PBF is stored unmodified with its Geofabrik MD5 and SHA-256 recorded (`services/collectors/context/osm.py:167-193`); provenance is retained (`provider: "osm_geofabrik"`, `osm.py:167`). |
| O-6 | Produced Works (renderings, aggregates) need attribution but not share-alike | **NOT_COMPLIANT (attribution limb)** | `public/demo/bengaluru-roads.png`, `public/demo/bengaluru-roads-traffic.png` and the H3 aggregates in `gold_network_h3_8` are Produced Works. They carry no attribution in the rendered UI. |
| O-7 | Commercial use permitted | **NOT_APPLICABLE** (no restriction) | ODbL imposes no commercial limit. |

**Ambiguity, stated honestly.** Whether `public/demo/bengaluru-basemap.json` is a Derivative
Database or a Produced Work is genuinely arguable: it is a rendering-oriented, coordinate-rounded,
vertex-decimated subset (`build_basemap.py:53,58-59`). The **conservative reading is Derivative
Database** — it is still a structured collection of OSM geometry keyed to OSM ways — and this
register treats it that way. Under the permissive reading only O-6 applies, and OneMove is still
non-compliant, because attribution is missing under either reading. The share-alike question only
changes the *remedy*, not whether there is a defect.

---

## 3. OpenStreetMap Foundation tile servers

- **Endpoint:** `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`
- **Terms:** OSMF Tile Usage Policy — https://operations.osmfoundation.org/policies/tiles/ (checked 2026-08-25)

| # | Obligation | Verdict | Evidence |
|:--|:--|:--|:--|
| T-1 | Visible "© OpenStreetMap contributors" credit on the map | **COMPLIANT** | `apps/observatory/src/components/map/network-map.tsx:111` renders `&copy; <a href=".../copyright">OpenStreetMap contributors</a>`. |
| T-2 | Same, on the second consumer | **PARTIALLY COMPLIANT** | `components/maps/CityCommandMap.tsx:97` renders `&copy; <a href=".../copyright">OSM</a> contributors`. The OSMF guidelines require the word **"OpenStreetMap"**; "OSM" alone is an abbreviation the guidelines do not sanction. The link target is correct, so this is a wording defect, not a missing credit. |
| T-3 | Identifiable User-Agent naming the app | **NOT_APPLICABLE / at risk** | Requests originate from the end user's browser via Leaflet, so the browser UA applies. The policy's UA rule targets programmatic clients; no server-side tile fetching exists in this repo. |
| T-4 | No bulk downloading, pre-seeding, or offline tile archives | **COMPLIANT** | No tile-scraping code exists. The demo deliberately avoids the tile server entirely by pre-rendering from the PBF (`scripts/demo/build_basemap.py:1-8`). |
| T-5 | No heavy or commercial use; best-effort service, no SLA | **AT RISK — NOT_COMPLIANT if shipped** | The policy discourages commercial products relying on the OSMF tile CDN. `CityCommandMap` and the observatory map point at it directly. Acceptable for internal/demo traffic; not acceptable as the basemap of a commercial product at scale. |
| T-6 | HTTPS only | **COMPLIANT** | Both URLs are `https://` (`CityCommandMap.tsx:98`, `network-map.tsx:113`). |

---

## 4. CARTO basemaps

- **Endpoint:** `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png`
- **Terms / attribution:** https://carto.com/attribution/ , https://docs.carto.com/faqs/carto-basemaps , https://carto.com/basemaps (checked 2026-08-25)
- **Required attribution string (CARTO's own documented example):**
  `© <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, © <a href="https://carto.com/attributions">CARTO</a>`
- **Limits:** free use up to a fair-use ceiling of ~5 million tile requests/month; CARTO states
  commercial use is subject to an Enterprise licence conversation.

| # | Obligation | Verdict | Evidence |
|:--|:--|:--|:--|
| C-1 | Visibly credit **CARTO**, linked to carto.com | **NOT_COMPLIANT** | `components/maps/SafeLeafletMap.tsx:120` credits only OpenStreetMap; CARTO is absent. `components/maps/MapComponent.tsx:54` likewise credits only `OSM`. Both consume CARTO tiles (`:121`, `:55`). |
| C-2 | Visibly credit OpenStreetMap | **PARTIALLY COMPLIANT** | `SafeLeafletMap.tsx:120` says "OpenStreetMap" with the correct `/copyright` link — acceptable. `MapComponent.tsx:54` says "OSM" and links to `openstreetmap.org/` rather than `/copyright` — wording and link both wrong. |
| C-3 | Do not remove or obscure CARTO notices (Basemaps T&Cs §6.b, §15.e) | **NOT_COMPLIANT** | Raster tiles carry no baked-in notice; the notice must be supplied by the integrator, and is not. |
| C-4 | Stay under the fair-use tile ceiling | **COMPLIANT (by volume)** | Demo/internal traffic only; no evidence of bulk fetching. |
| C-5 | Commercial use requires an Enterprise arrangement | **AT RISK** | No CARTO agreement exists. Same posture as T-5. |

---

## 5. TomTom (Traffic Flow tiles, Flow Segment Data, Routing API)

This is the highest-risk provider in the register.

- **Endpoints in use:**
  - Traffic flow raster tiles — `https://api.tomtom.com/traffic/map/4/tile/flow/relative/{z}/{x}/{y}.png` (`scripts/demo/fetch_traffic.py:65`)
  - Flow Segment Data — `https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json` (`scripts/demo/fetch_traffic.py:91`)
  - Routing (traffic-aware) — `https://api.tomtom.com/routing/1/calculateRoute/...` (`scripts/demo/fetch_mission.py:35`, `services/collectors/traffic/tomtom/client.py:23`)
- **Key handling:** `TOMTOM_API_KEY` env var (`services/collectors/traffic/tomtom/client.py:21`); the
  demo scripts read the key from a local file outside the repo (`scripts/demo/fetch_traffic.py:54`,
  `scripts/demo/fetch_mission.py:30`). No key value is committed.
- **Terms URLs (checked 2026-08-25):**
  - https://developer.tomtom.com/terms-and-conditions → redirects to https://docs.tomtom.com/legal/terms-and-conditions
  - https://developer.tomtom.com/map-display-api/documentation/copyrights
  - https://docs.tomtom.com/pricing

> **Retrieval caveat — recorded rather than papered over.** `docs.tomtom.com/legal/terms-and-conditions`
> is a client-rendered single-page app; the clause text could not be extracted programmatically on
> 2026-08-25, only the page chrome. The attribution obligation below is quoted from TomTom's
> published Maps API terms language and the Copyrights API documentation, both of which are
> retrievable. **The retention and redistribution clauses must be confirmed against the executed
> agreement / the PDF terms before any external showing.** Where the clause text is not directly
> verifiable, this register states the conservative reading and marks it as such. That is a
> blocking action item, not a footnote.

| # | Obligation | Verdict | Evidence |
|:--|:--|:--|:--|
| TT-1 | For Maps API services that do **not** auto-generate a TomTom logo/copyright notice, the integrator must implement the **TomTom Copyrights API** to generate the applicable copyright and logo attribution | **NOT_COMPLIANT** | Raw raster tiles and raw JSON are consumed directly (`fetch_traffic.py:65-70`, `:91-95`); no Copyrights API call exists anywhere in the repo (zero matches for `copyrights`/`copyrightsCaption` under `services/`, `scripts/`, `app/`, `components/`). The traffic layer is rendered at `components/demo/BengaluruMap.tsx:137-143` with `alt="Live traffic flow"` and **no copyright notice and no TomTom logo**. |
| TT-2 | Do not remove, obscure, mask, or change any TomTom logo or copyright notice | **NOT_COMPLIANT** | The tile mosaic is cropped and resampled (`scripts/demo/fetch_traffic.py:86`) and then composited under a 0.78-opacity overlay (`BengaluruMap.tsx:141`). Any notice within the tile imagery would be cropped or dimmed. |
| TT-3 | Provider named where its output is displayed | **PARTIALLY COMPLIANT** | `app/demo/network-intelligence/page.tsx:295` shows `provider ${tr.provider}` → "TomTom" in a panel eyebrow, and `public/demo/bengaluru-traffic.json` carries `"provider": "TomTom"` (`fetch_traffic.py:113`). A provider label satisfies honesty about data origin; it does **not** satisfy TT-1, which requires the Copyrights API output and the logo. |
| TT-4 | Storage/caching of Results is limited; TomTom restricts retention of downloadable Map Data and Traffic Analytics products (publicly documented figures: 90 days and 60 days respectively) | **NOT_COMPLIANT (conservative reading)** | TomTom Results are **committed to git**, which is permanent retention, not caching: `public/demo/bengaluru-traffic.png` (2.9 MB tile mosaic), `public/demo/bengaluru-traffic.json` (Flow Segment Data values), `public/demo/mission.json` (route geometry — 7.5 KB of decoded polyline points, `scripts/demo/fetch_mission.py:45,65`). All four are tracked (`git ls-files public/demo/`). Separately, `services/collectors/traffic/tomtom/client.py:130` persists **raw** API responses to the bronze layer with no TTL and no expiry job. |
| TT-5 | Redistribution of raw Results to third parties | **NOT_COMPLIANT (conservative reading)** | `public/demo/*` is served as static assets by Next.js **and** is committed to the repository. Publishing raw provider tiles and raw flow readings in a source repository is redistribution to an unbounded audience, not internal use. |
| TT-6 | Commercial-use limits / free-tier transaction caps | **UNVERIFIED** | Which plan `TOMTOM_API_KEY` belongs to is not recorded anywhere in the repo. Cannot be asserted either way. Must be established before an external showing. |
| TT-7 | Rate limits | **COMPLIANT (by volume)** | The demo fetchers run offline, once, over a small bbox at zoom 14 and six named corridors (`fetch_traffic.py:29-36,63-66`). `run_tomtom_intraday()` iterates a bounded route list from `configs/data/bengaluru_pilot_routes.yaml` (`client.py:45,119`). No unbounded loop. |
| TT-8 | Key must not be exposed | **PARTIALLY COMPLIANT** | The key is never committed. However it is passed as a **URL query parameter** (`fetch_traffic.py:66,92`, `fetch_mission.py:37`, `client.py:36`), so it lands in any proxy/CDN access log on the path. Acceptable for an offline build script; not acceptable if these calls ever move client-side. |

**The single most serious finding in this register:** committing TomTom traffic imagery, flow
readings, and routing geometry to a source repository and serving them as public static assets is
the kind of defect that no amount of engineering quality offsets. It is independent of whether the
demo is impressive.

---

## 6. Open-Meteo

- **Endpoints:** `https://api.open-meteo.com/v1/forecast`, `https://archive-api.open-meteo.com/v1/archive`, `https://api.open-meteo.com/data/{meta_id}/static/meta.json`
- **Terms:** https://open-meteo.com/en/terms (checked 2026-08-25)
- **Licence:** API data provided under **CC-BY 4.0** (https://creativecommons.org/licenses/by/4.0/)
- **Free-tier limits (quoted from the terms):** "Less than 10'000 API calls per day", "5'000 per hour", "600 per minute"
- **Commercial:** "You may only use the free API services for non-commercial purposes."

| # | Obligation | Verdict | Evidence |
|:--|:--|:--|:--|
| OM-1 | CC-BY 4.0 attribution: credit Open-Meteo wherever the data is displayed | **PARTIALLY COMPLIANT** | `app/demo/network-intelligence/page.tsx:282` shows the eyebrow `"Bengaluru · observed · Open-Meteo"`. The provider is named, which is the substance of CC-BY. There is **no link to open-meteo.com and no CC-BY 4.0 licence notice**, which CC-BY 4.0 §3(a)(1) requires "to the extent reasonably practicable" — trivially practicable in a web UI. |
| OM-2 | Stay under the free-tier call limits | **COMPLIANT** | `services/collectors/execution/openmeteo_forecast.py:264` fetches **all 94 pilot cells in a single multi-location request** ("Fetch one forecast cycle for all 94 pilot cells"), with exponential backoff on rate-limit responses (`:152-163`). Orders of magnitude below 10,000/day. |
| OM-3 | Identify the client | **COMPLIANT (exceeds requirement)** | `services/collectors/execution/openmeteo_forecast.py:59` sets `USER_AGENT = "zonepilot-r0-collector/1.0 (+https://github.com/MANEESHREDDYD/OneMove)"`. Note `services/api/core/collectors/weather.py:15-28` sends the default httpx UA — Open-Meteo does not require one, so this is a hygiene gap, not a breach. |
| OM-4 | **Free tier is non-commercial only** | **NOT_COMPLIANT (conservative reading)** | All call sites target `api.open-meteo.com` / `archive-api.open-meteo.com` — the free, unauthenticated endpoints. No `customer-api.open-meteo.com` host and no Open-Meteo API-key variable exists anywhere in the repo. OneMove is being presented to an external commercial audience as a decision system. |
| OM-5 | Caching / storing responses | **COMPLIANT** | CC-BY 4.0 permits storage and redistribution provided attribution is given. Persisting forecast cycles keyed by `issued_at` (`openmeteo_forecast.py:1-32`) is squarely within the licence. |
| OM-6 | Redistribution of raw responses | **COMPLIANT, conditional on OM-1** | Permitted under CC-BY 4.0 **with** attribution and a licence notice. Since OM-1 is only partially satisfied, redistributed artifacts must carry the notice added under R-4 below. |

**Ambiguity, stated honestly.** Whether a sales/evaluation demo is "commercial purposes" is a
genuine judgement call — no revenue is earned from the weather data itself. The **conservative
reading is that a demo built to win a commercial customer is commercial use**, and OneMove should
be on a paid Open-Meteo plan (or have written confirmation from Open-Meteo) before the external
showing. Open-Meteo's paid tier is inexpensive; this is a cheap gap to close and an expensive one
to be caught on.

---

## 7. Project OSRM (self-hosted)

- **Licence:** BSD 2-Clause — https://github.com/Project-OSRM/osrm-backend (checked 2026-08-25)
- **Deployment:** self-hosted. `services/zonepilot/optimization/r1_network.py:160` reads
  `ZONEPILOT_OSRM_URL`; a dedicated GCP service account exists
  (`zonepilot-osrm-production`, `infra/gcp/environments/production/terraform.tfstate.backup:1010`).

| # | Obligation | Verdict | Evidence |
|:--|:--|:--|:--|
| OS-1 | Retain the BSD 2-Clause copyright notice in redistributions | **NOT_APPLICABLE** | OSRM is run as a service, not redistributed. Notice retention would attach only if the binary/source were shipped. |
| OS-2 | Do **not** use the public demo server `router.project-osrm.org` for production | **COMPLIANT** | Zero matches for `router.project-osrm.org` across `*.py`, `*.ts`, `*.tsx`. Only `localhost:5000` in a smoke test (`tests/pipeline/test_osrm_smoke.py:52`) and the env-configured URL. The optimizer refuses to run without a configured router rather than inventing travel times (`r1_network.py:161-164`). |
| OS-3 | The **routing results** inherit the licence of the underlying map data (OSM → ODbL) | **NOT_COMPLIANT** | `data/private/official/gold/r1_osrm_travel_matrix.json` is derived from OSM geometry and is git-tracked. It carries no ODbL notice. Same defect class as O-4. |

---

## 8. Libraries (not data services)

| Component | Licence | URL (checked 2026-08-25) | Obligation | Verdict |
|:--|:--|:--|:--|:--|
| Uber H3 | Apache-2.0 | https://github.com/uber/h3/blob/master/LICENSE | Preserve NOTICE/attribution on redistribution | **NOT_APPLICABLE** — consumed as a dependency, not redistributed. H3 cell indices are not copyrightable output. |
| Leaflet / react-leaflet | BSD-2-Clause (`node_modules/leaflet/package.json`) | https://github.com/Leaflet/Leaflet | Retain copyright notice in redistribution | **COMPLIANT** — bundler preserves the licence header; no notice removed. |
| OSRM backend | BSD-2-Clause | see §7 | see §7 | see §7 |

---

## 9. Swiggy Partner MCP API — dormant, no agreement on file

- **Endpoints:** `https://auth.swiggy.com/oauth2/token`, `https://api.swiggy.com/mcp/v1`
  (`services/collectors/platforms/swiggy/mcp_client.py:8-9`)
- **Terms:** **not public.** Access is governed by a bilateral partner agreement. No such
  agreement is referenced anywhere in this repository.

| # | Obligation | Verdict | Evidence |
|:--|:--|:--|:--|
| SW-1 | An executed partner agreement must exist before calling the API | **NOT VERIFIABLE — no agreement on file** | No contract reference in `docs/`. |
| SW-2 | Fail closed without credentials | **COMPLIANT** | `mcp_client.py:28-29` raises `READY_NEEDS_SWIGGY_OAUTH_OR_PRODUCTION_ACCESS` when `SWIGGY_CLIENT_ID`/`SWIGGY_CLIENT_SECRET` are absent. No live call is possible today. |
| SW-3 | Consumer order data is PII and would carry data-protection obligations (India DPDP Act) | **NOT ASSESSED** | `fetch_food_orders` / `fetch_instamart_orders` (`mcp_client.py:64-79`) would return consumer order records. No DPIA, retention policy, or processing agreement exists. **This must not be enabled without one.** |

Because the client fails closed and has no credentials, this is a **latent** rather than an active
defect. It becomes a blocking one the moment a key is provisioned.

---

## 10. Tracked data artifacts — corrected verdicts

The previous version of this document marked every artifact "publicly redistributable: YES".
That is wrong for the provider-derived artifacts. Corrected:

| Artifact | Upstream | Governing licence | Publicly redistributable? |
|:--|:--|:--|:--|
| `public/demo/bengaluru-traffic.png` | **TomTom** raster tiles | TomTom Maps API terms | **NO** — see TT-4, TT-5 |
| `public/demo/bengaluru-traffic.json` | **TomTom** Flow Segment Data | TomTom Maps API terms | **NO** — see TT-4, TT-5 |
| `public/demo/mission.json` | **TomTom** Routing geometry | TomTom Maps API terms | **NO** — see TT-4, TT-5 |
| `public/demo/bengaluru-roads-traffic.png` | OSM + **TomTom** composite | TomTom terms dominate | **NO** |
| `public/demo/bengaluru-basemap.json` | OSM | ODbL 1.0 | **YES, only with ODbL notice + attribution** (currently absent — O-4) |
| `public/demo/bengaluru-roads.png` | OSM | ODbL (Produced Work) | **YES, only with attribution** (currently absent — O-6) |
| `data/private/official/gold/gold_network_h3_8.*` | OSM → H3 aggregates | ODbL | **YES, with attribution** |
| `data/private/official/gold/r1_osrm_travel_matrix.json` | OSM via self-hosted OSRM | ODbL | **YES, with attribution** (currently absent — OS-3) |
| `data/private/official/manifests/*.json` | OneMove pipeline | Repo licence | **YES** |
| `data/bronze/*`, `data/silver/*`, `data/demo_exports/*.csv`, `data/dq/dq_report.json` | Synthetic | Repo licence | **YES** — no third-party data, verdict unchanged |

---

## 11. Remediation list, ranked by severity

### P0 — blocking for any external showing

| ID | Gap | Concrete change |
|:--|:--|:--|
| **R-1** | TomTom Results committed to git and served publicly (TT-4, TT-5) | `git rm --cached public/demo/bengaluru-traffic.png public/demo/bengaluru-traffic.json public/demo/mission.json public/demo/bengaluru-roads-traffic.png`; add `public/demo/*traffic*`, `public/demo/mission.json` to `.gitignore`; regenerate them at demo-build time via `scripts/demo/fetch_traffic.py` and `scripts/demo/fetch_mission.py` (both already reproducible) into a build-output directory rather than a tracked one. **Owner: demo/build engineer — not this role's files.** |
| **R-2** | No TomTom copyright attribution or logo on the demo map (TT-1, TT-2) | Add a visible attribution overlay to `components/demo/BengaluruMap.tsx` naming TomTom whenever the traffic layer is visible. **Partially closed by this change — see §12.** Full closure requires calling the TomTom Copyrights API (`https://api.tomtom.com/map/2/copyrights/caption.json`) at fetch time in `scripts/demo/fetch_traffic.py`, persisting `copyrightsCaption` into `bengaluru-traffic.json`, and rendering that exact string. |
| **R-3** | TomTom plan/tier unknown; clause text unverified (TT-6, §5 caveat) | Retrieve the executed TomTom terms PDF and record the plan tier, the permitted retention window, and the redistribution clause in §5 of this document, replacing the conservative readings with quoted clause numbers. |
| **R-4** | No OpenStreetMap attribution on the flagship demo map (O-1, O-2, O-3, O-6) | Render `© OpenStreetMap contributors` linked to `openstreetmap.org/copyright` in a corner of `components/demo/BengaluruMap.tsx`. **Closed by this change — see §12.** |

### P1 — must be closed before the audience sees it commercially

| ID | Gap | Concrete change |
|:--|:--|:--|
| **R-5** | Open-Meteo free tier is non-commercial only (OM-4) | Move to a paid Open-Meteo plan: point the collectors at `customer-api.open-meteo.com`, add an `OPEN_METEO_API_KEY` env var (name only) threaded through `services/collectors/execution/openmeteo_forecast.py:57-58`, `services/collectors/context/openmeteo.py:30,46`, `services/collectors/openmeteo_real.py:52`, `services/api/core/collectors/openmeteo.py:14`, `services/api/core/collectors/weather.py:15`. Alternatively obtain written confirmation from Open-Meteo that the demo use is acceptable, and file it. |
| **R-6** | CARTO attribution entirely missing (C-1, C-3) | Add `© CARTO` linked to `carto.com/attributions` to the `attribution` prop in `components/maps/SafeLeafletMap.tsx:120` and `components/maps/MapComponent.tsx:54`. **Closed by this change — see §12.** |
| **R-7** | ODbL share-alike notice missing on derived databases (O-4, OS-3) | Add a `"license": "ODbL-1.0"` and `"attribution": "© OpenStreetMap contributors"` field to the payload written by `scripts/demo/build_basemap.py:106-125` and by the R1 matrix generator (`scripts/generate_r1_matrix.py`); add `docs/legal/ODbL-DERIVED-DATA.md` stating which artifacts are ODbL-licensed Derivative Databases. |

### P2 — hygiene, close before GA

| ID | Gap | Concrete change |
|:--|:--|:--|
| **R-8** | `"OSM"` used where the guidelines require `"OpenStreetMap"` (T-2, C-2) | Change the `attribution` strings in `components/maps/CityCommandMap.tsx:97` and `components/maps/MapComponent.tsx:54` to spell out "OpenStreetMap" and link to `/copyright`. **Closed for `MapComponent.tsx` by this change — see §12.** `CityCommandMap.tsx` remains. |
| **R-9** | OSMF/CARTO tile CDNs used as a commercial product basemap (T-5, C-5) | Decide a basemap strategy: self-host tiles from the existing PBF, or take a CARTO/commercial plan. Record the decision in `docs/legal/`. |
| **R-10** | `TOMTOM_API_KEY` travels in the URL query string (TT-8) | Keep TomTom calls server-side only. If a client-side path is ever added, proxy through the API so the key is never issued to a browser. |
| **R-11** | Swiggy partner API has no agreement, no DPIA (SW-1, SW-3) | Do not provision `SWIGGY_CLIENT_ID`/`SWIGGY_CLIENT_SECRET` until a partner agreement and a DPDP-compliant retention policy exist. Consider deleting `services/collectors/platforms/swiggy/` if it is not on the roadmap. |
| **R-12** | Open-Meteo collector in the API layer sends a default UA (OM-3) | Set the same `USER_AGENT` constant in `services/api/core/collectors/weather.py`. |

---

## 12. What was fixed in this change

Attribution strings and one shared component. No logic, styling-system, or behavioural changes.

| File | Change | Closes |
|:--|:--|:--|
| `components/maps/MapAttribution.tsx` (new) | A shared, server-renderable credit component holding the OpenStreetMap, CARTO, TomTom and OSRM strings and their canonical links. `attributionText()` exposes the same strings so a test can assert they reach the markup. | supports R-4, R-6 |
| `components/demo/BengaluruMap.tsx` | Renders `MapAttribution` over the map: `© OpenStreetMap contributors` always, `Traffic © TomTom` only while the traffic layer is visible, `Routing by OSRM` only while a mission route is drawn. | R-4 fully; R-2 partially (the Copyrights API caption is still required) |
| `components/maps/SafeLeafletMap.tsx` | Consumes CARTO tiles and credited only OpenStreetMap. Now credits `OpenStreetMap contributors · © CARTO`. | R-6 |
| `components/maps/MapComponent.tsx` | Consumes CARTO tiles, said `OSM`, and linked to `openstreetmap.org/` rather than `/copyright`. All three corrected, and CARTO added. | R-6, R-8 (this file) |
| `components/maps/CityCommandMap.tsx` | Consumes OSMF tiles and said `OSM`, which the OSMF attribution guidelines do not sanction. Now spells out `OpenStreetMap contributors`. | R-8 (this file) |

**A correction to an earlier draft of this section.** It listed the
`SafeLeafletMap.tsx` and `MapComponent.tsx` edits as already applied when they
were not in the tree; the files still carried the original strings. The claims
were checked line by line against the working tree and the edits were then
actually made. A compliance document that reports a control as present when it
is absent is the same defect class it exists to catch, so the correction is
recorded here rather than quietly overwritten.

**What remains open:** R-1, R-3, R-5, R-7, R-9, R-10, R-11, R-12 and the
residual half of R-2. R-8 is now closed for all three map components. R-1 is the
blocking one.

---

## 13. Verification notes

- Provider inventory derived by enumerating every external host referenced in
  `services/`, `scripts/`, `app/`, `components/`, `apps/observatory/src/`, then tracing each to a
  call site. Hosts found and dispositioned: `api.tomtom.com`, `api.open-meteo.com`,
  `archive-api.open-meteo.com`, `www.openstreetmap.org`, `download.geofabrik.de`,
  `basemaps.cartocdn.com`, `tile.openstreetmap.org`, `project-osrm.org`, `carto.com`,
  `api.swiggy.com`, `auth.swiggy.com`. Remaining hosts (`unpkg.com`, `cdnjs.cloudflare.com`,
  `raw.githubusercontent.com`, `github.com`, Cloud Run URLs, `localhost`) are asset/CDN or
  first-party infrastructure, not data providers.
- Mappls was confirmed dead by search, not by assumption: zero matches across all source
  extensions.
- No credential value was read, printed, or committed in the course of this audit.
