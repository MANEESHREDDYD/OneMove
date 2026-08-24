# OneMove — CTO Review Baseline

**Audited:** 2026-08-24 · **Branch head:** `ceee6e5` (`hotfix/onemove-p0-security-incident`) · **main:** `ec4bb92`
**Method:** runtime and code evidence only. No status below is taken from a README or a
design document; where documentation and code disagree, code wins.

## Status vocabulary

`VERIFIED` proven by runtime evidence cited here · `WORKING` code exercised, not
independently proven · `PARTIAL` real but incomplete · `DEMO_ONLY` works only inside a
scripted/demo path · `DEAD` present but unreachable · `STALE` real but not current ·
`BROKEN` fails · `BLOCKED` needs access/data unavailable · `NOT_IMPLEMENTED` absent.

---

## Headline

Three findings decide the CTO-review verdict.

1. **`main` is not the product.** The branch head is **59 commits ahead of `main`, 0
   behind**. A reviewer who clones this repository does not see the working system.
2. **Live data is not actually live.** TomTom and Open-Meteo collectors exist and are
   real code, but nothing schedules them, and `traffic_observations` and
   `weather_observations` both contain **0 rows**. Every "live" value shown so far was
   fetched by a demo script at record time.
3. **The decision cannot be challenged.** There is no do-nothing baseline and no
   structured explanation record, so a reviewer can see *what* the optimizer chose but
   not *why*, nor whether it beats doing nothing.

---

## Subsystem classification

| Subsystem | Status | Evidence |
|---|---|---|
| Repository / authoritative main | **BROKEN** | `git rev-list --left-right --count main...HEAD` = `0  59` |
| README credibility | **BROKEN** | Badge targets `.github/workflows/python.yml`, which does not exist (actual: `python-ci.yml`). README:110 = "17-Agent Engineering Architecture" |
| CI: required workflows green | **BROKEN** | Run `32693546939` (Python CI): `2 failed, 315 passed, 56 skipped` |
| CI: consolidation | **PARTIAL** | 9 workflows on disk for one product |
| CI: main coverage | **STALE** | Last 12 runs on `main` are Dependabot Updates + CodeQL only; no Python/Node CI run on main in the window |
| Bengaluru geography (94 H3 r8) | **VERIFIED** | `gold_network_h3_8.parquet` = 94 rows, res 8, lat 12.90–12.98 lon 77.58–77.65 |
| Road basemap | **VERIFIED** | `pilot_roads.osm.pbf`, 11,285 drivable ways, named Bengaluru arterials |
| Interactive map | **PARTIAL** | Static raster + SVG overlay. No pan/zoom, no vector tiles, no attribution |
| Traffic acquisition (runtime) | **DEMO_ONLY** | `services/collectors/traffic/tomtom/client.py` exists; no Cloud Scheduler/Run job in IaC; `traffic_observations` = **0 rows** |
| Weather acquisition (runtime) | **DEMO_ONLY** | `services/collectors/context/openmeteo.py` exists; `weather_observations` = **0 rows** |
| Freshness / degradation | **DEMO_ONLY** | Computed in the demo route from a baked JSON capture; no product-wide surface |
| Do-nothing vs recommended | **NOT_IMPLEMENTED** | No baseline comparison in code; all `DO NOTHING` hits are SQL `ON CONFLICT` |
| Why-this-decision | **NOT_IMPLEMENTED** | No structured explanation record in `services/zonepilot/` |
| Objective transparency | **PARTIAL** | Weighted objective + component values exist in `result_document.objective`; no human-facing view |
| Economics assumptions | **WORKING** | `services/zonepilot/assumptions/` — digest-sealed set, `r1-pilot-proxy@1.0.0` |
| Sensitivity analysis | **PARTIAL** | `assumptions/sensitivity.py` exists but is **not exposed via any API route** |
| CP-SAT optimization | **VERIFIED** | Real async solve, `OPTIMAL`, `ortools-cp-sat-9.15.6755`, job `80e0136c…` |
| Decision freeze | **VERIFIED** | `dec-7d1f361ac3c9a368`, reconstructed from solver result |
| Evidence lineage | **VERIFIED** | 8-node chain with real ids and per-node evidence class |
| PIT replay | **VERIFIED** | `expected_hash` == `actual_hash` (`32124ab6b7c7bdfc`), `EXACT_MATCH` |
| Backtest | **NOT_IMPLEMENTED** | No backtest code or doc anywhere in `services/` or `docs/` |
| Tenant isolation / RLS | **PARTIAL** | App-layer proven; DB-layer migration still blocked on NULL-workspace rows |
| Rate limiting | **PARTIAL** | `services/api/core/ratelimit.py` exists; per-instance, not authoritative under scale |
| Observability | **PARTIAL** | `core/telemetry.py`, request ids, release identity present; no collector health |
| Data Health page | **NOT_IMPLEMENTED** | No route; `/admin/data-platform` is marketplace-era |
| System Health page | **PARTIAL** | `/admin/system-health` exists, not audited for real values |
| Product identity | **BROKEN** | 67 routes: 30 marketplace + 28 admin vs 5 operator. Default nav = Rides/Eats/Grocery/Courier |
| Unscripted demo | **PARTIAL** | `/demo/network-intelligence` renders only state pushed by the recording harness |
| CTO-review deployment | **NOT_VERIFIED** | 2 deployments exist in the GitHub API; neither smoke-tested here |
| Executive one-pager | **NOT_IMPLEMENTED** | `docs/EXECUTIVE_OVERVIEW.md` absent |
| Cost model | **NOT_IMPLEMENTED** | `docs/COST_MODEL.md` absent |
| Provider licensing | **NOT_IMPLEMENTED** | No terms review for OSM / TomTom / Open-Meteo |

---

## Repository credibility inventory

Tracked files whose primary purpose is agent coordination or execution state:

```
.tracked_files.txt
AGENTS.md
docs/architecture/DEPENDENCY_GRAPH.md
docs/architecture/OWNERSHIP.md
docs/execution/SUBAGENT_OWNERSHIP.md
```

Untracked root noise: `auditor_v2_report.txt`, `docs_list.txt`, `failed_log.txt`,
`log.txt`, `task.md`, `CTO_PRODUCTION_READINESS_MATRIX.md`.

`docs/` holds 49 tracked markdown files for one product.

Note: `AGENTS.md` is re-generated by `next dev` (see `generate-agent-files.js`) and
cannot simply be deleted; it needs handling, not removal.

---

## What must NOT regress

Verified and protected: 94 H3 r8 cells · `pilot_roads.osm.pbf` geography · the R1 travel
matrix · CP-SAT determinism · evidence taxonomy · decision freeze · PIT replay ·
app-layer tenant isolation · the 315 passing Python tests.

---

## Known data-integrity defect

`data/geo/bengaluru_clip.osm.pbf` is **byte-identical** to `andorra-latest.osm.pbf`
(sha256 `f7da0ba356d7…`) — Andorra mislabelled as Bengaluru. Unused, but it is exactly
the kind of thing a reviewer finds. A permanent wrong-geography regression test is
warranted.
