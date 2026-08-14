import os

import pytest
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "mock_anon_key")

def _is_supabase_reachable():
    try:
        r = requests.head(f"{SUPABASE_URL}/rest/v1/", headers={"apikey": ANON_KEY}, timeout=2)
        return r.status_code < 500
    except Exception:
        return False

if not _is_supabase_reachable():
    pytestmark = pytest.mark.skip(reason="Live Supabase environment unreachable at SUPABASE_URL")

def test_role_attacks():
    email = "attacker@onemove.com"
    password = "password123"
    
    auth_url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {"apikey": ANON_KEY, "Content-Type": "application/json"}
    
    # Try to signup with malicious raw_user_meta_data assigning admin
    res = requests.post(auth_url, json={"email": email, "password": password, "data": {"role": "admin"}}, headers=headers)
    if res.status_code != 200:
        res = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", json={"email": email, "password": password}, headers=headers)
    
    user = res.json()
    token = user["access_token"]
    user_id = user["user"]["id"]

    headers_auth = {
        "apikey": ANON_KEY, 
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Verify that the trigger forced them to customer
    prof_res = requests.get(f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}", headers=headers_auth)
    assert prof_res.status_code == 200, f"Failed to get profile: {prof_res.text}"
    prof = prof_res.json()
    assert len(prof) > 0, f"Profile not found for user {user_id}. DB state might be corrupt or RLS failed."
    assert prof[0]["role"] == "customer", "Trigger failed to force customer role on signup"

    # Try self role update
    res = requests.patch(f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}", headers=headers_auth, json={"role": "admin"})
    
    prof = requests.get(f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}", headers=headers_auth).json()
    assert prof[0]["role"] == "customer", "Role update attack succeeded!"
    print("Role attacks blocked successfully.")

    # Try reading studies
    res = requests.get(f"{SUPABASE_URL}/rest/v1/studies", headers=headers_auth)
    assert len(res.json()) == 0, "Non-admin could read studies table!"

