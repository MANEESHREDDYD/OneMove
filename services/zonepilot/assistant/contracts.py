"""Contracts for R8 Typed Deterministic Assistant Layer."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ToolName(str, Enum):
    GET_ZONE_STATE = "get_zone_state"
    GET_NETWORK_SNAPSHOT = "get_network_snapshot"
    GET_FORECAST = "get_forecast"
    RUN_SCENARIO = "run_scenario"
    GET_SCENARIO = "get_scenario"
    RUN_OPTIMIZATION = "run_optimization"
    GET_OPTIMIZATION = "get_optimization"
    COMPARE_DECISIONS = "compare_decisions"
    GET_RESILIENCE_RESULT = "get_resilience_result"
    GET_EXPERIMENT = "get_experiment"
    GET_DECISION = "get_decision"
    GET_OUTCOME = "get_outcome"
    GET_EVIDENCE = "get_evidence"
    EXPLAIN_DECISION = "explain_decision"


class AssistantToolCall(StrictContract):
    tool_name: ToolName
    arguments: dict[str, Any]
    workspace_id: str = Field(min_length=1)


class AssistantToolResult(StrictContract):
    tool_name: ToolName
    result_data: dict[str, Any]
    evidence_ids: tuple[str, ...] = ()
    execution_time_ms: int = Field(ge=0)
    success: bool = True
    error_message: str | None = None


class NumericalClaimBinding(StrictContract):
    claim_text: str
    numeric_value: float
    source_field: str
    evidence_id: str


class AssistantResponse(StrictContract):
    answer_text: str
    bound_claims: tuple[NumericalClaimBinding, ...] = ()
    referenced_evidence_ids: tuple[str, ...] = ()
    tools_executed: tuple[ToolName, ...] = ()
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
