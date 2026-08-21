# OneMove — narration

Timings are approximate and track the recorded beats. Every number spoken here
appears on screen, and every on-screen number came from a live call.

---

**0:00 — 0:15 · Opening**

OneMove is a decision system for physical commerce networks. It observes a real
network, stresses it, optimises the response, and preserves the decision so it
can be proved and reproduced later.

---

**0:15 — 0:39 · The Bengaluru pilot network**

This is a real network, not a mock. Ninety-four H3 cells at resolution 8 sit on
Bengaluru's actual road geometry, built from a public OpenStreetMap extract —
`pilot_roads.osm.pbf`. The arterials you can read on the map are the real ones:
Outer Ring Road, Hosur Road, Bannerghatta Road, 100 Feet Road.

Everything in this layer is classed `PUBLIC_GEOGRAPHIC`. It is public evidence,
and it is labelled as such.

---

**0:39 — 1:14 · What is happening right now**

Two live observations, from two independent providers.

Current weather for Bengaluru comes from Open-Meteo, classed `PUBLIC_OFFICIAL`,
stamped with the time it was observed. Live traffic comes from TomTom, classed
`PROVIDER_ESTIMATED` — the coloured flow on the roads, plus measured congestion
on six named corridors: current speed against free-flow speed, and the ratio
between them.

Both carry a capture timestamp, and the freshness label is derived from that
timestamp rather than asserted.

---

**1:14 — 1:44 · One simulated delivery mission**

To make the network story concrete, follow a single mission across the city:
created, accepted, picked up, en route, delivered.

The mission is synthetic — there is no order, no customer and no rider. The
route is not. It is a real 14.4 km path over Bengaluru's roads, and the two
travel times come from the routing provider: roughly 35 minutes at free flow
against 44 minutes with current traffic. A real delay of about nine minutes on
one run.

---

**1:44 — 1:53 · Why this scales into a decision**

One delayed delivery is a routing problem. Correlated delays across a city
become a network decision problem — and that is what the rest of this is about.

---

**1:53 — 2:13 · The counterfactual**

Now the network gets stressed. This is a monsoon stress test: `HEAVY_RAIN`, a
sixty percent travel-time shock, applied to the authentic baseline.

Note what the panel says side by side. Observed right now is whatever the
weather actually is — and the stress case is separate and explicitly
`SIMULATED`. The system never presents a simulation as an observation.

The map shifts with it. All ninety-four cells move to the scenario state.

---

**2:13 — 2:35 · Derived impact**

The impact metrics are computed from the frozen travel matrix, not estimated —
coverage, P50, P90 and P95 travel, disconnected zones, redundancy, and a
degradation grade. Classed `DERIVED`. Anything the backend cannot establish
reads `UNAVAILABLE` rather than zero.

---

**2:35 — 2:59 · Real optimisation**

The question becomes operational: given the stressed network, what capacity
configuration should we run?

The job is submitted asynchronously to a durable queue and picked up by a
separate worker — the same path as production, minus the cloud transport. It
moves through QUEUED and RUNNING under its real job id.

---

**2:59 — 3:25 · The solver result**

Google OR-Tools CP-SAT returns `OPTIMAL` — proved, not approximated — across
three uncertainty scenarios. Four facilities opened, with the weighted
objective, the solve time, the solver build, and the sealed assumption set that
priced it.

And the facilities are not just identifiers in a list. They light up on the
Bengaluru map, in the H3 cells the solver actually chose.

---

**3:25 — 3:47 · Freezing the decision**

The decision is reconstructed from the authoritative solver result and frozen
into the ledger: decision id, selected action, decision time, dataset and
network versions, solver version, the feature snapshot hash, and the release
that produced it.

An operator cannot type these values in. They are read from the solver output or
they do not exist.

---

**3:47 — 4:08 · Evidence lineage**

Every decision resolves to its inputs: decision, optimisation result, problem
snapshot, travel matrix, network graph, the simulated scenario, the assumption
set, and the release. Each node carries its own evidence class, so a reader can
see exactly which parts are public evidence, which are simulated, and which are
declared assumptions.

---

**4:08 — 4:31 · Point-in-time replay**

Finally, the decision is replayed using the information and assumptions that
were knowable at the moment it was made — not today's state.

The frozen action hash and the recomputed hash are shown side by side. Action,
facilities and objective all reproduce, and the verdict is whatever the replay
actually returned.

---

**4:31 — 4:44 · Close**

Observe, stress, optimise, decide, prove, replay.

OneMove turns physical network data into reproducible operational decisions.
