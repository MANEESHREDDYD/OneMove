"""Deterministic execution engine for typed Assistant tools."""

from __future__ import annotations

import re
import time
from typing import Any, Callable

from services.zonepilot.assistant.contracts import (
    AssistantToolCall,
    AssistantToolResult,
    ToolName,
)

# Prompt injection pattern protection
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|all)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"<\s*script[^>]*>[\s\S]*?<\s*/\s*script\s*>", re.IGNORECASE),
    re.compile(r"<\s*/?\s*script\b[^>]*>", re.IGNORECASE),
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
            # No authoritative source is wired for this tool. Report UNAVAILABLE
            # rather than synthesising a plausible answer (P0-ASSISTANT-TRUTH-001).
            return AssistantToolResult(
                tool_name=call.tool_name,
                result_data={"status": "UNAVAILABLE"},
                execution_time_ms=0,
                success=False,
                error_message=(f"UNAVAILABLE: no authoritative source is registered for tool {call.tool_name.value}"),
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
        except AuthoritativeSourceUnavailable as unavailable:
            elapsed = int((time.perf_counter() - start) * 1000)
            return AssistantToolResult(
                tool_name=call.tool_name,
                result_data={"status": "UNAVAILABLE"},
                execution_time_ms=elapsed,
                success=False,
                error_message=f"UNAVAILABLE: {unavailable}",
            )
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            return AssistantToolResult(
                tool_name=call.tool_name,
                result_data={"status": "UNAVAILABLE"},
                execution_time_ms=elapsed,
                success=False,
                error_message=str(e),
            )


class AuthoritativeSourceUnavailable(RuntimeError):
    """No authoritative record backs the requested value.

    Raised instead of substituting a placeholder. Surfaces to the caller as an
    explicit UNAVAILABLE result (P0-ASSISTANT-TRUTH-001).
    """


def _provenance(obj: Any, workspace_id: str, entity_ref: str) -> dict[str, Any]:
    """Extract real provenance from an authoritative response object.

    Every numeric the assistant emits must carry the workspace it was read for,
    the upstream source record, its dataset/artifact version, and an evidence ID
    that resolves through the evidence inspector.
    """
    artifact_hash = getattr(obj, "artifact_hash", None)
    if not artifact_hash:
        raise AuthoritativeSourceUnavailable(f"{entity_ref} carries no artifact hash; provenance cannot be established")

    source = getattr(obj, "source", None)
    if not source:
        raise AuthoritativeSourceUnavailable(f"{entity_ref} carries no source attribution")

    observed_at = getattr(obj, "observed_at", None)
    return {
        "workspace_id": workspace_id,
        "source": str(source),
        "source_version": getattr(obj, "source_version", None),
        "artifact_sha256": str(artifact_hash),
        "observed_at": observed_at.isoformat() if hasattr(observed_at, "isoformat") else observed_at,
        "evidence_ids": [f"artifact_sha256:{artifact_hash}", entity_ref],
    }


def _field(field_evidence: Any) -> Any:
    """Unwrap an authoritative FieldEvidence value; never defaults."""
    value = getattr(field_evidence, "value", None)
    if value is None:
        raise AuthoritativeSourceUnavailable("Authoritative field carries no value")
    return value


def build_assistant_registry(
    *,
    observatory_service: Any,
    decision_ledger: Any,
    forecast_repository: Any,
) -> AssistantToolRegistry:
    """Build the production Assistant registry backed by authoritative sources only.

    Handlers read from the same repositories/services that serve the REST API. A
    tool with no authoritative backing is deliberately not registered, so it
    reports UNAVAILABLE rather than returning a plausible-looking number.
    """
    registry = AssistantToolRegistry()

    def _handle_get_zone_state(args: dict[str, Any], ws: str) -> dict[str, Any]:
        zone_id = str(args.get("zone_id", "")).strip()
        if not zone_id:
            raise ValueError("zone_id is required")
        try:
            state = observatory_service.get_zone_state(zone_id).data
        except Exception as exc:
            raise AuthoritativeSourceUnavailable(f"Zone {zone_id} is not present in the gold network: {exc}") from exc

        static = state.static
        payload = {
            "zone_id": state.zone_id,
            "resolution": state.resolution,
            "road_length_km": _field(static.road_length_km),
            "intersection_count": _field(static.intersection_count),
            "commercial_poi_count": _field(static.commercial_poi_count),
            "unavailable_layers": [layer.layer for layer in state.unavailable_dynamic_layers],
        }
        payload.update(_provenance(state, ws, f"zone:{state.zone_id}"))
        return payload

    def _handle_get_network_snapshot(args: dict[str, Any], ws: str) -> dict[str, Any]:
        snapshots = observatory_service.list_network_snapshots().data
        if not snapshots:
            raise AuthoritativeSourceUnavailable("No network snapshot artifact is currently mounted")
        snap = snapshots[0]
        payload = {
            "snapshot_id": snap.snapshot_id,
            "graph_version": snap.graph_version,
            "h3_resolution": snap.h3_resolution,
            "graph_vertices": snap.metrics.graph_vertices,
            "graph_directed_edges": snap.metrics.graph_directed_edges,
            "intersections": snap.metrics.intersections,
            "connected_components": snap.metrics.connected_components,
        }
        payload.update(_provenance(snap, ws, f"network_snapshot:{snap.snapshot_id}"))
        return payload

    def _handle_get_forecast(args: dict[str, Any], ws: str) -> dict[str, Any]:
        zone_id = str(args.get("zone_id", "")).strip()
        if not zone_id:
            raise ValueError("zone_id is required")
        rows = forecast_repository.get_zone_forecasts(zone_id, ws, limit=1)
        if not rows:
            raise AuthoritativeSourceUnavailable(
                f"No persisted forecast record exists for zone {zone_id} in workspace {ws}"
            )
        row = rows[0]
        return {
            "zone_id": zone_id,
            "workspace_id": ws,
            "target_metric": row.get("target_metric"),
            "predicted_value": row.get("predicted_value"),
            "model_id": row.get("model_id"),
            "model_version": row.get("model_version"),
            "horizon_minutes": row.get("horizon_minutes"),
            "issued_at": str(row.get("issued_at")) if row.get("issued_at") is not None else None,
            "source": "forecast_records",
            "evidence_ids": [f"forecast_record:{row.get('forecast_id') or row.get('id')}"],
        }

    def _handle_explain_decision(args: dict[str, Any], ws: str) -> dict[str, Any]:
        decision_id = str(args.get("decision_id", "")).strip()
        if not decision_id:
            raise ValueError("decision_id is required")
        # Workspace-scoped: a decision outside the caller's workspace is simply absent.
        dec = decision_ledger.get_decision(decision_id, ws)
        if dec is None:
            raise AuthoritativeSourceUnavailable(f"Decision {decision_id} is not present in workspace {ws}")
        return {
            "decision_id": dec.decision_id,
            "workspace_id": dec.workspace_id,
            "action": dec.selected_action,
            "opened_facilities": list(dec.opened_facilities),
            "objective_value": dec.objective_value,
            "expected_travel_seconds": dec.expected_travel_seconds,
            "p95_travel_seconds": dec.p95_travel_seconds,
            "coverage_basis_points": dec.coverage_basis_points,
            "decision_time": dec.decision_time.isoformat(),
            "dataset_version": dec.dataset_version,
            "graph_version": dec.graph_version,
            "solver_version": dec.solver_version,
            "problem_snapshot_sha256": dec.feature_snapshot_hash,
            "osrm_bundle_hash": dec.osrm_bundle_hash,
            "source": "decision_records",
            "evidence_ids": list(dec.evidence_ids),
        }

    registry.register(ToolName.GET_ZONE_STATE, _handle_get_zone_state)
    registry.register(ToolName.GET_NETWORK_SNAPSHOT, _handle_get_network_snapshot)
    registry.register(ToolName.GET_FORECAST, _handle_get_forecast)
    registry.register(ToolName.EXPLAIN_DECISION, _handle_explain_decision)

    # Deliberately NOT registered until an authoritative source exists:
    # GET_SCENARIO, GET_EXPERIMENT, RUN_SCENARIO, RUN_OPTIMIZATION, GET_OPTIMIZATION,
    # COMPARE_DECISIONS, GET_RESILIENCE_RESULT, GET_DECISION, GET_OUTCOME, GET_EVIDENCE.
    return registry
