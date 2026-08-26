# OneMove — final demo narration (3:57)

**Framing, and it matters:** everything shown is public geographic evidence or an
explicitly labelled simulation. Nothing is Swiggy operational data. Say "we
simulate a 60% travel-time increase", never "demand rose 60%".

**0:00 — Positioning.** OneMove: Physical Commerce Network Intelligence,
Resilience & Decision Optimization. The question it answers: how should a
physical-commerce network position capacity and respond to uncertainty while
preserving service at the lowest defensible cost?

**0:20 — Bengaluru network.** 94 H3 cells at resolution 8, drawn from the mounted
Gold artifact (`pilot_roads.osm.pbf`, graph `1.1.0+bad320dd48da`). Evidence class
`PUBLIC_GEOGRAPHIC`. Every polygon is real geometry returned by the API.

**1:00 — Simulated disruption.** One counterfactual on that authentic baseline:
`HEAVY_RAIN`, `travel_time_inflation_basis_points: 6000` — shown as +60% travel
time. Evidence class `SIMULATED`.

**1:30 — Network impact.** Coverage, P50/P90/P95 travel, disconnected zones,
redundancy and degradation grade, all `DERIVED` from the frozen matrix. Anything
not computable is reported `UNAVAILABLE` with a reason, never defaulted to zero.

**2:00 — CP-SAT.** A real solve across three uncertainty tiers, submitted and
polled asynchronously. Job id, `ortools-cp-sat-9.15.6755`, `OPTIMAL`, the
facilities opened, the objective, and the frozen assumption set — badged
`ASSUMPTION`, because these are declared proxies, not measured economics.

**2:45 — Authoritative decision.** Frozen from the completed solver result. An
operator cannot type convincing metrics and have them stored as optimizer output:
caller-supplied figures are held separately as `UNVERIFIED` operator claims, and
facility identifiers are resolved against the canonical catalog.

**3:15 — Evidence.** Decision → result → snapshot → matrix → network → assumption
set → release identity.

**3:35 — Point-in-time replay.** The strongest part. The decision is replayed
using what was knowable at its decision time, not today's state. Frozen hash and
recomputed hash are shown side by side; when they agree the verdict is
`EXACT_MATCH`. The verdict is displayed as returned — a `DRIFT` result would show
as `DRIFT`.

**Closing.** OneMove turns network data into reproducible operational decisions —
not dashboards, not predictions.
