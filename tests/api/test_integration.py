import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_api_health():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/governance/consent?participant_id=part-123&agreed=true"),
        ("post", "/governance/withdraw?participant_id=part-123"),
        ("post", "/governance/activate?participant_id=part-123"),
        ("get", "/governance/retention"),
    ],
)
def test_governance_stub_routes_are_not_served(method: str, path: str):
    """The governance router was removed.

    Those four routes had no auth dependency and no storage: they returned
    hardcoded success strings for consent, withdrawal, activation and retention
    audit. An unauthenticated endpoint that says "CONSENT_RECORDED" without
    recording consent is worse than a 404, so the router is gone and must stay
    gone.
    """
    response = getattr(client, method)(path)
    assert response.status_code == 404


def test_no_governance_routes_are_registered():
    assert [route for route in app.routes if getattr(route, "path", "").startswith("/governance")] == []

def test_unauthenticated_probes_endpoint():
    # Attempting to submit probe without bearer token must return 401 or 403
    response = client.post("/v1/probes", json={"assignment_id": "assign-123", "client_event_id": "evt-123", "observed_at_device": "2026-08-08T12:00:00Z", "availability_state": "IN_STOCK"})
    assert response.status_code in [401, 403]

