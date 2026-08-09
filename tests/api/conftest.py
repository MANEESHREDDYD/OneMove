import os
import subprocess
import json

if "SUPABASE_ANON_KEY" not in os.environ or "SUPABASE_SERVICE_ROLE_KEY" not in os.environ:
    try:
        result = subprocess.run(["npx", "supabase", "status", "-o", "json"], capture_output=True, text=True, check=True, shell=True)
        status = json.loads(result.stdout)
        os.environ["SUPABASE_URL"] = status.get("API_URL", "http://127.0.0.1:54321")
        os.environ["SUPABASE_ANON_KEY"] = status.get("ANON_KEY")
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = status.get("SERVICE_ROLE_KEY")
    except Exception as e:
        print(f"Could not load Supabase environment variables natively: {e}")
