"""Contracts for R5 Proxy Economics and Experiment Registry."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from services.temporal.contracts import EvidenceClass


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ProxyEconomicsMetric(StrictContract):
    total_fixed_cost_units: int = Field(ge=0)
    total_variable_cost_proxy: float = Field(ge=0.0)
    cost_per_coverage_point: float = Field(ge=0.0)
    cost_per_p95_minute_reduced: float = Field(ge=0.0)
    incremental_resilience_proxy_cost: float = Field(ge=0.0)
    evidence_class: EvidenceClass = EvidenceClass.ASSUMPTION
    assumption_version: str = Field(min_length=1)

    @field_validator("total_variable_cost_proxy", "cost_per_coverage_point", "cost_per_p95_minute_reduced", "incremental_resilience_proxy_cost")
    @classmethod
    def numeric_is_finite(cls, val: float) -> float:
        if not math.isfinite(val):
            raise ValueError("economic proxy values must be finite")
        return val


class FrontierPoint(StrictContract):
    solution_id: str
    open_facility_count: int = Field(ge=1)
    total_fixed_cost_units: int = Field(ge=0)
    p95_travel_seconds: int = Field(ge=0)
    coverage_basis_points: int = Field(ge=0, le=10_000)
    resilience_score: int = Field(ge=0, le=10_000)
    is_pareto_optimal: bool = True


class ExperimentStatus(str, Enum):
    PROPOSED = "PROPOSED"
    FROZEN = "FROZEN"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    INCONCLUSIVE = "INCONCLUSIVE"


class ExperimentDefinition(StrictContract):
    experiment_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    target_metric: str = Field(min_length=1)
    parameters: dict[str, Any]
    status: ExperimentStatus = ExperimentStatus.FROZEN
    frozen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_class: EvidenceClass = EvidenceClass.DERIVED


class ExperimentEvaluation(StrictContract):
    experiment_id: str = Field(min_length=1)
    definition: ExperimentDefinition
    measured_baseline: float
    measured_treatment: float
    effect_size: float
    hypothesis_confirmed: bool
    confidence_description: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    code_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
