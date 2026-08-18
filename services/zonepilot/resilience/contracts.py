"""Contracts for R4 Network Resilience and Stress Testing."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import math
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from services.temporal.contracts import EvidenceClass


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


class ResilienceMetrics(StrictContract):
    coverage_basis_points: int = Field(ge=0, le=10_000)
    p50_duration_seconds: int = Field(ge=0)
    p90_duration_seconds: int = Field(ge=0)
    p95_duration_seconds: int = Field(ge=0)
    disconnected_zones_count: int = Field(ge=0)
    redundancy_index_basis_points: int = Field(ge=0, le=10_000)
    failure_exposure_score: int = Field(ge=0, le=10_000)
    capacity_loss_basis_points: int = Field(ge=0, le=10_000)

    @model_validator(mode="after")
    def validate_quantiles(self) -> Self:
        if self.p50_duration_seconds > self.p90_duration_seconds:
            raise ValueError("p50_duration_seconds must not exceed p90_duration_seconds")
        if self.p90_duration_seconds > self.p95_duration_seconds:
            raise ValueError("p90_duration_seconds must not exceed p95_duration_seconds")
        return self


class ScenarioComparison(StrictContract):
    baseline_scenario_id: str
    stressed_scenario_id: str
    coverage_delta_basis_points: int
    p95_inflation_seconds: int
    p95_inflation_basis_points: int
    additional_disconnected_zones: int
    capacity_loss_basis_points: int
    resilience_grade: str


class ResilienceEvaluationResult(StrictContract):
    evaluation_id: str = Field(min_length=1)
    scenario: ResilienceScenario
    metrics: ResilienceMetrics
    baseline_comparison: ScenarioComparison | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    code_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    fail_closed: bool = False
