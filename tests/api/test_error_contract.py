"""F-025 -- the canonical API error contract.

Every production route must fail with one envelope:

    {"error": {"code", "message", "retryable", "details", "request_id", "trace_id"}}

and the status must carry the right meaning. The finding that produced this file
was that database unavailability surfaced as 422 VALIDATION_FAILED, as an
unhandled 500, and occasionally as 503 -- so a client could not tell a retryable
dependency outage from a permanent mistake of its own.

Nothing here touches a database: dependency failures are injected.
"""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from services.api.core.auth import get_current_user
from services.api.main import app
from services.api.routers import observatory
from services.common.db_dsn import DatabaseConfigurationError

ENVELOPE_FIELDS = {"code", "message", "retryable", "details", "request_id", "trace_id"}

# Routes that exist only to drive the app-level exception handlers. They are
# registered on the real app because the handlers under test are registered
# there too.


@app.get("/_test/error-contract/db-config", include_in_schema=False)
def _raise_database_configuration_error() -> dict:
    raise DatabaseConfigurationError("DATABASE_URL is required (ENVIRONMENT=unset) and is not set.")


@app.get("/_test/error-contract/db-operational", include_in_schema=False)
def _raise_psycopg_operational_error() -> dict:
    raise psycopg.OperationalError("connection to server at 'db' (10.0.0.1), port 5432 failed")


@app.get("/_test/error-contract/boom", include_in_schema=False)
def _raise_unexpected_error() -> dict:
    raise RuntimeError("an internal invariant broke")


class _StrictBody(BaseModel):
    order_id: str
    quantity: int


@app.post("/_test/error-contract/validated", include_in_schema=False)
def _validated_route(body: _StrictBody) -> dict:
    return {"order_id": body.order_id}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def authenticated_client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "user-error-contract",
        "workspace_id": "ws-error-contract",
    }
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def envelope_of(response) -> dict:
    body = response.json()
    assert "error" in body, f"response is not the canonical envelope: {body}"
    error = body["error"]
    assert set(error) >= ENVELOPE_FIELDS, f"missing envelope fields: {ENVELOPE_FIELDS - set(error)}"
    assert isinstance(error["code"], str) and error["code"]
    assert isinstance(error["message"], str)
    assert isinstance(error["retryable"], bool)
    assert isinstance(error["details"], dict)
    assert isinstance(error["request_id"], str) and error["request_id"] != "unknown"
    assert isinstance(error["trace_id"], str) and error["trace_id"] != "unknown"
    return error


# --- The envelope itself ------------------------------------------------------


def test_unauthenticated_request_returns_canonical_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/zones")

    assert response.status_code == 401
    error = envelope_of(response)
    assert error["code"] == "UNAUTHORIZED"
    assert error["retryable"] is False


def test_unknown_route_uses_the_canonical_not_found_code(client: TestClient) -> None:
    response = client.get("/api/v1/definitely-not-a-route")

    assert response.status_code == 404
    error = envelope_of(response)
    assert error["code"] == "NOT_FOUND"
    assert error["retryable"] is False


def test_bad_client_schema_is_the_only_thing_that_yields_422(client: TestClient) -> None:
    response = client.post("/_test/error-contract/validated", json={"order_id": 5})

    assert response.status_code == 422
    error = envelope_of(response)
    assert error["code"] == "VALIDATION_FAILED"
    assert error["retryable"] is False


def test_request_id_and_trace_id_come_from_the_request_not_a_parallel_mechanism(client: TestClient) -> None:
    """The ids in the envelope must be the ones the middleware assigned."""
    response = client.get("/api/v1/zones")
    error = envelope_of(response)

    assert error["request_id"] == response.headers["x-request-id"]
    assert error["trace_id"] == response.headers["x-trace-id"]


