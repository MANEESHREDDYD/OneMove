import json
import os
import urllib.request

from dotenv import dotenv_values

env = dotenv_values(".env.local")
SUPABASE_URL = env.get("SUPABASE_URL") or env.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_ANON_KEY = env.get("SUPABASE_ANON_KEY") or env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
TENANT_A_EMAIL = "operator@onemove.internal"
TENANT_A_PASS = os.environ.get("TENANT_A_PASSWORD") or "OneMoveOperator2026!"

# 1. Login to Supabase
url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/token?grant_type=password"
headers = {
    "Content-Type": "application/json",
    "apikey": SUPABASE_ANON_KEY,
}
payload = {"email": TENANT_A_EMAIL, "password": TENANT_A_PASS}
req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
with urllib.request.urlopen(req, timeout=15) as resp:
    token = json.loads(resp.read().decode("utf-8"))["access_token"]
print("Supabase token acquired!")

# 2. Test Staging API Version
api_url = "https://zonepilot-api-staging-935663019643.asia-south1.run.app/api/v1/version"
req2 = urllib.request.Request(api_url, headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req2, timeout=15) as resp2:
    data = json.loads(resp2.read().decode("utf-8"))
    print("Staging API Version Response:", json.dumps(data, indent=2))
