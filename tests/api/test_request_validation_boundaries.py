"""Request-model boundaries that were only enforced (or not enforced at all) below the API.

Every case here was found by driving the live app with hostile input. They share
one shape: an invariant that the domain, the driver or the database already
holds is missing from the request model, so a permanent client mistake is either
accepted and durably persisted, or reported as a retryable 5xx.

The contract these tests pin is the one the router already states for itself in
`_fail_if_dependency_unavailable`: a dependency outage is a retryable 503, and a
client mistake is a typed, non-retryable 4xx. Nothing in between.

None of these tests may reach the store. A request that is rejected correctly is
rejected before anything is written, which is the property `_never_persists`
asserts directly.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.core.auth import get_current_user
from services.api.main import app
from services.api.routers import observatory

ENVELOPE_FIELDS = {"code", "message", "retryable", "details", "request_id", "trace_id"}

WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "00000000-0000-0000-0000-000000000002"

VALID_H3_CELL = "88618925d3fffff"


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": USER_ID,
        "workspace_id": WORKSPACE_ID,
        "role": "operator",
    }
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def never_persists(monkeypatch: pytest.MonkeyPatch):
    """Fail loudly if a rejected request still reached a durable writer."""
    written: list[object] = []

    def _forbidden(*args, **kwargs):
        written.append((args, kwargs))
        raise AssertionError("a rejected request reached the store")

    monkeypatch.setattr(observatory._forecast_repo, "save_prediction", _forbidden)
    monkeypatch.setattr(observatory._opt_service, "submit_optimization", _forbidden)
    return written


def envelope_of(response) -> dict:
    body = response.json()
    assert "error" in body, f"response is not the canonical envelope: {body}"
    error = body["error"]
    assert set(error) >= ENVELOPE_FIELDS, f"missing envelope fields: {ENVELOPE_FIELDS - set(error)}"
    return error


# --- POST /api/v1/forecast/predict : zone_id ---------------------------------


@pytest.mark.parametrize(
    "zone_id",
    [
        "../../etc/passwd",
        "'; DROP TABLE forecast_records;--",
        "not-an-h3",
        "",
        "Z" * 10_240,
        "88618925d3ffffZ",
    ],
    ids=["traversal", "sql-shaped", "arbitrary", "empty", "oversized", "near-miss"],
)
def test_forecast_rejects_any_zone_id_that_is_not_an_h3_cell(
    client: TestClient, never_persists: list, zone_id: str
) -> None:
    """A forecast row keyed to a zone that cannot exist is unfalsifiable garbage.

    `zone_id` was a bare `str`, so the endpoint returned 201 and wrote the value
    into `forecast_records` verbatim -- including `../../etc/passwd`. The table
    is a measurement table; once such a row exists nothing distinguishes it from
    a real one, because nothing recorded that the zone was never validated.
    """
    response = client.post("/api/v1/forecast/predict", json={"zone_id": zone_id})

    assert response.status_code == 422, response.text
    error = envelope_of(response)
    assert error["code"] == "INVALID_ARGUMENT"
    assert error["retryable"] is False


def test_forecast_zone_id_rejection_matches_the_zone_state_route(client: TestClient, never_persists: list) -> None:
    """The read path and the write path must agree on what a zone id is.

    GET /zones/{zone_id}/state has always rejected a non-H3 id with this exact
    message. The forecast write path accepted what the read path refused.
    """
    response = client.post("/api/v1/forecast/predict", json={"zone_id": "not-an-h3"})

    assert envelope_of(response)["message"] == "Zone ID must be a valid H3 cell identifier"
