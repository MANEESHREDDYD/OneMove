"""Contracts for R4 Network Resilience and Stress Testing.

Truth rules enforced here (F-010, reopened):

* A metric is either **DERIVED** from the frozen authentic travel matrix and the
  frozen scenario inputs, or it is **UNAVAILABLE** with a stated reason. There is
  no third state. ``0`` is a measurement, never a stand-in for "not computed":
  an operator must be able to distinguish "no zone was disconnected" from "we
  never worked out whether a zone was disconnected".
* Every ``None`` metric must carry a matching entry in
  :attr:`ResilienceMetrics.unavailable`, and every derived metric must not. The
  model validator makes an unexplained gap unconstructible.
* Evidence classes are truthful and separated: ``PUBLIC_GEOGRAPHIC`` for the
  routed baseline matrix, ``SIMULATED`` for the counterfactual disruption laid
  on top of it, ``ASSUMPTION`` for declared thresholds and capacity ledgers, and
  ``DERIVED`` for anything computed from those.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.temporal.contracts import EvidenceClass

BASIS_POINTS = 10_000
MAX_TRAVEL_SECONDS = 7 * 24 * 60 * 60

#: Every operational metric the resilience record can carry. Kept as data so the
#: "derived or explicitly unavailable" invariant can be checked exhaustively.
METRIC_FIELDS: tuple[str, ...] = (
    "coverage_basis_points",
    "p50_duration_seconds",
    "p90_duration_seconds",
    "p95_duration_seconds",
    "disconnected_zones_count",
    "redundancy_index_basis_points",
    "failure_exposure_score",
    "capacity_loss_basis_points",
)

#: Evidence a routing baseline may legitimately claim. A baseline may never be
#: SIMULATED or an ASSUMPTION -- that was the original F-010 fabrication.
ROUTING_BASELINE_EVIDENCE: frozenset[EvidenceClass] = frozenset(
    {
        EvidenceClass.OBSERVED,
        EvidenceClass.PUBLIC_OFFICIAL,
        EvidenceClass.PUBLIC_GEOGRAPHIC,
    }
)


class ScenarioType(str, Enum):
    ROAD_CLOSURE = "ROAD_CLOSURE"
    FACILITY_OUTAGE = "FACILITY_OUTAGE"
    CONGESTION_SPIKE = "CONGESTION_SPIKE"
    HEAVY_RAIN = "HEAVY_RAIN"
    CAPACITY_REDUCTION = "CAPACITY_REDUCTION"
    COMPOUND_FAILURE = "COMPOUND_FAILURE"


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ResilienceScenario(StrictContract):
    schema_name: str = Field(default="zonepilot.resilience_scenario", min_length=1)
    schema_version: str = Field(default="1.0.0", min_length=1)
    scenario_id: str = Field(min_length=1)
    scenario_type: ScenarioType
    description: str = Field(min_length=1)
    evidence_class: EvidenceClass = EvidenceClass.SIMULATED
    parameters: dict[str, Any]
    seed: int = 42
    graph_version: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_evidence_class(self) -> Self:
        if self.evidence_class not in {EvidenceClass.SIMULATED, EvidenceClass.DERIVED}:
            raise ValueError(f"Counterfactual scenarios cannot have evidence_class={self.evidence_class.value}")
        return self


class MetricUnavailable(StrictContract):
    """A metric that was not computed, and why it could not be."""

    metric: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def metric_is_known(self) -> Self:
        if self.metric not in METRIC_FIELDS:
            raise ValueError(f"unknown resilience metric: {self.metric}")
        return self


class CoverageAssumption(StrictContract):
    """Declared definition of "covered" -- a policy threshold, not a measurement.

    A threshold is a definition rather than data about the world, so it may be
    defaulted; but it must be named, versioned and frozen into the evaluation
    record so a reader can see which definition produced the number.
    """

    assumption_id: str = Field(min_length=1)
    max_travel_seconds: int = Field(gt=0, le=MAX_TRAVEL_SECONDS)
    source: str = Field(min_length=1)
    evidence_class: EvidenceClass = EvidenceClass.ASSUMPTION


class CapacityAssumption(StrictContract):
    """Explicitly frozen per-facility capacity ledger.

    ZonePilot holds no observed facility capacity. Any capacity figure is an
    assumption supplied by the caller and is labelled as one; absent this
    object, capacity-derived metrics are UNAVAILABLE rather than invented.
    """

    assumption_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    facility_capacity_units: dict[str, int]
    evidence_class: EvidenceClass = EvidenceClass.ASSUMPTION

    @model_validator(mode="after")
    def capacities_are_positive(self) -> Self:
        if not self.facility_capacity_units:
            raise ValueError("capacity assumption must name at least one facility")
        for facility_id, units in self.facility_capacity_units.items():
            if not facility_id.strip():
                raise ValueError("capacity assumption facility ids must not be blank")
            if units <= 0:
                raise ValueError(f"capacity for {facility_id} must be positive")
        return self


class ScenarioDisruption(StrictContract):
    """The SIMULATED counterfactual, expressed at travel-matrix granularity.

    Only effects that can actually be applied to a facility x demand duration
    matrix live here. A scenario parameter that cannot be translated into one of
    these effects (an OSM way id, a rainfall depth) is not silently dropped --
    the caller is refused, because an unmodelled disruption evaluated against an
    undisturbed matrix would report the baseline as if it were the failure.
    """

    disabled_facility_ids: tuple[str, ...] = ()
    unreachable_pairs: tuple[tuple[str, str], ...] = ()
    travel_time_inflation_basis_points: int = Field(default=0, ge=0, le=1_000_000)
    facility_capacity_basis_points: dict[str, int] = Field(default_factory=dict)
    evidence_class: EvidenceClass = EvidenceClass.SIMULATED

    @model_validator(mode="after")
    def disruption_is_coherent(self) -> Self:
        if self.evidence_class is not EvidenceClass.SIMULATED:
            raise ValueError("a counterfactual disruption is SIMULATED by construction")
        if len(set(self.disabled_facility_ids)) != len(self.disabled_facility_ids):
            raise ValueError("disabled_facility_ids must be unique")
        for _, bps in self.facility_capacity_basis_points.items():
            if bps < 0 or bps > BASIS_POINTS:
                raise ValueError("facility_capacity_basis_points must be within 0..10000")
        return self

    @property
    def is_empty(self) -> bool:
        return not (
            self.disabled_facility_ids
            or self.unreachable_pairs
            or self.travel_time_inflation_basis_points
            or self.facility_capacity_basis_points
        )

    @property
    def affects_capacity(self) -> bool:
        return bool(self.disabled_facility_ids or self.facility_capacity_basis_points)


class FrozenScenarioInputs(StrictContract):
    """Everything an evaluation is derived from, frozen before anything persists.

    The digest covers the routed baseline, the simulated disruption and the
    declared assumptions, so a stored result can be re-derived and checked.
    """

    matrix_id: str = Field(min_length=1)
    graph_version: str = Field(min_length=1)
    router: str = Field(min_length=1)
    router_version: str = Field(min_length=1)
    matrix_evidence_class: EvidenceClass
    facility_ids: tuple[str, ...] = Field(min_length=1)
    demand_ids: tuple[str, ...] = Field(min_length=1)
    baseline_durations_seconds: tuple[tuple[int, ...], ...]
    disruption: ScenarioDisruption
    coverage_assumption: CoverageAssumption | None = None
    capacity_assumption: CapacityAssumption | None = None
    inputs_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def inputs_are_coherent(self) -> Self:
        if self.matrix_evidence_class not in ROUTING_BASELINE_EVIDENCE:
            raise ValueError(
                f"a routing baseline cannot claim evidence_class={self.matrix_evidence_class.value}; "
                "simulated or assumed travel times are not a baseline"
            )
        if len(self.baseline_durations_seconds) != len(self.facility_ids):
            raise ValueError("baseline matrix must contain one row per facility_id")
        for row in self.baseline_durations_seconds:
            if len(row) != len(self.demand_ids):
                raise ValueError("baseline matrix rows must contain one duration per demand_id")
        known_facilities = set(self.facility_ids)
        unknown = set(self.disruption.disabled_facility_ids) - known_facilities
        if unknown:
            raise ValueError(f"disruption disables facilities absent from the matrix: {sorted(unknown)}")
        return self

    def lineage(self) -> dict[str, Any]:
        """Human- and audit-readable provenance for the persisted record."""
        return {
            "matrix_id": self.matrix_id,
            "graph_version": self.graph_version,
            "router": self.router,
            "router_version": self.router_version,
            "matrix_evidence_class": self.matrix_evidence_class.value,
            "facility_count": len(self.facility_ids),
            "demand_count": len(self.demand_ids),
            "inputs_sha256": self.inputs_sha256,
            "disruption_evidence_class": self.disruption.evidence_class.value,
            "disruption": {
                "disabled_facility_ids": list(self.disruption.disabled_facility_ids),
                "unreachable_pair_count": len(self.disruption.unreachable_pairs),
                "travel_time_inflation_basis_points": self.disruption.travel_time_inflation_basis_points,
                "facility_capacity_basis_points": dict(self.disruption.facility_capacity_basis_points),
            },
            "coverage_assumption": (
                None
                if self.coverage_assumption is None
                else {
                    "assumption_id": self.coverage_assumption.assumption_id,
                    "max_travel_seconds": self.coverage_assumption.max_travel_seconds,
                    "source": self.coverage_assumption.source,
                    "evidence_class": self.coverage_assumption.evidence_class.value,
                }
            ),
            "capacity_assumption": (
                None
                if self.capacity_assumption is None
                else {
                    "assumption_id": self.capacity_assumption.assumption_id,
                    "source": self.capacity_assumption.source,
                    "evidence_class": self.capacity_assumption.evidence_class.value,
                }
            ),
        }


class ResilienceMetrics(StrictContract):
    """Derived operational metrics. ``None`` means UNAVAILABLE, never zero."""

    coverage_basis_points: int | None = Field(default=None, ge=0, le=BASIS_POINTS)
    p50_duration_seconds: int | None = Field(default=None, ge=0)
    p90_duration_seconds: int | None = Field(default=None, ge=0)
    p95_duration_seconds: int | None = Field(default=None, ge=0)
    disconnected_zones_count: int | None = Field(default=None, ge=0)
    redundancy_index_basis_points: int | None = Field(default=None, ge=0, le=BASIS_POINTS)
    failure_exposure_score: int | None = Field(default=None, ge=0, le=BASIS_POINTS)
    capacity_loss_basis_points: int | None = Field(default=None, ge=0, le=BASIS_POINTS)
    evidence_class: EvidenceClass = EvidenceClass.DERIVED
    unavailable: tuple[MetricUnavailable, ...] = ()

    @model_validator(mode="after")
    def every_gap_is_explained(self) -> Self:
        named = [entry.metric for entry in self.unavailable]
        if len(named) != len(set(named)):
            raise ValueError("a metric may be declared unavailable only once")
        named_set = set(named)
        for field in METRIC_FIELDS:
            value = getattr(self, field)
            if value is None and field not in named_set:
                raise ValueError(f"{field} was not computed and must declare why it is unavailable")
            if value is not None and field in named_set:
                raise ValueError(f"{field} cannot be both derived and unavailable")

        quantiles = [self.p50_duration_seconds, self.p90_duration_seconds, self.p95_duration_seconds]
        if all(value is not None for value in quantiles):
            p50, p90, p95 = quantiles
            if p50 > p90:  # type: ignore[operator]
                raise ValueError("p50_duration_seconds must not exceed p90_duration_seconds")
            if p90 > p95:  # type: ignore[operator]
                raise ValueError("p90_duration_seconds must not exceed p95_duration_seconds")
        return self

    @property
    def is_complete(self) -> bool:
        return not self.unavailable

    def unavailable_reasons(self) -> dict[str, str]:
        return {entry.metric: entry.reason for entry in self.unavailable}


class ScenarioComparison(StrictContract):
    baseline_scenario_id: str
    stressed_scenario_id: str
    coverage_delta_basis_points: int | None = None
    p95_inflation_seconds: int | None = None
    p95_inflation_basis_points: int | None = None
    additional_disconnected_zones: int | None = None
    capacity_loss_basis_points: int | None = None
    resilience_grade: str


class ResilienceEvaluationResult(StrictContract):
    evaluation_id: str = Field(min_length=1)
    scenario: ResilienceScenario
    metrics: ResilienceMetrics
    inputs: FrozenScenarioInputs
    baseline_comparison: ScenarioComparison | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    code_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    fail_closed: bool = False
