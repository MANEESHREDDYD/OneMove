"""Applying a sealed assumption set to the facility-optimization problem.

The registry stores named numbers. This module is the single place that knows
what those numbers *mean* to the optimizer -- which record supplies a facility's
capacity, how a scenario multiplier turns a free-flow duration into a congested
one, which weight applies when uncovered demand is forbidden.

Keeping that mapping here rather than in the request handler is what makes the
handler auditable: it can be read end to end without encountering a single
business number, and every number it does use is reachable from a set digest.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from services.zonepilot.assumptions.contracts import (
    AssumptionName,
    AssumptionRecord,
    AssumptionSet,
    AssumptionSetRef,
    AssumptionValue,
)
from services.zonepilot.optimization.contracts import (
    BASIS_POINTS,
    MatrixEvidenceClass,
    ObjectiveWeights,
)

#: Gold network columns the demand proxy reads.
COMMERCIAL_POI_COLUMN = "commercial_poi_count"
INTERSECTION_COLUMN = "intersection_count"


def gold_zone_key(demand_id: str) -> str:
    """The H3 index a demand id refers to, whether it is ``dem:<h3>`` or bare."""
    _, _, zone = demand_id.rpartition(":")
    return zone or demand_id


class AssumptionApplicationError(ValueError):
    """A set does not carry an assumption the optimizer requires."""


@dataclass(frozen=True, slots=True)
class ScenarioTier:
    """One rung of the uncertainty ladder.

    ``evidence_class`` is not an assumption -- it is a statement about how the
    matrix was produced, and it stays structural so that a set edit can never
    relabel a simulated failure as observed geography.
    """

    role: str
    travel_time_multiplier: float
    probability_basis_points: int
    evidence_class: MatrixEvidenceClass
    is_baseline: bool

    def scale_duration_seconds(self, duration_seconds: int) -> int:
        """Inflate one routed duration, quantized up to a whole second."""
        return int(math.ceil(duration_seconds * self.travel_time_multiplier))


#: The ladder's shape (order, derivation, evidence) is fixed; only its numbers
#: come from the assumption set.
_TIER_SHAPE: tuple[tuple[str, str, str, MatrixEvidenceClass, bool], ...] = (
    (
        "BASELINE",
        AssumptionName.SCENARIO_BASELINE_TRAVEL_MULTIPLIER,
        AssumptionName.SCENARIO_BASELINE_PROBABILITY_BPS,
        MatrixEvidenceClass.PUBLIC_GEOGRAPHIC,
        True,
    ),
    (
        "DEGRADED",
        AssumptionName.SCENARIO_DEGRADED_TRAVEL_MULTIPLIER,
        AssumptionName.SCENARIO_DEGRADED_PROBABILITY_BPS,
        MatrixEvidenceClass.DERIVED,
        False,
    ),
    (
        "SEVERE",
        AssumptionName.SCENARIO_SEVERE_TRAVEL_MULTIPLIER,
        AssumptionName.SCENARIO_SEVERE_PROBABILITY_BPS,
        MatrixEvidenceClass.SIMULATED_FAILURE,
        False,
    ),
)


class AssumptionSetView:
    """Typed, read-only access to one sealed set.

    A view never mutates its set and never falls back to another one: an absent
    assumption raises rather than resolving to a default, because a default is
    just an unversioned assumption with better manners.
    """

    __slots__ = ("_set",)

    def __init__(self, assumption_set: AssumptionSet) -> None:
        self._set = assumption_set

    def __repr__(self) -> str:
        return f"AssumptionSetView({self._set.assumption_set_id}@{self._set.version})"

    @property
    def assumption_set(self) -> AssumptionSet:
        return self._set

    @property
    def assumption_set_id(self) -> str:
        return self._set.assumption_set_id

    @property
    def version(self) -> str:
        return self._set.version

    @property
    def sha256(self) -> str:
        return self._set.sha256

    @property
    def ref(self) -> AssumptionSetRef:
        return self._set.ref

    @property
    def token(self) -> str:
        """The lineage string frozen into the job, snapshot and result."""
        return self._set.token

    # -- raw access ----------------------------------------------------------

    def record(self, name: str) -> AssumptionRecord:
        try:
            return self._set.record(name)
        except KeyError as exc:
            raise AssumptionApplicationError(str(exc)) from exc

    def value(self, name: str) -> AssumptionValue:
        return self.record(name).value

    def integer(self, name: str) -> int:
        raw = self.value(name)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise AssumptionApplicationError(
                f"assumption {name!r} must be an integer to be used here, got {type(raw).__name__}"
            )
        return raw

    def real(self, name: str) -> float:
        raw = self.value(name)
        if isinstance(raw, bool):
            raise AssumptionApplicationError(f"assumption {name!r} is not numeric")
        return float(raw)

    # -- facilities ----------------------------------------------------------

    @property
    def facility_capacity_units(self) -> int:
        return self.integer(AssumptionName.FACILITY_CAPACITY_UNITS)

    @property
    def facility_fixed_cost_units(self) -> int:
        return self.integer(AssumptionName.FACILITY_FIXED_COST_UNITS)

    def facility_failure_exposure_basis_points(self, *, rank: int) -> int:
        """Exposure for the facility at ``rank`` in the matrix ordering.

        Clamped to the basis-point ceiling so a wider candidate list cannot push
        the value past what the optimization contract accepts.
        """
        per_rank = self.integer(AssumptionName.FACILITY_FAILURE_EXPOSURE_BPS_PER_RANK)
        return min(BASIS_POINTS, per_rank * rank)

    # -- demand --------------------------------------------------------------

    @property
    def demand_commercial_poi_weight(self) -> int:
        return self.integer(AssumptionName.DEMAND_COMMERCIAL_POI_WEIGHT)

    @property
    def demand_intersection_weight(self) -> int:
        return self.integer(AssumptionName.DEMAND_INTERSECTION_WEIGHT)

    @property
    def demand_missing_feature_default(self) -> int:
        return self.integer(AssumptionName.DEMAND_MISSING_FEATURE_DEFAULT)

    @property
    def demand_minimum_units(self) -> int:
        return self.integer(AssumptionName.DEMAND_MINIMUM_UNITS)

    def demand_units(self, gold_row: Mapping[str, Any] | None) -> int:
        """Proxy demand for one H3 cell from its Gold network features.

        A missing row and a row with missing columns are treated identically: the
        counts are unknown, and the documented default keeps the cell in the
        coverage problem instead of dropping it.
        """
        row: Mapping[str, Any] = gold_row or {}
        default = self.demand_missing_feature_default
        poi = row.get(COMMERCIAL_POI_COLUMN, default)
        intersections = row.get(INTERSECTION_COLUMN, default)
        poi = default if poi is None else int(poi)
        intersections = default if intersections is None else int(intersections)
        proxy = poi * self.demand_commercial_poi_weight + intersections * self.demand_intersection_weight
        return max(self.demand_minimum_units, proxy)

    def demand_units_for(self, demand_id: str, gold_rows: Mapping[str, Mapping[str, Any]]) -> int:
        """Proxy demand for one demand point, looked up by its H3 index."""
        return self.demand_units(gold_rows.get(gold_zone_key(demand_id)))

    # -- scenarios -----------------------------------------------------------

    @property
    def scenario_tiers(self) -> tuple[ScenarioTier, ...]:
        return tuple(
            ScenarioTier(
                role=role,
                travel_time_multiplier=self.real(multiplier_name),
                probability_basis_points=self.integer(probability_name),
                evidence_class=evidence_class,
                is_baseline=is_baseline,
            )
            for role, multiplier_name, probability_name, evidence_class, is_baseline in _TIER_SHAPE
        )

    # -- objective and solver ------------------------------------------------

    @property
    def minimum_coverage_basis_points(self) -> int:
        return self.integer(AssumptionName.CONSTRAINT_MINIMUM_COVERAGE_BPS)

    @property
    def solver_max_time_seconds(self) -> float:
        return self.real(AssumptionName.SOLVER_MAX_TIME_SECONDS)

    def objective_weights(self, *, allow_uncovered_demand: bool) -> ObjectiveWeights:
        """Weights for this set, stamped with the reference that produced them.

        The coverage-loss branch lives here rather than at the call site so that
        the zero case is a recorded, explained assumption instead of a bare
        literal in a request handler.
        """
        coverage_loss = (
            self.integer(AssumptionName.OBJECTIVE_COVERAGE_LOSS_WEIGHT)
            if allow_uncovered_demand
            else self.integer(AssumptionName.OBJECTIVE_COVERAGE_LOSS_WEIGHT_MANDATORY)
        )
        return ObjectiveWeights(
            assumption_version=self.token,
            expected_travel=self.integer(AssumptionName.OBJECTIVE_EXPECTED_TRAVEL_WEIGHT),
            p95_travel=self.integer(AssumptionName.OBJECTIVE_P95_TRAVEL_WEIGHT),
            facility_cost=self.integer(AssumptionName.OBJECTIVE_FACILITY_COST_WEIGHT),
            failure_exposure=self.integer(AssumptionName.OBJECTIVE_FAILURE_EXPOSURE_WEIGHT),
            coverage_loss=coverage_loss,
        )
