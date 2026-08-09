from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_api_health():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_api_ready():
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "db_connected": True}

def test_governance_consent_endpoint():
    response = client.post("/governance/consent?participant_id=part-123&agreed=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CONSENT_RECORDED"
    assert data["participant_id"] == "part-123"
    assert data["agreed"] is True

def test_unauthenticated_probes_endpoint():
    # Attempting to submit probe without bearer token must return 401 or 403
    response = client.post("/v1/probes", json={"assignment_id": "assign-123", "client_event_id": "evt-123", "observed_at_device": "2026-08-08T12:00:00Z", "availability_state": "IN_STOCK"})
    assert response.status_code in [401, 403]

