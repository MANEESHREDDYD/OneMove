# OneMove

**Physical Commerce Network Intelligence, Resilience & Decision Optimization**

How should a physical-commerce network position capacity and respond to
uncertainty, while preserving customer service at the lowest defensible cost —
and be able to prove, months later, why it chose what it chose?

**Runtime:** ~4:35 · 1920×1080

## What the demo shows

1. **Bengaluru pilot network** — 94 H3 cells at resolution 8 on the city's real
   road geometry, rendered from the public OpenStreetMap extract
   `pilot_roads.osm.pbf`.
2. **Live observation** — current Bengaluru weather, and live traffic flow with
   measured congestion on six named arterials. Both timestamped.
3. **One simulated delivery mission** — a synthetic mission (no order, no
   customer, no rider) moving along a *real* 14.4 km routed path across the
   city, with the provider's own free-flow and traffic-aware ETAs and the delay
   between them. It exists to connect a single late delivery to the
   network-scale decision that follows.
4. **Simulated disruption** — a `HEAVY_RAIN` monsoon stress test applying a +60%
   travel-time shock, shown side by side with the actual current conditions so
   the two are never confused.
5. **Derived impact** — coverage, P50/P90/P95 travel, disconnected zones,
   redundancy and degradation grade, computed from the frozen travel matrix.
6. **Real CP-SAT optimization** — an asynchronous solve across three uncertainty
   scenarios returning `OPTIMAL`, with the chosen facilities highlighted on the
   map in the H3 cells the solver actually selected.
7. **Authoritative decision freeze** — reconstructed from the solver result, not
   entered by hand.
8. **Evidence lineage** — decision → result → problem snapshot → matrix →
   network → scenario → assumption set → release.
9. **Point-in-time replay** — the decision replayed against what was knowable at
   the time, with the frozen and recomputed hashes shown side by side.

## Evidence classes

Every value on screen belongs to exactly one class, and the class is visible:

| Class | Meaning | Source in this demo |
|---|---|---|
| `PUBLIC_GEOGRAPHIC` | Public geographic evidence | OpenStreetMap pilot extract, H3 network |
| `PUBLIC_OFFICIAL` | Public official observation | Open-Meteo current weather |
| `PROVIDER_ESTIMATED` | Third-party estimate | TomTom traffic flow |
| `SIMULATED` | Counterfactual, not observed | The monsoon stress test |
| `ASSUMPTION` | Declared business proxy | Sealed assumption set `r1-pilot-proxy` |
| `DERIVED` | Computed from the above | Impact metrics, solver output, decision |

Anything the system cannot establish is shown as `UNAVAILABLE`. It is never
filled in with a plausible number.

## Data provenance

**No Swiggy private, customer, or operational data is used.**

The recording was made in an isolated OneMove demonstration environment. The
network is built from public Bengaluru geographic evidence; weather and traffic
are public/third-party observations of public roads. Facility capacities, cost
weights and demand proxies are declared assumptions, labelled as such on screen
and sealed under a versioned assumption set.

This is not Swiggy production infrastructure and does not represent Swiggy's
actual network, demand, or service levels.

## Files

| File | Purpose |
|---|---|
| `onemove-swiggy-demo-FINAL-APPROVED.webm` | The approved recording (master) |
| `onemove-swiggy-demo-FINAL-APPROVED.mp4` | H.264 transcode of that master |
| `checksums.sha256` | SHA-256 for both files |
| `metadata.json` | Providers, versions and identifiers from the recorded run |
| `final_report.txt` | Verification results and known limitations |
| `narration.md` | Narration aligned to the recording |
| `screenshots/` | Per-stage stills captured during the run |
| `frames/` | Frames extracted from the final binary for QA |

Verify integrity with `sha256sum -c checksums.sha256`.
