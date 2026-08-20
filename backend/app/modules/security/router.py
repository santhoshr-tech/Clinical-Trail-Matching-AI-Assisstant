import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from app.schemas.security import SecurityReviewReport
from app.schemas.common import UserRole
from app.core.security import require_role, AuthenticatedUser
from app.modules.security.service import run_phase17_security_audit

router = APIRouter(prefix="/security", tags=["security"])
logger = logging.getLogger("clinical_trial_assistant")

@router.get("/review", response_model=Dict[str, Any])
def get_security_review_endpoint(
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER
    ]))
):
    """Retrieve complete Phase 17 Security & Privacy Review report."""
    try:
        report = run_phase17_security_audit()
        return {
            "success": True,
            "data": report.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Error conducting security review: {e}")
        raise HTTPException(status_code=500, detail=str(e))
