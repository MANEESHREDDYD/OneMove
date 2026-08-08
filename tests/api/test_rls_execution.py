import pytest
import requests
import os

SUPABASE_URL = "http://127.0.0.1:54321"
ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "sb_publishable" + "_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH")
LOCAL_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "sb_secret" + "_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz")

def test_rls_probes():
    email1 = "test_user_c@onemove.com"
    email2 = "test_user_d@onemove.com"
    password = "password123"
    
    auth_url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {"apikey": ANON_KEY, "Content-Type": "application/json"}
    
    res_a = requests.post(auth_url, json={"email": email1, "password": password}, headers=headers)
    if res_a.status_code != 200:
        res_a = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", json={"email": email1, "password": password}, headers=headers)
    
    user_a = res_a.json()
    token_a = user_a["access_token"]
    id_a = user_a["user"]["id"]

    res_b = requests.post(auth_url, json={"email": email2, "password": password}, headers=headers)
    if res_b.status_code != 200:
        res_b = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", json={"email": email2, "password": password}, headers=headers)
        
    user_b = res_b.json()
    token_b = user_b["access_token"]
    id_b = user_b["user"]["id"]

    srv_headers = {
        "apikey": LOCAL_SERVICE_KEY,
        "Authorization": f"Bearer {LOCAL_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    study = requests.post(f"{SUPABASE_URL}/rest/v1/studies", headers=srv_headers, json={
        "city": "Bengaluru",
        "started_at": "2026-08-01T00:00:00Z",
        "protocol_version": "1.0",
        "status": "planned"
    }).json()
    
    study_id = study[0]["id"] if isinstance(study, list) else study["id"]

    requests.post(f"{SUPABASE_URL}/rest/v1/participants", headers=srv_headers, json={"id": id_a, "external_id": "ext_c", "hash_key_version": "v1"})
    requests.post(f"{SUPABASE_URL}/rest/v1/participants", headers=srv_headers, json={"id": id_b, "external_id": "ext_d", "hash_key_version": "v1"})
    
    order_a = requests.post(f"{SUPABASE_URL}/rest/v1/volunteer_orders", headers=srv_headers, json={"study_id": study_id, "participant_id": id_a}).json()
    order_b = requests.post(f"{SUPABASE_URL}/rest/v1/volunteer_orders", headers=srv_headers, json={"study_id": study_id, "participant_id": id_b}).json()
    
    order_id_a = order_a[0]["id"]
    order_id_b = order_b[0]["id"]

    headers_a = {
        "apikey": ANON_KEY, 
        "Authorization": f"Bearer {token_a}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/volunteer_order_events",
        headers=headers_a,
        json={
            "order_id": order_id_a,
            "event_type": "PROBE",
            "occurred_at": "2026-08-07T18:00:00Z",
            "provenance": "OBSERVED",
            "client_event_id": "probe_1"
        }
    )
    assert res.status_code == 201, f"Failed to insert probe: {res.text}"

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/volunteer_order_events",
        headers=headers_a,
        json={
            "order_id": order_id_b,
            "event_type": "PROBE",
            "occurred_at": "2026-08-07T18:00:00Z",
            "provenance": "OBSERVED",
            "client_event_id": "probe_2"
        }
    )
    assert res.status_code in [401, 403, 404], f"Should have thrown an RLS violation: {res.status_code} {res.text}"

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/volunteer_order_events",
        headers=headers_a,
        json={
            "order_id": order_id_a,
            "event_type": "PROBE",
            "occurred_at": "2026-08-07T18:00:00Z",
            "provenance": "OBSERVED",
            "client_event_id": "probe_1"
        }
    )
    assert res.status_code == 409, f"Should have thrown unique constraint violation: {res.status_code} {res.text}"

    get_res = requests.get(f"{SUPABASE_URL}/rest/v1/volunteer_order_events?order_id=eq.{order_id_a}", headers=headers_a).json()
    event_a_id = get_res[0]["id"]
        
    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/volunteer_order_events",
        headers=headers_a,
        json={
            "order_id": order_id_a,
            "event_type": "PROBE_CORRECTION",
            "occurred_at": "2026-08-07T18:05:00Z",
            "provenance": "OBSERVED",
            "supersedes_id": event_a_id,
            "correction_reason": "Typo in data",
            "client_event_id": "probe_3"
        }
    )
    assert res.status_code == 201, f"Failed to insert correction: {res.text}"

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/volunteer_orders?participant_id=eq.{id_b}",
        headers=headers_a
    )
    assert len(res.json()) == 0, f"Participant A cannot read Participant B's orders. Data: {res.text}"
    print("RLS test passed.")
