import datetime
import os
import uuid

import pytest
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "mock_anon_key")
LOCAL_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "mock_service_key")
JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "REDACTED_SYNTHETIC_TEST_SECRET")

def _is_supabase_reachable():
    try:
        r = requests.head(f"{SUPABASE_URL}/rest/v1/", headers={"apikey": ANON_KEY}, timeout=2)
        return r.status_code < 500
    except Exception:
        return False

if not _is_supabase_reachable():
    pytestmark = pytest.mark.skip(reason="Live Supabase environment unreachable at SUPABASE_URL")

email1 = "test_user_e@onemove.com"
email2 = "test_user_f@onemove.com"
email3 = "test_user_g@onemove.com" # owner
password = "testpassword123"



@pytest.fixture(scope="module")
def setup_users():
    auth_url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {"apikey": ANON_KEY, "Content-Type": "application/json"}
    
    requests.post(auth_url, headers=headers, json={"email": email1, "password": password})
    requests.post(auth_url, headers=headers, json={"email": email2, "password": password})
    requests.post(auth_url, headers=headers, json={"email": email3, "password": password})
    
    res1 = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", headers=headers, json={"email": email1, "password": password})
    u1_id = res1.json().get("user", {}).get("id")
    u1_token = res1.json().get("access_token")
    user1 = {"token": u1_token, "id": u1_id}
    
    res2 = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", headers=headers, json={"email": email2, "password": password})
    u2_id = res2.json().get("user", {}).get("id")
    u2_token = res2.json().get("access_token")
    user2 = {"token": u2_token, "id": u2_id}
    
    res3 = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", headers=headers, json={"email": email3, "password": password})
    u3_id = res3.json().get("user", {}).get("id")
    u3_token = res3.json().get("access_token")
    user3 = {"token": u3_token, "id": u3_id}
    
    # Use service key to provision studies and assignments
    service_headers = {"apikey": LOCAL_SERVICE_KEY, "Authorization": f"Bearer {LOCAL_SERVICE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    
    # 1. Create study
    study_res = requests.post(f"{SUPABASE_URL}/rest/v1/studies", headers=service_headers, json={
        "city": "Bengaluru",
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "protocol_version": "1.0",
        "study_phase": "DRY_RUN",
        "status": "planned"
    })
    assert study_res.status_code in (200, 201), f"Failed to create study: {study_res.text}"
    study_id = study_res.json()[0]["id"]
    
    # 2. Add participants (auth triggers might have done this, but we do it manually to be safe if no trigger)
    # The new schema requires participants.id to match auth.uid(), which happens via trigger or insert.
    requests.post(f"{SUPABASE_URL}/rest/v1/participants", headers=service_headers, json={"id": user1["id"], "external_id": "ext1", "hash_key_version": "1"})
    requests.post(f"{SUPABASE_URL}/rest/v1/participants", headers=service_headers, json={"id": user2["id"], "external_id": "ext2", "hash_key_version": "1"})
    requests.post(f"{SUPABASE_URL}/rest/v1/participants", headers=service_headers, json={"id": user3["id"], "external_id": "ext3", "hash_key_version": "1"})
    
    # 3. Create assignments
    a1_res = requests.post(f"{SUPABASE_URL}/rest/v1/assignments", headers=service_headers, json={
        "study_id": study_id,
        "participant_id": user1["id"],
        "zone_cluster": "BGLR-1",
        "platform": "APP",
        "intent": "TEST",
        "protocol": "ANCHOR"
    })
    assert a1_res.status_code in (200, 201), f"Failed to create assignment 1: {a1_res.text}"
    assign1 = a1_res.json()[0]["id"]
    
    a2_res = requests.post(f"{SUPABASE_URL}/rest/v1/assignments", headers=service_headers, json={
        "study_id": study_id,
        "participant_id": user2["id"],
        "zone_cluster": "Indiranagar",
        "platform": "ZEPTO",
        "intent": "QC",
        "protocol": "ANCHOR",
        "status": "ACTIVE"
    })
    assign2 = a2_res.json()[0]["id"]
    
    # 4. Assign OWNER role to user3
    requests.post(f"{SUPABASE_URL}/rest/v1/participant_roles", headers=service_headers, json={
        "participant_id": user3["id"],
        "study_id": study_id,
        "role": "OWNER"
    })
    
    return {
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "study_id": study_id,
        "assign1": assign1,
        "assign2": assign2
    }

def submit_probe(token, probe_data):
    url = "http://127.0.0.1:8000/v1/probes"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return requests.post(url, headers=headers, json=probe_data)

def test_own_probe_insert_allowed(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK",
        "eta_low_min": 10,
        "eta_high_min": 15
    }
    res = submit_probe(setup_users["user1"]["token"], payload)
    assert res.status_code == 200, res.text
    
def test_exact_idempotent_replay(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    res1 = submit_probe(setup_users["user1"]["token"], payload)
    assert res1.status_code == 200
    
    # Exact duplicate retry
    res2 = submit_probe(setup_users["user1"]["token"], payload)
    assert res2.status_code == 200, res2.text
    assert res2.json().get("idempotent_replay") is True

def test_conflicting_idempotency_reuse(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    res1 = submit_probe(setup_users["user1"]["token"], payload)
    assert res1.status_code == 200
    
    # Conflicting reuse
    payload["availability_state"] = "OUT_OF_STOCK"
    res2 = submit_probe(setup_users["user1"]["token"], payload)
    assert res2.status_code == 409

def test_cross_user_probe_read_rejected(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    submit_probe(setup_users["user1"]["token"], payload)
    
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user2']['token']}"}
    res = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 0

def test_update_rejection(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    submit_probe(setup_users["user1"]["token"], payload)
    
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}", "Content-Type": "application/json", "Prefer": "return=representation"}
    res = requests.patch(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers, json={"eta_low_min": 50})
    # Update not allowed in RLS
    assert len(res.json()) == 0

def test_delete_rejection(setup_users):
    client_event_id = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    submit_probe(setup_users["user1"]["token"], payload)
    
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}"}
    res_del = requests.delete(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers)
    assert res_del.status_code in [200, 204, 401, 403]
    
    res_get = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?client_event_id=eq.{client_event_id}", headers=headers)
    assert len(res_get.json()) == 1

def test_wrong_assignment_rejected(setup_users):
    # User 1 tries to submit probe for User 2's assignment
    client_event_id = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign2"],
        "client_event_id": client_event_id,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    res = submit_probe(setup_users["user1"]["token"], payload)
    # The API will reject because assignment owner check fails
    assert res.status_code in [403, 404]
    
def test_browser_submitted_study_id_rejected_by_pydantic_fail_closed(setup_users):
    service_headers = {"apikey": LOCAL_SERVICE_KEY, "Authorization": f"Bearer {LOCAL_SERVICE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    study_res = requests.post(f"{SUPABASE_URL}/rest/v1/studies", headers=service_headers, json={
        "city": "Bengaluru",
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "protocol_version": "1.0"
    })
    study_id2 = study_res.json()[0]["id"]
    a_res = requests.post(f"{SUPABASE_URL}/rest/v1/assignments", headers=service_headers, json={
        "study_id": study_id2,
        "participant_id": setup_users["user1"]["id"],
        "zone_cluster": "Indiranagar",
        "platform": "SWIGGY",
        "intent": "FOOD",
        "protocol": "ANCHOR"
    })
    assign_diff = a_res.json()[0]["id"]
    
    # Client sends study_id to endpoint -> fail-closed extra field rejection
    client_event_id = str(uuid.uuid4())
    payload = {
        "study_id": setup_users["study_id"],
        "assignment_id": assign_diff,
        "client_event_id": client_event_id,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    res = submit_probe(setup_users["user1"]["token"], payload)
    assert res.status_code == 422

def test_cross_study_assignment_submission_boundary(setup_users):
    # Attempting to use an assignment from an inactive/closed study
    service_headers = {"apikey": LOCAL_SERVICE_KEY, "Authorization": f"Bearer {LOCAL_SERVICE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    study_res = requests.post(f"{SUPABASE_URL}/rest/v1/studies", headers=service_headers, json={
        "city": "Bengaluru",
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "protocol_version": "1.0",
        "status": "COMPLETED"
    })
    closed_study_id = study_res.json()[0]["id"]
    
    inactive_assign = requests.post(f"{SUPABASE_URL}/rest/v1/assignments", headers=service_headers, json={
        "study_id": closed_study_id,
        "participant_id": setup_users["user1"]["id"],
        "zone_cluster": "Koramangala",
        "platform": "ZEPTO",
        "intent": "QC",
        "protocol": "ANCHOR",
        "status": "INACTIVE"
    }).json()[0]["id"]
    
    payload = {
        "assignment_id": inactive_assign,
        "client_event_id": str(uuid.uuid4()),
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    res = submit_probe(setup_users["user1"]["token"], payload)
    assert res.status_code == 403
    assert "Assignment is not ACTIVE" in res.text

def test_metadata_owner_escalation_rejected(setup_users):
    # User 1 (ordinary participant) attempts to read all study observations via PostgREST
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}"}
    res = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?study_id=eq.{setup_users['study_id']}", headers=headers)
    assert res.status_code == 200
    # User 1 cannot see User 2's or User 3's probes
    for r in res.json():
        assert r["participant_id"] == setup_users["user1"]["id"]

def test_real_owner_qc_authorized(setup_users):
    # User 3 is OWNER for the study. Should be able to read User 1's probes
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user3']['token']}"}
    res = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?study_id=eq.{setup_users['study_id']}", headers=headers)
    assert res.status_code == 200
    # Ensure they see user1's data
    has_user1_probe = any(r["participant_id"] == setup_users["user1"]["id"] for r in res.json())
    assert has_user1_probe is True

def test_metadata_admin_escalation_rejected(setup_users):
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}", "Content-Type": "application/json"}
    res = requests.patch(f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{setup_users['user1']['id']}", headers=headers, json={"role": "admin"})
    assert res.status_code in [401, 403, 404, 400, 405]

def test_correction_creates_new_row_and_preserves_original(setup_users):
    client_event_id_1 = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id_1,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    res1 = submit_probe(setup_users["user1"]["token"], payload)
    assert res1.status_code == 200
    db_id = res1.json()[0]["id"]
    
    # Correction
    client_event_id_2 = str(uuid.uuid4())
    payload2 = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id_2,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "OUT_OF_STOCK",
        "supersedes_id": db_id,
        "correction_reason": "USER_FIX"
    }
    res2 = submit_probe(setup_users["user1"]["token"], payload2)
    assert res2.status_code == 200
    
    # Original still exists
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}"}
    res_orig = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations?id=eq.{db_id}", headers=headers)
    assert len(res_orig.json()) == 1