def test_inbound_traceparent_is_honoured(client: TestClient) -> None:
    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    response = client.get("/api/v1/zones", headers={"traceparent": traceparent})

    assert envelope_of(response)["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"


def test_supplied_request_id_is_echoed_into_the_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/zones", headers={"x-request-id": "req-abc-123"})

    assert envelope_of(response)["request_id"] == "req-abc-123"


def test_malicious_trace_headers_are_not_echoed(client: TestClient) -> None:
    response = client.get(
        "/api/v1/zones",
        headers={"traceparent": "<script>alert(1)</script>", "x-cloud-trace-context": "not a trace"},
    )

    error = envelope_of(response)
    assert "<script>" not in error["trace_id"]


# --- Dependency unavailability is 503, centrally -------------------------------


def test_database_configuration_error_is_503_not_422_or_500(client: TestClient) -> None:
    """The core regression: an unconfigured database is a retryable dependency outage."""
    response = client.get("/_test/error-contract/db-config")

    assert response.status_code == 503, "an unavailable database must not be reported as 422 or 500"
    error = envelope_of(response)
    assert error["code"] == "DEPENDENCY_UNAVAILABLE"
    assert error["retryable"] is True
    assert error["details"]["dependency"] == "database"


def test_psycopg_operational_error_is_503(client: TestClient) -> None:
    response = client.get("/_test/error-contract/db-operational")

    assert response.status_code == 503
    error = envelope_of(response)
    assert error["code"] == "DEPENDENCY_UNAVAILABLE"
    assert error["retryable"] is True


def test_dependency_failure_does_not_leak_driver_detail(client: TestClient) -> None:
    """Driver messages can carry host, port and user. They are logged, not returned."""
    response = client.get("/_test/error-contract/db-operational")

    assert "10.0.0.1" not in response.text
    assert "5432" not in response.text


def test_unexpected_error_is_a_generic_internal_error(client: TestClient) -> None:
    response = client.get("/_test/error-contract/boom")

    assert response.status_code == 500
    error = envelope_of(response)
    assert error["code"] == "INTERNAL_ERROR"
    assert "invariant" not in error["message"], "internal failure detail must not reach the client"


def test_route_level_handler_cannot_downgrade_a_db_outage_to_422(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broad `except Exception` in a router must not relabel an outage as a client error.

    POST /api/v1/scenarios wraps scenario execution in `except Exception ->
    EXECUTION_ERROR 422`. That is exactly how a database outage was being
    reported as a permanent client mistake.
    """

    def _unavailable(**_kwargs):
        raise DatabaseConfigurationError("DATABASE_URL is required (ENVIRONMENT=unset) and is not set.")

    monkeypatch.setattr(observatory._res_service, "execute_scenario", _unavailable)

    response = authenticated_client.post(
        "/api/v1/scenarios",
        json={
            "scenario_type": "CONGESTION_SPIKE",
            "description": "error contract probe",
            "parameters": {"congestion_multiplier": 1.5},
            "seed": 42,
        },
    )

    assert response.status_code == 503
    error = envelope_of(response)
    assert error["code"] == "DEPENDENCY_UNAVAILABLE"
    assert error["retryable"] is True


def test_assistant_does_not_serve_a_dependency_outage_as_a_200_answer(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An internal failure must not be dressed up as a successful business answer."""

    class _UnavailableRegistry:
        def execute(self, call):
            from services.zonepilot.assistant.contracts import AssistantToolResult

            return AssistantToolResult(
                tool_name=call.tool_name,
                result_data={"status": "UNAVAILABLE"},
                execution_time_ms=0,
                success=False,
                error_message="DATABASE_URL is required (ENVIRONMENT=unset) and is not set.",
            )

    monkeypatch.setattr(observatory, "build_assistant_registry", lambda **_kwargs: _UnavailableRegistry())

    response = authenticated_client.post(
        "/api/v1/assistant/query",
        json={"query": "forecast?", "tool_name": "get_forecast", "arguments": {"zone_id": "8860145b41fffff"}},
    )

    assert response.status_code == 503, "a database outage must not be returned as a 200 business answer"
    error = envelope_of(response)
    assert error["code"] == "DEPENDENCY_UNAVAILABLE"
    assert error["retryable"] is True


def test_assistant_domain_miss_stays_a_typed_200_response(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A truthful "no authoritative record" answer is a domain result, not an outage."""

    class _DomainMissRegistry:
        def execute(self, call):
            from services.zonepilot.assistant.contracts import AssistantToolResult

            return AssistantToolResult(
                tool_name=call.tool_name,
                result_data={"status": "UNAVAILABLE"},
                execution_time_ms=1,
                success=False,
                error_message="UNAVAILABLE: Zone 8860145b41fffff is not present in the gold network",
            )

    monkeypatch.setattr(observatory, "build_assistant_registry", lambda **_kwargs: _DomainMissRegistry())

    response = authenticated_client.post(
        "/api/v1/assistant/query",
        json={"query": "zone?", "tool_name": "get_zone_state", "arguments": {"zone_id": "8860145b41fffff"}},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False


# --- Readiness probe -----------------------------------------------------------


def test_readyz_returns_a_typed_503_when_the_dsn_is_unconfigured(client: TestClient) -> None:
    """Residual on F-025: this raised DatabaseConfigurationError uncaught and 500'd."""
    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"status": "unready", "db_connected": False}


def test_liveness_is_unaffected_by_database_state(client: TestClient) -> None:
    """F-024: liveness must never depend on a dependency being reachable."""
    for path in ("/health", "/healthz", "/health/live"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
