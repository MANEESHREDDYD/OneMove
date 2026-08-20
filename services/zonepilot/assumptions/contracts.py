"""Versioned, digest-sealed assumption contracts.

An assumption is a number nobody measured. The programme this package exists to
serve removes the opposite claim: values that were invented at a keyboard,
inlined into a request handler, and then reported as though they were observed
economics. The remedy is not to move the numbers somewhere tidier. It is to give
every one of them an identity, a stated source, a rationale, a validity range, a
sensitivity range, and a cryptographic seal over the whole set -- so that a
decision can name the exact assumptions it was made under, and a replay can load
those same assumptions back rather than whatever is current today.

Three invariants carry the weight:

* ``AssumptionRecord`` cannot be constructed without ``source`` and
  ``rationale``. There is no default and no placeholder.
* ``AssumptionSet.sha256`` is recomputed on validation. A set whose seal does not
  match its contents does not deserialize at all, so a tampered or drifted set
  fails closed instead of being replayed as authentic.
* The digest is taken over records in canonical order, so it identifies content,
  not the order the records happened to be listed in.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Literal, Self, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.temporal.contracts import EvidenceClass

SHA256_PATTERN = r"^[0-9a-f]{64}$"
NAME_PATTERN = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
VERSION_PATTERN = r"^[0-9A-Za-z][0-9A-Za-z.\-]*$"
SET_ID_PATTERN = r"^[a-z][a-z0-9\-]*$"

_TOKEN_PATTERN = re.compile(
    r"^(?P<assumption_set_id>[a-z][a-z0-9\-]*)"
    r"@(?P<version>[0-9A-Za-z][0-9A-Za-z.\-]*)"
    r"\+sha256\.(?P<sha256>[0-9a-f]{64})$"
)

#: The only honest source string for a number that was picked, not observed.
#: Anything more authoritative-sounding would reintroduce the defect this package
#: exists to remove: a proxy presented as measured operator economics.
UNMEASURED_PILOT_PROXY = "proxy chosen for the pilot, not measured"

AssumptionValue = int | float


class AssumptionName:
    """Canonical assumption names.

    Referencing these instead of raw strings makes a rename a grep-able edit
    rather than a silent lookup miss at request time.
    """

    FACILITY_CAPACITY_UNITS = "facility.capacity_units"
    FACILITY_FIXED_COST_UNITS = "facility.fixed_cost_units"
    FACILITY_FAILURE_EXPOSURE_BPS_PER_RANK = "facility.failure_exposure_basis_points_per_rank"

    DEMAND_COMMERCIAL_POI_WEIGHT = "demand.commercial_poi_weight"
    DEMAND_INTERSECTION_WEIGHT = "demand.intersection_weight"
    DEMAND_MISSING_FEATURE_DEFAULT = "demand.missing_feature_count_default"
    DEMAND_MINIMUM_UNITS = "demand.minimum_demand_units"

    SCENARIO_BASELINE_TRAVEL_MULTIPLIER = "scenario.baseline.travel_time_multiplier"
    SCENARIO_DEGRADED_TRAVEL_MULTIPLIER = "scenario.degraded.travel_time_multiplier"
    SCENARIO_SEVERE_TRAVEL_MULTIPLIER = "scenario.severe.travel_time_multiplier"
    SCENARIO_BASELINE_PROBABILITY_BPS = "scenario.baseline.probability_basis_points"
    SCENARIO_DEGRADED_PROBABILITY_BPS = "scenario.degraded.probability_basis_points"
    SCENARIO_SEVERE_PROBABILITY_BPS = "scenario.severe.probability_basis_points"

    OBJECTIVE_EXPECTED_TRAVEL_WEIGHT = "objective.expected_travel_weight"
    OBJECTIVE_P95_TRAVEL_WEIGHT = "objective.p95_travel_weight"
    OBJECTIVE_FACILITY_COST_WEIGHT = "objective.facility_cost_weight"
    OBJECTIVE_FAILURE_EXPOSURE_WEIGHT = "objective.failure_exposure_weight"
    OBJECTIVE_COVERAGE_LOSS_WEIGHT = "objective.coverage_loss_weight"
    OBJECTIVE_COVERAGE_LOSS_WEIGHT_MANDATORY = "objective.coverage_loss_weight_when_coverage_mandatory"

    CONSTRAINT_MINIMUM_COVERAGE_BPS = "constraints.minimum_coverage_basis_points"
    SOLVER_MAX_TIME_SECONDS = "solver.max_time_seconds"


class AssumptionStatus(str, Enum):
    """Lifecycle of an assumption set.

    ``SUPERSEDED`` and ``RETIRED`` sets stay resolvable forever: a decision frozen
    under a set that has since been replaced must still be replayable under it.
    Only ``ACTIVE`` is eligible to be selected for a *new* decision.
    """

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class StrictContract(BaseModel):
    """Reject unknown fields, implicit coercion, and mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _require_text(value: str, field: str, minimum: int) -> str:
    stripped = value.strip()
    if len(stripped) < minimum:
        raise ValueError(f"{field} must be at least {minimum} non-blank characters; assumptions are not self-evident")
    return value