def test_current_state_resolution_selects_correction(setup_users):
    client_event_id_1 = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id_1,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    res1 = submit_probe(setup_users["user1"]["token"], payload)
    db_id_1 = res1.json()[0]["id"]
    
    client_event_id_2 = str(uuid.uuid4())
    payload2 = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": client_event_id_2,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "OUT_OF_STOCK",
        "supersedes_id": db_id_1,
        "correction_reason": "USER_FIX"
    }
    res2 = submit_probe(setup_users["user1"]["token"], payload2)
    db_id_2 = res2.json()[0]["id"]
    
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {setup_users['user1']['token']}"}
    # Query current state view for the assignment
    res_view = requests.get(f"{SUPABASE_URL}/rest/v1/probe_observations_current?assignment_id=eq.{setup_users['assign1']}", headers=headers)
    assert res_view.status_code == 200
    
    ids_in_view = [r["id"] for r in res_view.json()]
    assert db_id_2 in ids_in_view
    assert db_id_1 not in ids_in_view # Superseded row is omitted

def test_cross_participant_correction_rejected(setup_users):
    # User 2 creates a probe
    client_event_id_1 = str(uuid.uuid4())
    payload = {
        "assignment_id": setup_users["assign2"],
        "client_event_id": client_event_id_1,
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK"
    }
    res1 = submit_probe(setup_users["user2"]["token"], payload)
    db_id = res1.json()[0]["id"]
    
    # User 1 tries to correct User 2's probe
    payload2 = {
        "assignment_id": setup_users["assign1"],
        "client_event_id": str(uuid.uuid4()),
        "observed_at_device": datetime.datetime.utcnow().isoformat() + "Z",
        "availability_state": "IN_STOCK",
        "supersedes_id": db_id,
        "correction_reason": "USER_FIX"
    }
    res2 = submit_probe(setup_users["user1"]["token"], payload2)
    assert res2.status_code == 403
    assert "Original probe belongs to a different participant" in res2.text
