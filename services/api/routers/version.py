import logging

from fastapi import APIRouter, Depends, HTTPException

from services.api.contracts.release_identity import ReleaseIdentityResponse
from services.api.core.auth import get_current_user
from services.api.services.release_identity import (
    ReleaseIdentityService,
    ReleaseIdentityUnavailable,
    get_release_identity_service,
)

router = APIRouter(prefix="/api/v1", tags=["release"])
logger = logging.getLogger("zonepilot.release_identity")


@router.get("/version", response_model=ReleaseIdentityResponse)
def get_version(
    _user: dict = Depends(get_current_user),
    service: ReleaseIdentityService = Depends(get_release_identity_service),
):
    """Return one authenticated, verified release and artifact identity."""

    try:
        return service.get_release_identity()
    except ReleaseIdentityUnavailable:
        logger.warning(
            "release_identity_unavailable",
            extra={"error_code": "RELEASE_IDENTITY_UNAVAILABLE"},
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "RELEASE_IDENTITY_UNAVAILABLE",
                    "message": "Release identity is unavailable or could not be verified.",
                    "retryable": True,
                    "details": {},
                }
            },
        ) from None
