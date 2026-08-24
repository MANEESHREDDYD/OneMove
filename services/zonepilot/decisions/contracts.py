"""Contracts for R7 Decision Ledger, Time Travel, Replay, and Shadow Evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.temporal.contracts import OutcomeStatus


class ShadowState(str, Enum):
    FROZEN_AWAITING_FUTURE = "FROZEN_AWAITING_FUTURE"
    JOINED_FUTURE_OBSERVED = "JOINED_FUTURE_OBSERVED"
    EVALUATED = "EVALUATED"


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DecisionRecord(StrictContract):
    schema_name: str = Field(default="zonepilot.decision_record", min_length=1)
    schema_version: str = Field(default="1.0.0", min_length=1)
    decision_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    decision_time: datetime
    network_version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    feature_snapshot_hash: str = Field(min_length=1)
    selected_action: str = Field(min_length=1)
    opened_facilities: tuple[str, ...]
    objective_value: int = Field(ge=0)
    expected_travel_seconds: int = Field(ge=0)

    # Legacy name. The value is a probability-weighted P95 across SCENARIO TOTAL
    # demand-weighted travel, so its unit is demand_units*seconds, not seconds.
    # Frozen records keep this field so history stays readable; new records also
    # populate p95_scenario_total_travel_demand_seconds, which states the unit.
    p95_travel_seconds: int = Field(ge=0)
    p95_scenario_total_travel_demand_seconds: int | None = Field(default=None, ge=0)

    coverage_basis_points: int = Field(ge=0, le=10_000)

    # The mathematical policy this decision was produced under. None means the
    # record predates policy versioning and must be treated as legacy: replaying
    # it under the current policy would compare answers from two different
    # models and report a difference as if it were drift.
    optimization_policy_version: str | None = None
    graph_version: str = Field(min_length=1)
    osrm_bundle_hash: str = Field(min_length=1)
    solver_version: str = Field(min_length=1)
    code_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    evidence_ids: tuple[str, ...] = ()
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_pit_rule(self) -> Self:
        if self.decision_time > self.recorded_at:
            raise ValueError("decision_time cannot be in the future relative to recorded_at")
        return self


class DecisionReplayResult(StrictContract):
    original_decision_id: str
    replayed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pit_valid: bool
    reproduced_exact_action: bool
    reproduced_exact_facilities: bool
    objective_match: bool
    match_status: str = "EXACT_MATCH"
    expected_hash: str | None = None
    actual_hash: str | None = None
    difference: dict[str, str | int | float | list[str]] = Field(default_factory=dict)
    reason: str | None = None
    code_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class ShadowEvaluation(StrictContract):
    shadow_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    frozen_decision_time: datetime
    future_observation_time: datetime
    shadow_state: ShadowState
    predicted_p95_seconds: int
    actual_observed_p95_seconds: int | None = None
    regret_seconds: int | None = None
    outcome_status: OutcomeStatus = OutcomeStatus.PENDING
    evaluated_at: datetime | None = None