def _number_token(value: AssumptionValue) -> str:
    """Exact, stable textual form of a number for hashing.

    ``repr`` round-trips IEEE-754 doubles exactly and distinguishes ``1500`` from
    ``1500.0``, so a type change is a content change and moves the digest.
    """
    return repr(value)


class AssumptionRecord(StrictContract):
    """One named number, with everything a reader needs to distrust it correctly."""

    schema_name: Literal["zonepilot.assumption_record"] = "zonepilot.assumption_record"
    schema_version: Literal["1.0.0"] = "1.0.0"
    assumption_id: str = Field(min_length=1, max_length=200)
    assumption_set_id: str = Field(pattern=SET_ID_PATTERN)
    name: str = Field(pattern=NAME_PATTERN)
    value: AssumptionValue
    unit: str = Field(min_length=1, max_length=80)
    evidence_class: Literal[EvidenceClass.ASSUMPTION] = EvidenceClass.ASSUMPTION
    source: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=2000)
    valid_min: AssumptionValue
    valid_max: AssumptionValue
    sensitivity_low: AssumptionValue
    sensitivity_high: AssumptionValue
    effective_at: datetime

    @field_validator("source")
    @classmethod
    def source_is_stated(cls, value: str) -> str:
        return _require_text(value, "source", 8)

    @field_validator("rationale")
    @classmethod
    def rationale_is_stated(cls, value: str) -> str:
        return _require_text(value, "rationale", 20)

    @field_validator("effective_at")
    @classmethod
    def effective_at_is_absolute(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("effective_at must be timezone-aware; a naive instant has no point-in-time meaning")
        return value

    @model_validator(mode="after")
    def ranges_are_coherent(self) -> Self:
        if self.valid_min > self.valid_max:
            raise ValueError(f"{self.name}: valid_min must not exceed valid_max")
        if not (self.valid_min <= self.value <= self.valid_max):
            raise ValueError(f"{self.name}: value {self.value!r} is outside its own declared validity range")
        if self.sensitivity_low > self.sensitivity_high:
            raise ValueError(f"{self.name}: sensitivity_low must not exceed sensitivity_high")
        if not (self.valid_min <= self.sensitivity_low and self.sensitivity_high <= self.valid_max):
            raise ValueError(f"{self.name}: sensitivity range must lie inside the validity range")
        if not (self.sensitivity_low <= self.value <= self.sensitivity_high):
            raise ValueError(f"{self.name}: the base value must lie inside its own sensitivity range")
        return self

    @property
    def sensitivity_range(self) -> tuple[AssumptionValue, AssumptionValue]:
        return (self.sensitivity_low, self.sensitivity_high)

    def canonical_payload(self) -> dict[str, str]:
        """Everything about this record that the set digest commits to."""
        return {
            "assumption_id": self.assumption_id,
            "assumption_set_id": self.assumption_set_id,
            "name": self.name,
            "unit": self.unit,
            "evidence_class": self.evidence_class.value,
            "source": self.source,
            "rationale": self.rationale,
            "value": _number_token(self.value),
            "valid_min": _number_token(self.valid_min),
            "valid_max": _number_token(self.valid_max),
            "sensitivity_low": _number_token(self.sensitivity_low),
            "sensitivity_high": _number_token(self.sensitivity_high),
            "effective_at": self.effective_at.astimezone(timezone.utc).isoformat(),
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
        }

    def with_value(self, value: AssumptionValue) -> AssumptionRecord:
        """Return a copy carrying a different value. The receiver is unchanged."""
        return self.model_copy(update={"value": value})


def canonical_record_order(records: Iterable[AssumptionRecord]) -> tuple[AssumptionRecord, ...]:
    """Total order used for hashing, so the digest covers content, not listing order."""
    return tuple(sorted(records, key=lambda record: (record.name, record.assumption_id)))


def compute_assumption_digest(
    records: Iterable[AssumptionRecord],
    *,
    assumption_set_id: str,
    version: str,
) -> str:
    """SHA-256 over the set identity and its canonically ordered records.

    Order-independent by construction, and total over record content: changing any
    field of any record -- including its rationale -- yields a different digest.
    """
    payload = {
        "schema": "zonepilot.assumption_set_digest.1.0.0",
        "assumption_set_id": assumption_set_id,
        "version": version,
        "records": [record.canonical_payload() for record in canonical_record_order(records)],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AssumptionSetRef(StrictContract):
    """The three things a replay needs in order to find one exact historical set."""

    assumption_set_id: str = Field(pattern=SET_ID_PATTERN)
    version: str = Field(pattern=VERSION_PATTERN)
    sha256: str = Field(pattern=SHA256_PATTERN)

    def token(self) -> str:
        """A single self-describing string, small enough for a lineage column."""
        return f"{self.assumption_set_id}@{self.version}+sha256.{self.sha256}"

    @classmethod
    def parse(cls, token: str) -> AssumptionSetRef:
        match = _TOKEN_PATTERN.match((token or "").strip())
        if match is None:
            raise ValueError(
                f"{token!r} is not a pinned assumption reference (expected set-id@version+sha256.<64 hex>)"
            )
        return cls(**match.groupdict())

    @classmethod
    def is_token(cls, token: str) -> bool:
        return _TOKEN_PATTERN.match((token or "").strip()) is not None


class AssumptionSet(StrictContract):
    """An immutable, digest-sealed collection of assumptions."""

    schema_name: Literal["zonepilot.assumption_set"] = "zonepilot.assumption_set"
    schema_version: Literal["1.0.0"] = "1.0.0"
    assumption_set_id: str = Field(pattern=SET_ID_PATTERN)
    version: str = Field(pattern=VERSION_PATTERN)
    sha256: str = Field(pattern=SHA256_PATTERN)
    created_at: datetime
    effective_at: datetime
    owner: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    status: AssumptionStatus
    records: tuple[AssumptionRecord, ...] = Field(min_length=1, max_length=500)
    #: Lineage strings written before this registry existed, which still identify
    #: this set. Kept so a decision frozen under the old bare version string
    #: replays against the real historical values instead of today's.
    legacy_tokens: tuple[str, ...] = ()

    @field_validator("created_at", "effective_at")
    @classmethod
    def instants_are_absolute(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("assumption set timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def seal_matches_contents(self) -> Self:
        names = [record.name for record in self.records]
        if len(names) != len(set(names)):
            raise ValueError("assumption names must be unique within a set")
        ids = [record.assumption_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("assumption_id values must be unique within a set")
        foreign = sorted({record.assumption_set_id for record in self.records} - {self.assumption_set_id})
        if foreign:
            raise ValueError(f"records belong to a different assumption set: {', '.join(foreign)}")
        recomputed = compute_assumption_digest(
            self.records,
            assumption_set_id=self.assumption_set_id,
            version=self.version,
        )
        if recomputed != self.sha256:
            raise ValueError(
                "assumption set seal is broken: declared sha256 "
                f"{self.sha256[:16]}... does not match the digest of its records ({recomputed[:16]}...)"
            )
        return self

    @property
    def ref(self) -> AssumptionSetRef:
        return AssumptionSetRef(
            assumption_set_id=self.assumption_set_id,
            version=self.version,
            sha256=self.sha256,
        )

    @property
    def token(self) -> str:
        return self.ref.token()

    def record(self, name: str) -> AssumptionRecord:
        for candidate in self.records:
            if candidate.name == name:
                return candidate
        raise KeyError(f"assumption {name!r} is not defined in {self.assumption_set_id}@{self.version}")

    def value(self, name: str) -> AssumptionValue:
        return self.record(name).value

    def names(self) -> tuple[str, ...]:
        return tuple(record.name for record in canonical_record_order(self.records))


def seal_assumption_set(
    *,
    assumption_set_id: str,
    version: str,
    created_at: datetime,
    effective_at: datetime,
    owner: str,
    description: str,
    status: AssumptionStatus,
    records: Sequence[AssumptionRecord],
    legacy_tokens: Sequence[str] = (),
) -> AssumptionSet:
    """Build a set and compute its seal, rather than asserting one by hand."""
    digest = compute_assumption_digest(records, assumption_set_id=assumption_set_id, version=version)
    return AssumptionSet(
        assumption_set_id=assumption_set_id,
        version=version,
        sha256=digest,
        created_at=created_at,
        effective_at=effective_at,
        owner=owner,
        description=description,
        status=status,
        records=tuple(records),
        legacy_tokens=tuple(legacy_tokens),
    )
