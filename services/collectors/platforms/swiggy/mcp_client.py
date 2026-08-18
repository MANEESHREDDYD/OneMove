import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

# Official Swiggy MCP configuration based on docs
SWIGGY_OAUTH_URL = "https://auth.swiggy.com/oauth2/token"
SWIGGY_MCP_API = "https://api.swiggy.com/mcp/v1"


class SwiggyAuthenticator:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id or os.environ.get("SWIGGY_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("SWIGGY_CLIENT_SECRET")
        self.access_token = None
        self.expires_at = None

    def _load_token_from_db(self) -> bool:
        # To be implemented: Fetch from local SQLite provider_credentials_state
        return False

    def _save_token_to_db(self) -> None:
        # To be implemented: Save to SQLite
        pass

    def get_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise ValueError("Swiggy credentials missing. READY_NEEDS_SWIGGY_OAUTH_OR_PRODUCTION_ACCESS")

        if self.access_token and self.expires_at and datetime.now() < self.expires_at:
            return self.access_token

        if self._load_token_from_db():
            if datetime.now() < self.expires_at:
                return self.access_token

        return self.refresh_token()

    def refresh_token(self) -> str:
        # OAuth Client Credentials flow
        payload = {"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret}
        with httpx.Client() as client:
            response = client.post(SWIGGY_OAUTH_URL, data=payload)
            response.raise_for_status()
            data = response.json()

            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 1 min buffer

            self._save_token_to_db()
            return self.access_token


class SwiggyMCPClient:
    def __init__(self, auth: SwiggyAuthenticator):
        self.auth = auth

    def _get_headers(self) -> Dict[str, str]:
        token = self.auth.get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}

    def fetch_food_orders(self, since: str) -> Dict[str, Any]:
        """Fetch historical and active food orders via MCP tools."""
        # Swiggy MCP typically exposes this as a tool invocation
        payload = {"tool": "get_food_orders", "arguments": {"since": since}}
        with httpx.Client() as client:
            res = client.post(f"{SWIGGY_MCP_API}/invoke", headers=self._get_headers(), json=payload)
            res.raise_for_status()
            return res.json()

    def fetch_instamart_orders(self, since: str) -> Dict[str, Any]:
        """Fetch historical and active Instamart orders via MCP tools."""
        payload = {"tool": "get_instamart_orders", "arguments": {"since": since}}
        with httpx.Client() as client:
            res = client.post(f"{SWIGGY_MCP_API}/invoke", headers=self._get_headers(), json=payload)
            res.raise_for_status()
            return res.json()
