import os
import psycopg
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)

def test_db_unavailable_readyz(monkeypatch):
    with patch("psycopg.connect", side_effect=psycopg.OperationalError("Timeout")):
        monkeypatch.setenv("ZONEPILOT_DB_URL", "postgresql://mock-user:mock-pass@mock-db:5432/postgres")
        
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json() == {"status": "unready", "db_connected": False}

def test_db_available_readyz(monkeypatch):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    with patch("psycopg.connect", return_value=mock_conn):
        monkeypatch.setenv("ZONEPILOT_DB_URL", "postgresql://mock-user:mock-pass@mock-db:5432/postgres")
        
        response = client.get("/readyz")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "db_connected": True}
