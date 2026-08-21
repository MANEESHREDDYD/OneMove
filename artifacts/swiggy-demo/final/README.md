# OneMove

**Physical Commerce Network Intelligence, Resilience & Decision Optimization**

How should a physical-commerce network position capacity and respond to
uncertainty while preserving customer service at the lowest defensible cost?

**Demo duration:** 3:57 (1920×1080)

## What the demo shows

1. **Bengaluru pilot network** — 94 H3 cells at resolution 8, built from public
   geographic evidence (`pilot_roads.osm.pbf`).
2. **Simulated disruption** — a monsoon scenario applying +60% travel time as an
   explicit counterfactual over that authentic baseline.
3. **Network impact** — coverage, P50/P90/P95 travel, disconnected zones,
   redundancy and degradation grade, derived from the frozen travel matrix.
4. **Real CP-SAT optimization** — an asynchronous solve across three uncertainty
   tiers, returning `OPTIMAL` with the facilities opened and the objective.
5. **Authoritative decision freeze** — the decision is reconstructed from the
   completed solver result, not entered by hand.
6. **Evidence lineage** — decision → result → problem snapshot → matrix →
   network → assumption set → release identity.
7. **Point-in-time replay** — the decision is replayed using the information and
   assumptions available at that point in time, not today's state. The frozen
   hash and the recomputed hash are shown side by side.

Values on screen carry their evidence class: `PUBLIC_GEOGRAPHIC` for the routing
baseline, `SIMULATED` for the counterfactual, `ASSUMPTION` for declared business
proxies, `DERIVED` for computed metrics. Anything the system cannot establish is
shown as `UNAVAILABLE` rather than filled in.

## Data provenance

**No Swiggy private, customer, or operational data is used.**

The recording was made in an isolated OneMove demonstration environment backed by
authentic public Bengaluru geographic evidence. Disruption magnitudes, facility
capacities and cost weights are declared assumptions, labelled as such on screen.
This is not Swiggy production infrastructure and does not represent Swiggy's
actual network, demand, or service levels.

## Files

| File | Purpose |
|---|---|
| `onemove-swiggy-demo-final.mp4` | Primary demo, H.264 (broadest compatibility) |
| `onemove-swiggy-demo-final.webm` | Primary demo, original master |
| `onemove-swiggy-demo-failsafe.mp4` | Independent backup recording |
| `onemove-swiggy-demo-failsafe.webm` | Backup, original master |
| `onemove-swiggy-demo-short.mp4` | 1:16 cut for recruiter / LinkedIn use, trimmed from the primary |
| `metadata.json` | Artifact versions and runtime identifiers from the recorded run |
| `final_report.txt` | Verification results and known limitations |
| `final-demo-narration.md` | Narration aligned to the video |
| `checksums.sha256` | SHA-256 for all five recordings |
| `screenshots/` | Stills of each step |

Verify integrity with `sha256sum -c checksums.sha256`.
