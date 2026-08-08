import pytest
import requests
import os
import uuid
import datetime

SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
LOCAL_SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

email1 = "test_user_c@onemove.com"
email2 = "test_user_d@onemove.com"
password = "testpassword123"
study_id = str(uuid.uuid4())
assignment_id_1 = str(uuid.uuid4())
assignment_id_2 = str(uuid.uuid4())

@pytest.fixture(scope="module")
def setup_users():
    # Attempt to sign up users (might fail if they exist, that's fine, we then sign in)
    auth_url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {"apikey": ANON_KEY, "Content-Type": "application/json"}
    
    requests.post(auth_url, headers=headers, json={"email": email1, "password": password})
    requests.post(auth_url, headers=headers, json={"email": email2, "password": password})
    
    # Sign in User 1
    res1 = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", headers=headers, json={"email": email1, "password": password})
    tok1 = res1.json().get("access_token")
    user_id1 = res1.json().get("user").get("id")
    
    # Sign in User 2
    res2 = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", headers=headers, json={"email": email2, "password": password})
    tok2 = res2.json().get("access_token")
    user_id2 = res2.json().get("user").get("id")
    
    return {
        "user1": {"token": tok1, "id": user_id1},
        "user2": {"token": tok2, "id": user_id2}
    }

def submit_probe(token, probe_data):
    url = "http://127.0.0.1:8000/v1/probes"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return requests.post(url, headers=headers, json=probe_data)

def test_own_probe_insert_allowed(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "eta_low_min": 5,
        "eta_high_min": 8,
        "option_count": 3,
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    res = submit_probe(setup_users["user1"]["token"], payload)
    assert res.status_code == 200, res.text

def test_exact_idempotent_replay(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "eta_low_min": 5,
        "eta_high_min": 8,
        "option_count": 3,
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    res1 = submit_probe(setup_users["user1"]["token"], payload)
    assert res1.status_code == 200
    
    # Exact duplicate retry
    res2 = submit_probe(setup_users["user1"]["token"], payload)
    assert res2.status_code == 200
    assert res2.json().get("idempotent_replay") is True

def test_conflicting_idempotency_reuse(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "eta_low_min": 5,
        "eta_high_min": 8,
        "option_count": 3,
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    res1 = submit_probe(setup_users["user1"]["token"], payload)
    assert res1.status_code == 200
    
    # Conflicting reuse (change ETA)
    payload["eta_low_min"] = 12
    payload["eta_high_min"] = 15
    res2 = submit_probe(setup_users["user1"]["token"], payload)
    assert res2.status_code == 409

def test_cross_user_probe_read_rejected(setup_users):
    # Setup some data
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    submit_probe(setup_users["user1"]["token"], payload)
    
    # User 2 tries to read it directly via Supabase API (RLS test)
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user2']['token']}"}
    res = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 0  # Empty array due to RLS

def test_own_probe_read_allowed(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    submit_probe(setup_users["user1"]["token"], payload)
    
    # User 1 tries to read it directly via Supabase API
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}"}
    res = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

def test_update_rejection(setup_users):
    client_event_id = str(uuid.uuid4())
    # User 1 inserts
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    submit_probe(setup_users["user1"]["token"], payload)
    
    # User 1 tries to UPDATE via Supabase API
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}", "Content-Type": "application/json", "Prefer": "return=representation"}
    res = requests.patch(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers, json={"eta_low_min": 50})
    # Since we didn't enable UPDATE in RLS, it should fail or return empty
    assert len(res.json()) == 0

def test_delete_rejection(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    submit_probe(setup_users["user1"]["token"], payload)
    
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}"}
    res = requests.delete(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers)
    
    # Should not be able to delete, verify it still exists
    res_get = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers)
    assert len(res_get.json()) == 1

def test_provenance_spoof_prevented(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    # Notice we don't even allow passing `provenance` in the ProbeObservationCreate pydantic schema.
    # If they pass it, pydantic ignores it or throws, and the server hardcodes "OBSERVED".
    payload["provenance"] = "SIMULATED"
    res = submit_probe(setup_users["user1"]["token"], payload)
    assert res.status_code == 200
    
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}"}
    res_get = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers).json()
    assert res_get[0]["provenance"] == "OBSERVED"

def test_server_timestamp_spoof_prevented(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    payload["received_at_server"] = "2000-01-01T00:00:00Z"
    submit_probe(setup_users["user1"]["token"], payload)
    
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}"}
    res_get = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers).json()
    # Pydantic ignores it, server overrides it.
    assert res_get[0]["received_at_server"][:4] != "2000"

def test_owner_qc_authorized(setup_users):
    # Service key represents backend ETL / QC operations in this architecture scope
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": study_id,
        "assignment_id": assignment_id_1,
        "client_event_id": client_event_id,
        "zone_cluster": "Z-01",
        "platform": "UBER",
        "intent": "GO_TO_CENTER",
        "protocol": "ANCHOR",
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK",
        "protocol_version": "1.0"
    }
    submit_probe(setup_users["user1"]["token"], payload)
    
    # QC role (Service Role) can read everything
    headers = {"apikey": LOCAL_SERVICE_KEY, "Authorization": f"Bearer {LOCAL_SERVICE_KEY}"}
    res_get = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers)
    assert res_get.status_code == 200
    assert len(res_get.json()) == 1
