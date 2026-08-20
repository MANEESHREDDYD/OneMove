"""The historical assumption sets, declared in code and mirrored in SQL.

Every value here was previously an anonymous integer inside a request handler.
None of them was measured. The point of restating them is not tidiness -- moving
literals into a constants module would change nothing -- but that each one now
carries the four things a reader needs in order to judge it: what it means, where
it came from, why it has the value it has, and how far it could plausibly move.

``source`` is deliberately blunt. For every record below the honest answer is
``proxy chosen for the pilot, not measured``, and it is written exactly that way.
Attributing these figures to observed operator economics would be the precise
defect this programme exists to remove.

Sets are append-only. A change to any value is a new version with a new digest;
the previous set stays here forever so that decisions frozen under it remain
replayable under it.
"""

from __future__ import annotations

from datetime import datetime, timezone

from services.zonepilot.assumptions.contracts import (
    UNMEASURED_PILOT_PROXY,
    AssumptionName,
    AssumptionRecord,
    AssumptionSet,
    AssumptionStatus,
    AssumptionValue,
    seal_assumption_set,
)

R1_PILOT_PROXY_SET_ID = "r1-pilot-proxy"
R1_PILOT_PROXY_VERSION = "1.0.0"

#: Back-dated to the release that introduced ``optimization_jobs``. These values
#: were already in force from that point; they simply had no identity. Dating the
#: set from today would make every optimization run before today unresolvable at
#: its own decision time, which would be a second falsehood covering the first.
_R1_EFFECTIVE_AT = datetime(2026, 8, 17, 0, 0, 0, tzinfo=timezone.utc)
_R1_SEALED_AT = datetime(2026, 8, 20, 0, 30, 0, tzinfo=timezone.utc)

#: What ``ObjectiveWeights.assumption_version`` carried before this registry
#: existed. Jobs, snapshots and results already persisted in PostgreSQL hold this
#: string, and it identifies exactly these values.
R1_LEGACY_TOKEN = "r1-proxy-1.0.0"


def _r1(
    name: str,
    value: AssumptionValue,
    *,
    unit: str,
    rationale: str,
    valid: tuple[AssumptionValue, AssumptionValue],
    sensitivity: tuple[AssumptionValue, AssumptionValue],
) -> AssumptionRecord:
    return AssumptionRecord(
        assumption_id=f"{R1_PILOT_PROXY_SET_ID}.{R1_PILOT_PROXY_VERSION}.{name}",
        assumption_set_id=R1_PILOT_PROXY_SET_ID,
        name=name,
        value=value,
        unit=unit,
        source=UNMEASURED_PILOT_PROXY,
        rationale=rationale,
        valid_min=valid[0],
        valid_max=valid[1],
        sensitivity_low=sensitivity[0],
        sensitivity_high=sensitivity[1],
        effective_at=_R1_EFFECTIVE_AT,
    )


