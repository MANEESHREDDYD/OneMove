# ZonePilot deterministic optimizer foundation

This module is an isolated R3 foundation, not an R3 research result. It does
not claim that any recommended facility plan outperforms a real baseline.

The solver consumes complete, finite travel-time matrices produced by a routed
network adapter. `TravelMatrix` requires integer seconds, a graph version, a
router version, and an evidence class. There is no geographic-distance fallback
and the module makes no provider calls.

Facility openings are shared across uncertainty scenarios. Demand assignments
may adapt by scenario. Every scenario enforces facility capacity, maximum routed
travel time, and minimum demand coverage. Capacity adjustments can represent a
facility outage or reduction without relabeling simulated evidence as observed.

The integer primary objective is:

```text
expected_travel_weight * probability_weighted_demand_seconds
+ p95_travel_weight * 10_000 * scenario_total_travel_p95
+ facility_cost_weight * 10_000 * fixed_cost_units
+ failure_exposure_weight * capacity_exposure_basis_points
+ coverage_loss_weight * probability_weighted_uncovered_demand
```

Weights carry an explicit `assumption_version`; their magnitudes are not hidden
or learned. P95 is the discrete weighted 95th percentile across the supplied
scenario distribution.

CP-SAT runs in a short-lived isolated process with one search worker and a fixed
seed. Native solver crashes and hard process deadlines become typed fail-closed
results instead of terminating a long-lived API process. After proving the primary
optimum, the engine proves a canonical tie-break that minimizes facility count,
prefers lower stable identifiers, prefers coverage, and then prefers lower
facility identifiers for scenario assignments. A merely `FEASIBLE`, timed-out,
invalid, or infeasible solve returns no facility or assignment decision.

The public FastAPI optimization routes intentionally remain `NOT_IMPLEMENTED`.
API activation requires separate job, authorization, persistence, evidence, and
rate-limit integration.
