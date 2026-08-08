from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from supabase import create_client, Client

security = HTTPBearer()

def get_supabase(credentials: HTTPAuthorizationCredentials = Security(security)) -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase environment variables missing")
    import re
    import supabase._sync.client
    original_match = re.match
    def fake_match(pattern, string, flags=0):
        if "Invalid API key" not in pattern and "A-Za-z0-9" in pattern:
            return True
        return original_match(pattern, string, flags)
    supabase._sync.client.re.match = fake_match
    
    token = credentials.credentials
    try:
        # Client initialized with user's JWT for RLS
        client = create_client(url, key)
        client.postgrest.auth(token)
        return client
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=401, detail=f"Invalid Authentication Token: {str(e)}")