_R1_RECORDS: tuple[AssumptionRecord, ...] = (
    _r1(
        AssumptionName.FACILITY_CAPACITY_UNITS,
        1500,
        unit="demand_units_per_facility_per_day",
        rationale=(
            "Applied uniformly to all 94 candidate facilities because no per-site throughput was ever observed. "
            "A single round number makes that uniformity obvious instead of disguising it as site-specific data. "
            "It should become a per-facility record the moment real throughput exists."
        ),
        valid=(1, 1_000_000_000),
        sensitivity=(1000, 2000),
    ),
    _r1(
        AssumptionName.FACILITY_FIXED_COST_UNITS,
        1000,
        unit="cost_units_per_facility_per_day",
        rationale=(
            "A unitless round number, identical for every candidate site, so the objective trades facility count "
            "against travel rather than choosing between sites on price. It is not a currency amount and any "
            "report that renders it as one is overstating what is known."
        ),
        valid=(0, 1_000_000_000),
        sensitivity=(500, 2000),
    ),
    _r1(
        AssumptionName.FACILITY_FAILURE_EXPOSURE_BPS_PER_RANK,
        100,
        unit="basis_points_per_facility_rank",
        rationale=(
            "Exposure is assigned from the facility's position in the travel-matrix ordering, which is arbitrary. "
            "It encodes only 'candidate sites differ in failure exposure' without claiming to know which ones do. "
            "Treat any ranking it produces as a tie-break shape, never as a risk measurement."
        ),
        valid=(0, 10_000),
        sensitivity=(50, 200),
    ),
    _r1(
        AssumptionName.DEMAND_COMMERCIAL_POI_WEIGHT,
        3,
        unit="demand_units_per_commercial_poi",
        rationale=(
            "Each commercial POI in a Gold H3 cell stands in for three units of delivery demand. No order volume "
            "was available for the pilot, so POI density is a shape proxy for where demand sits. The factor sets "
            "the POI term's weight relative to the intersection term and carries no absolute meaning."
        ),
        valid=(0, 1000),
        sensitivity=(1, 6),
    ),
    _r1(
        AssumptionName.DEMAND_INTERSECTION_WEIGHT,
        1,
        unit="demand_units_per_intersection",
        rationale=(
            "Street intersections stand in for accessibility-driven demand at one third the weight of a commercial "
            "POI. Only the ratio between the two terms reaches the optimizer, so this record and the POI weight "
            "must be read together."
        ),
        valid=(0, 1000),
        sensitivity=(0, 3),
    ),
    _r1(
        AssumptionName.DEMAND_MISSING_FEATURE_DEFAULT,
        1,
        unit="count",
        rationale=(
            "When a demand cell is absent from the Gold network table its POI and intersection counts are unknown, "
            "not zero. Substituting one keeps the cell inside the coverage problem; substituting zero would drop it "
            "and silently flatter every coverage metric that follows."
        ),
        valid=(0, 1000),
        sensitivity=(0, 1),
    ),
    _r1(
        AssumptionName.DEMAND_MINIMUM_UNITS,
        1,
        unit="demand_units",
        rationale=(
            "Floor of one unit per demand point. The optimization contract requires strictly positive demand, so a "
            "featureless cell must still carry a unit. This is a modelling floor imposed by the contract, not an "
            "estimate of latent demand, which is why its sensitivity range is a single point."
        ),
        valid=(1, 1000),
        sensitivity=(1, 1),
    ),
    _r1(
        AssumptionName.SCENARIO_BASELINE_TRAVEL_MULTIPLIER,
        1.0,
        unit="ratio",
        rationale=(
            "The baseline scenario is the routed OSRM free-flow matrix itself, so its multiplier is exactly one by "
            "definition. It is recorded so the scenario ladder is complete and auditable, not because it is a "
            "choice anyone could make differently."
        ),
        valid=(1.0, 1.0),
        sensitivity=(1.0, 1.0),
    ),
    _r1(
        AssumptionName.SCENARIO_DEGRADED_TRAVEL_MULTIPLIER,
        1.4,
        unit="ratio",
        rationale=(
            "Congested travel is modelled as free-flow inflated by 40 percent. Peak-hour inflation was never "
            "measured on this corridor set. The derived matrix is classified DERIVED rather than observed for "
            "exactly this reason, and no claim about real congestion should be drawn from it."
        ),
        valid=(1.0, 5.0),
        sensitivity=(1.2, 1.8),
    ),
    _r1(
        AssumptionName.SCENARIO_SEVERE_TRAVEL_MULTIPLIER,
        1.6,
        unit="ratio",
        rationale=(
            "Congestion plus a link outage is modelled as free-flow inflated by 60 percent. The step up from the "
            "congested scenario is the entire claimed cost of an outage, and it is a guess; the resulting matrix "
            "is classified SIMULATED_FAILURE so that it can never be mistaken for an observed disruption."
        ),
        valid=(1.0, 5.0),
        sensitivity=(1.4, 2.5),
    ),
    _r1(
        AssumptionName.SCENARIO_BASELINE_PROBABILITY_BPS,
        6000,
        unit="basis_points",
        rationale=(
            "The network is assumed free-flowing 60 percent of the time. No observed distribution of network "
            "states exists; the three scenario probabilities are a subjective prior chosen to sum to 10000 basis "
            "points. Perturbing one for sensitivity requires renormalising the other two."
        ),
        valid=(0, 10_000),
        sensitivity=(4000, 8000),
    ),
    _r1(
        AssumptionName.SCENARIO_DEGRADED_PROBABILITY_BPS,
        3000,
        unit="basis_points",
        rationale=(
            "Congestion is assumed to hold 30 percent of the time, from the same subjective prior as the baseline "
            "probability. Perturbing it for sensitivity requires renormalising the other two so the ladder still "
            "sums to 10000 basis points."
        ),
        valid=(0, 10_000),
        sensitivity=(1500, 4500),
    ),
    _r1(
        AssumptionName.SCENARIO_SEVERE_PROBABILITY_BPS,
        1000,
        unit="basis_points",
        rationale=(
            "A compound congestion-and-outage state is assumed 10 percent of the time. This is the figure that "
            "sets how much the objective pays for resilience, and it is the least defensible of the three; it "
            "deserves the widest reading of its sensitivity range."
        ),
        valid=(0, 10_000),
        sensitivity=(300, 2500),
    ),
    _r1(
        AssumptionName.OBJECTIVE_EXPECTED_TRAVEL_WEIGHT,
        5000,
        unit="objective_weight",
        rationale=(
            "Objective weights are relative: only their ratios reach the argmin. Expected travel is set equal to "
            "the coverage-loss weight so that, at the pilot's demand scale, losing a unit of coverage costs about "
            "as much as the travel serving it would have. That equivalence was asserted, never calibrated."
        ),
        valid=(0, 1_000_000_000),
        sensitivity=(2500, 10_000),
    ),
    _r1(
        AssumptionName.OBJECTIVE_P95_TRAVEL_WEIGHT,
        1000,
        unit="objective_weight",
        rationale=(
            "Tail travel carries one fifth of the weight of expected travel, so the pilot prefers a better average "
            "over a better worst case. An operator with a delivery-time promise would invert this ordering; it is "
            "a stated preference and not an observed one."
        ),
        valid=(0, 1_000_000_000),
        sensitivity=(0, 5000),
    ),
    _r1(
        AssumptionName.OBJECTIVE_FACILITY_COST_WEIGHT,
        3000,
        unit="objective_weight",
        rationale=(
            "Facility cost sits below travel, so the optimizer opens facilities up to the requested bound unless "
            "the travel gain is negligible. This is why max_open_facilities, rather than any economics, is the "
            "binding limit on the pilot's answers."
        ),
        valid=(0, 1_000_000_000),
        sensitivity=(1000, 6000),
    ),
    _r1(
        AssumptionName.OBJECTIVE_FAILURE_EXPOSURE_WEIGHT,
        500,
        unit="objective_weight",
        rationale=(
            "The smallest active weight: resilience is a tie-break here, not a driver. Since the exposure figure "
            "it multiplies is rank-assigned and arbitrary, weighting it heavily would amplify an arbitrary "
            "ordering into a decision that looked considered."
        ),
        valid=(0, 1_000_000_000),
        sensitivity=(0, 3000),
    ),
    _r1(
        AssumptionName.OBJECTIVE_COVERAGE_LOSS_WEIGHT,
        5000,
        unit="objective_weight",
        rationale=(
            "Charged per uncovered demand unit when the request permits uncovered demand. Held equal to the "
            "expected-travel weight so that leaving demand unserved is never quietly cheaper than serving it."
        ),
        valid=(0, 1_000_000_000),
        sensitivity=(2500, 10_000),
    ),
    _r1(
        AssumptionName.OBJECTIVE_COVERAGE_LOSS_WEIGHT_MANDATORY,
        0,
        unit="objective_weight",
        rationale=(
            "When a request forbids uncovered demand the constraint already makes uncovered demand infeasible, so "
            "a penalty weight would price an outcome that cannot occur. Structurally zero; recorded so the branch "
            "in the problem builder is an explained value rather than an unexplained literal."
        ),
        valid=(0, 0),
        sensitivity=(0, 0),
    ),
    _r1(
        AssumptionName.CONSTRAINT_MINIMUM_COVERAGE_BPS,
        0,
        unit="basis_points",
        rationale=(
            "The pilot enforces no hard coverage floor and relies on the coverage-loss penalty instead, so a "
            "stretched request returns a solution with visible uncovered demand rather than no answer at all. Any "
            "real service-level commitment would raise this above zero and accept the infeasibility."
        ),
        valid=(0, 10_000),
        sensitivity=(0, 9500),
    ),
    _r1(
        AssumptionName.SOLVER_MAX_TIME_SECONDS,
        30.0,
        unit="seconds",
        rationale=(
            "Wall-clock budget for CP-SAT on the 94x12x3 problem, chosen to sit well inside the asynchronous "
            "worker's job lease rather than from a measured time-to-optimality. Hitting it yields a TIME_LIMIT "
            "result that fails closed, so the budget cannot silently degrade a decision into a worse one."
        ),
        valid=(1.0, 300.0),
        sensitivity=(10.0, 120.0),
    ),
)


R1_PILOT_PROXY_V1_0_0: AssumptionSet = seal_assumption_set(
    assumption_set_id=R1_PILOT_PROXY_SET_ID,
    version=R1_PILOT_PROXY_VERSION,
    created_at=_R1_SEALED_AT,
    effective_at=_R1_EFFECTIVE_AT,
    owner="onemove-network-optimization",
    description=(
        "R1 Bengaluru pilot facility-optimization proxies. Every value is an unmeasured assumption. The set is "
        "back-dated to the release that introduced optimization jobs, because these numbers were already in force "
        "from that point without an identity; this registry gives them one rather than pretending they are new."
    ),
    status=AssumptionStatus.ACTIVE,
    records=_R1_RECORDS,
    legacy_tokens=(R1_LEGACY_TOKEN,),
)


#: Every set the registry knows about, oldest first. Append; never edit in place.
SEED_ASSUMPTION_SETS: tuple[AssumptionSet, ...] = (R1_PILOT_PROXY_V1_0_0,)
