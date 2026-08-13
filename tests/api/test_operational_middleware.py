import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from services.api.core.middleware import RequestIdMiddleware
from services.api.core.telemetry import InMemoryRateLimiter, JsonFormatter, safe_request_id
from services.api.main import app


def test_cors_preflight_for_observatory() -> None:
    response = TestClient(app).options(
        "/api/v1/zones",
        headers={
            "origin": "http://localhost:3001",
            "access-control-request-method": "GET",
            "access-control-request-headers": "authorization,x-workspace-id",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3001"


def test_invalid_request_id_is_replaced() -> None:
    test_app = FastAPI()
    test_app.add_middleware(RequestIdMiddleware)

    @test_app.get("/")
    def root() -> dict[str, bool]:
        return {"ok": True}

    response = TestClient(test_app).get("/", headers={"x-request-id": "contains spaces"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "contains spaces"
    assert safe_request_id("valid-id:1", lambda: "fallback") == "valid-id:1"


def test_rate_limiter_releases_next_window() -> None:
    now = [100.0]
    limiter = InMemoryRateLimiter(clock=lambda: now[0])

    assert limiter.check("auth", "principal", 1) == (True, 0)
    allowed, retry_after = limiter.check("auth", "principal", 1)
    assert allowed is False
    assert retry_after > 0

    now[0] += 61
    assert limiter.check("auth", "principal", 1) == (True, 0)


def test_json_logging_redacts_sensitive_fields() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "completed", (), None)
    record.request_id = "request-1"
    record.token = "secret-value"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "request-1"
    assert payload["token"] == "[REDACTED]"
    assert "secret-value" not in json.dumps(payload)


def test_metrics_are_disabled_without_explicit_activation(monkeypatch) -> None:
    monkeypatch.delenv("ZONEPILOT_METRICS_ENABLED", raising=False)
    response = TestClient(app).get("/metrics")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_404"


def test_validation_error_does_not_echo_sensitive_input() -> None:
    class SecretPayload(BaseModel):
        password: str = Field(min_length=12)

    @app.post("/_test/secret-validation", include_in_schema=False)
    def validate_secret(payload: SecretPayload) -> dict[str, bool]:
        return {"ok": bool(payload.password)}

    response = TestClient(app).post("/_test/secret-validation", json={"password": "hunter"})
    serialized = json.dumps(response.json())

    assert response.status_code == 422
    assert "hunter" not in serialized
    assert "input" not in serialized
