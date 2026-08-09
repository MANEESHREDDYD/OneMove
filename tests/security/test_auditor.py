import pytest
import jwt
import os
import datetime
import pandas as pd
from core.auth import verify_token
from services.etl.pipeline import build_experiment_a_dataset
from routers.events import ProbeObservationCreate
from pydantic import ValidationError

def test_dry_run_contamination_fails_closed():
    # Verify DRY_RUN records are rejected by Experiment A dataset builder
    df = pd.DataFrame([
        {"id": "1", "study_phase": "DRY_RUN", "provenance": "OBSERVED"},
        {"id": "2", "study_phase": "EXPERIMENT_A", "provenance": "OBSERVED"}
    ])
    with pytest.raises(ValueError) as exc:
        build_experiment_a_dataset(df)
    assert "DRY_RUN rows in dataset" in str(exc.value)

def test_jwt_tampering_rejected():
    secret = os.environ.get("SUPABASE_JWT_SECRET", "REDACTED_SYNTHETIC_TEST_SECRET")
    token = jwt.encode({"sub": "user-1", "aud": "authenticated", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, secret, algorithm="HS256")
    tampered_token = token[:-5] + "XXXXX"
    with pytest.raises(Exception):
        verify_token(tampered_token)

def test_forbidden_extra_fields_rejected():
    # Verify browser submitted study_id or platform is strictly rejected by Pydantic fail-closed schema
    invalid_payload = {
        "assignment_id": "assign-123",
        "client_event_id": "evt-123",
        "observed_at_device": "2026-08-08T12:00:00Z",
        "availability_state": "IN_STOCK",
        "study_id": "forbidden-study-id"
    }
    with pytest.raises(ValidationError):
        ProbeObservationCreate(**invalid_payload)

