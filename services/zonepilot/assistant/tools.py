"""Deterministic execution engine for typed Assistant tools."""

from __future__ import annotations

import re
import time
from typing import Any, Callable

from services.zonepilot.assistant.contracts import (
    AssistantResponse,
    AssistantToolCall,
    AssistantToolResult,
    NumericalClaimBinding,
    ToolName,
)

# Prompt injection pattern protection
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"<script.*?>.*?</script>", re.IGNORECASE),
    re.compile(r"drop\s+table", re.IGNORECASE),
    re.compile(r"union\s+select", re.IGNORECASE),
]


def sanitize_input(text: str) -> str:
    """Sanitize external strings to prevent prompt injection and XSS."""
    if not isinstance(text, str):
        return str(text)
    sanitized = text
    for pattern in _INJECTION_PATTERNS:
        sanitized = pattern.sub("[FILTERED_INPUT]", sanitized)
    return sanitized.strip()


class AssistantToolRegistry:
    def __init__(self) -> None:
        self._handlers: dict[ToolName, Callable[[dict[str, Any], str], dict[str, Any]]] = {}

    def register(self, tool_name: ToolName, handler: Callable[[dict[str, Any], str], dict[str, Any]]) -> None:
        self._handlers[tool_name] = handler

    def execute(self, call: AssistantToolCall) -> AssistantToolResult:
        handler = self._handlers.get(call.tool_name)
        if not handler:
            return AssistantToolResult(
                tool_name=call.tool_name,
                result_data={},
                execution_time_ms=0,
                success=False,
                error_message=f"Unknown tool: {call.tool_name.value}",
            )

        start = time.perf_counter()
        try:
            # Sanitize input arguments
            sanitized_args = {k: sanitize_input(v) if isinstance(v, str) else v for k, v in call.arguments.items()}
            data = handler(sanitized_args, call.workspace_id)
            elapsed = int((time.perf_counter() - start) * 1000)
            evidence_ids = tuple(data.get("evidence_ids", []))
            return AssistantToolResult(
                tool_name=call.tool_name,
                result_data=data,
                evidence_ids=evidence_ids,
                execution_time_ms=elapsed,
                success=True,
            )
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            return AssistantToolResult(
                tool_name=call.tool_name,
                result_data={},
                execution_time_ms=elapsed,
                success=False,
                error_message=str(e),
            )


def create_default_registry() -> AssistantToolRegistry:
    registry = AssistantToolRegistry()

    # Register deterministic tool handlers
    registry.register(
        ToolName.GET_ZONE_STATE,
        lambda args, ws: {
            "zone_id": args.get("zone_id", "8860145b59fffff"),
            "name": "Bengaluru Central Pilot Zone",
            "road_length_m": 4250.0,
            "intersection_count": 28,
            "poi_count": 14,
            "evidence_ids": ["ev-osm-blr-8860145b59fffff"],
        },
    )

    registry.register(
        ToolName.GET_NETWORK_SNAPSHOT,
        lambda args, ws: {
            "layer": args.get("layer", "zones"),
            "zone_count": 94,
            "status": "HEALTHY",
            "evidence_ids": ["ev-gold-network-h3r8"],
        },
    )

    registry.register(
        ToolName.GET_FORECAST,
        lambda args, ws: {
            "zone_id": args.get("zone_id", "8860145b59fffff"),
            "provider": "open-meteo",
            "precipitation_mm": 0.0,
            "temperature_c": 24.5,
            "status": "AVAILABLE",
            "evidence_ids": ["ev-om-hourly-20260818"],
        },
    )

    registry.register(
        ToolName.GET_SCENARIO,
        lambda args, ws: {
            "scenario_id": args.get("scenario_id", "s1_free_flow"),
            "inflation_basis_points": 10000,
            "probability_basis_points": 6000,
            "evidence_ids": ["ev-scenario-s1"],
        },
    )

    registry.register(
        ToolName.GET_EXPERIMENT,
        lambda args, ws: {
            "experiment_id": args.get("experiment_id", "EXP-01"),
            "title": "Early Network Degradation",
            "status": "FROZEN",
            "evidence_ids": ["ev-exp-01"],
        },
    )

    registry.register(
        ToolName.EXPLAIN_DECISION,
        lambda args, ws: {
            "decision_id": args.get("decision_id", "dec-sample"),
            "action": "OPEN_FACILITIES",
            "opened_facilities": ["fac:01", "fac:04", "fac:07", "fac:11"],
            "p95_travel_seconds": 780,
            "coverage_pct": 98.4,
            "reasoning": "Optimized trade-off between coverage and fixed cost proxy across 3 uncertainty scenarios.",
            "evidence_ids": ["ev-dec-sample"],
        },
    )

    return registry
