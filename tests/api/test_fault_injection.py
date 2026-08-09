import os
import httpx
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from services.api.main import app

client = TestClient(app)

def test_db_unavailable_readyz():
    with patch("httpx.AsyncClient.head", side_effect=httpx.ConnectTimeout("Timeout")):
        # We need env vars present for it to even try
        os.environ["SUPABASE_URL"] = "http://mock-supabase.local"
        os.environ["SUPABASE_ANON_KEY"] = "mock-key"
        
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json() == {"status": "unready", "db_connected": False}

def test_db_available_readyz():
    class MockResponse:
        status_code = 200
        
    async def mock_head(*args, **kwargs):
        return MockResponse()
        
    with patch("httpx.AsyncClient.head", new=mock_head):
        os.environ["SUPABASE_URL"] = "http://mock-supabase.local"
        os.environ["SUPABASE_ANON_KEY"] = "mock-key"
        
        response = client.get("/readyz")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "db_connected": True}

# We can also add TomTom timeout mock when that service is fully wired.
