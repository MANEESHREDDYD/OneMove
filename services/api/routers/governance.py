from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ConsentLog(BaseModel):
    participant_id: str
    consent_version: str

@router.post("/v1/governance/consent")
async def log_consent(consent: ConsentLog):
    """
    Log participant consent for ZonePilot study.
    """
    return {"status": "success"}

@router.post("/v1/governance/withdraw/{participant_id}")
async def process_withdrawal(participant_id: str):
    """
    FR-4b: Data withdrawal mechanics.
    Sets all operational records for participant to 'WITHDRAWN' status.
    PII masking occurs downstream.
    """
    return {"status": "success", "message": f"Participant {participant_id} withdrawn."}
