from fastapi import APIRouter

router = APIRouter(prefix="/governance", tags=["Governance"])

@router.post("/consent")
def submit_consent(participant_id: str, agreed: bool):
    return {"status": "CONSENT_RECORDED", "participant_id": participant_id, "agreed": agreed}

@router.post("/withdraw")
def withdraw_participant(participant_id: str):
    return {"status": "WITHDRAWN", "participant_id": participant_id}

@router.post("/activate")
def activate_participant(participant_id: str):
    return {"status": "ACTIVATED", "participant_id": participant_id}

@router.get("/retention")
def retention_audit():
    return {"status": "AUDIT_RUNNING", "flagged_records": 0}
