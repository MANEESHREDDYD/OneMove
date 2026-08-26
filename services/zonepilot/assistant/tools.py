"""Deterministic execution engine for typed Assistant tools."""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any, Callable

from services.zonepilot.assistant.contracts import (
    AssistantToolCall,
    AssistantToolResult,
    ToolName,
)
from services.zonepilot.forecast.timeline import coerce_utc, utc_now

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


# Entity types the canonical Evidence Inspector can actually resolve
# (ObservatoryService.get_evidence). An evidence ID is only emitted when it
# resolves through that inspector; anything else is reported as an unverified
# reference so it can never be mistaken for an audit trail.
RESOLVABLE_EVIDENCE_TYPES = ("dataset", "network", "zone")


def evidence_id(entity_type: str, entity_id: str) -> str:
    """Build an Evidence Inspector reference of the canonical resolvable form.

    The value mirrors the inspector route /api/v1/evidence/{entity_type}/{entity_id},
    so it can be dereferenced verbatim.
    """
    if entity_type not in RESOLVABLE_EVIDENCE_TYPES:
        raise ValueError(f"{entity_type} is not resolvable by the Evidence Inspector")
    return f"{entity_type}/{entity_id}"


def _provenance(obj: Any, workspace_id: str, entity_type: str, entity_id: str) -> dict[str, Any]:
    """Extract real provenance from an authoritative response object.

    Every numeric the assistant emits carries the workspace it was read for, the
    upstream source record, its artifact version, and an evidence ID that
    resolves through the Evidence Inspector.
    """
    artifact_hash = getattr(obj, "artifact_hash", None)
    if not artifact_hash:
        raise AuthoritativeSourceUnavailable(f"{entity_type}/{entity_id} carries no artifact hash")

    source = getattr(obj, "source", None)
    if not source:
        raise AuthoritativeSourceUnavailable(f"{entity_type}/{entity_id} carries no source attribution")

    evidence_class = getattr(obj, "evidence_class", None)
    observed_at = getattr(obj, "observed_at", None)
    return {
        "workspace_id": workspace_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "source": str(source),
        "source_version": getattr(obj, "source_version", None),
        "evidence_class": getattr(evidence_class, "value", evidence_class),
        "artifact_sha256": str(artifact_hash),
        "observed_at": observed_at.isoformat() if hasattr(observed_at, "isoformat") else observed_at,
        "evidence_ids": [evidence_id(entity_type, entity_id)],
    }


def _decision_time(args: dict[str, Any]) -> datetime:
    """Resolve the decision time a point-in-time read must be bounded by.

    Callers may pin the context with ``as_of``/``decision_time``; otherwise the
    context is now. An unparseable value is an error, never a silent fallback to
    now, because that would quietly widen the window the caller asked to narrow.
    """
    for key in ("as_of", "decision_time"):
        raw = args.get(key)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        resolved = coerce_utc(raw.strip() if isinstance(raw, str) else raw)
        if resolved is None:
            raise ValueError(f"{key} must be an ISO-8601 timestamp")
        return resolved
    return utc_now()


def _measure(field_evidence: Any) -> dict[str, Any]:
    """Unwrap an authoritative FieldEvidence into value + unit. Never defaults."""
    value = getattr(field_evidence, "value", None)
    if value is None:
        raise AuthoritativeSourceUnavailable("Authoritative field carries no value")
    return {"value": value, "unit": getattr(field_evidence, "unit", None)}


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
            "road_length_km": _measure(static.road_length_km),
            "intersection_count": _measure(static.intersection_count),
            "commercial_poi_count": _measure(static.commercial_poi_count),
            "unavailable_layers": [layer.layer for layer in state.unavailable_dynamic_layers],
        }
        payload.update(_provenance(state, ws, "zone", state.zone_id))
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
        payload.update(_provenance(snap, ws, "network", snap.snapshot_id))
        return payload

    def _handle_get_forecast(args: dict[str, Any], ws: str) -> dict[str, Any]:
        zone_id = str(args.get("zone_id", "")).strip()
        if not zone_id:
            raise ValueError("zone_id is required")
        as_of = _decision_time(args)

        # Point-in-time read only. The unbounded read ordered by target_time DESC,
        # so limit=1 returned the furthest-FUTURE forecast: a record issued after
        # the decision time was selectable from a past context (F-020). A backing
        # repository that cannot answer "as of" is reported UNAVAILABLE rather
        # than fallen back to an unbounded read.
        point_in_time_read = getattr(forecast_repository, "get_zone_forecasts_as_of", None)
        if not callable(point_in_time_read):
            raise AuthoritativeSourceUnavailable(
                "Forecast repository does not support point-in-time reads; "
                "a forecast cannot be served without an issue-time bound"
            )
        rows = point_in_time_read(zone_id, ws, as_of, 1)
        if not rows:
            raise AuthoritativeSourceUnavailable(
                f"No forecast record issued on or before {as_of.isoformat()} exists "
                f"for zone {zone_id} in workspace {ws}"
            )
        row = rows[0]
        issued_at = row.get("forecast_issue_time", row.get("issued_at"))
        return {
            "zone_id": zone_id,
            "workspace_id": ws,
            "as_of": as_of.isoformat(),
            "target_metric": row.get("target_metric"),
            "predicted_value": row.get("predicted_value"),
            "model_id": row.get("model_id"),
            "model_version": row.get("model_version"),
            "horizon_minutes": row.get("horizon_minutes"),
            "issued_at": str(issued_at) if issued_at is not None else None,
            "source": "forecast_records",
            "record_id": str(row.get("forecast_id") or row.get("id") or ""),
            # The Evidence Inspector has no forecast branch, so there is no
            # resolvable evidence ID to offer. Saying so is the honest answer;
            # emitting an unresolvable identifier would fake an audit trail.
            "evidence_ids": [],
            "evidence_resolvable": False,
            "evidence_unavailable_reason": "Evidence Inspector exposes no forecast_record entity type.",
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
            "record_id": dec.decision_id,
            "evidence_ids": [],
            "evidence_resolvable": False,
            "evidence_unavailable_reason": "Evidence Inspector exposes no decision entity type.",
            "unverified_evidence_refs": list(dec.evidence_ids),
        }

    registry.register(ToolName.GET_ZONE_STATE, _handle_get_zone_state)
    registry.register(ToolName.GET_NETWORK_SNAPSHOT, _handle_get_network_snapshot)
    registry.register(ToolName.GET_FORECAST, _handle_get_forecast)
    registry.register(ToolName.EXPLAIN_DECISION, _handle_explain_decision)

    # Deliberately NOT registered until an authoritative source exists:
    # GET_SCENARIO, GET_EXPERIMENT, RUN_SCENARIO, RUN_OPTIMIZATION, GET_OPTIMIZATION,
    # COMPARE_DECISIONS, GET_RESILIENCE_RESULT, GET_DECISION, GET_OUTCOME, GET_EVIDENCE.
    return registry
