from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.schemas.common import ApiResponse, UserRole, ScreeningState
from app.core.security import require_role, AuthenticatedUser
from app.modules.audit.service import log_audit_event

router = APIRouter(prefix="/review", tags=["review"])

class SubmitReviewRequest(BaseModel):
    screeningRunId: str
    humanState: ScreeningState
    overrideFlag: bool = False
    overrideReason: Optional[str] = None

@router.post("/submit", response_model=ApiResponse[dict])
async def submit_review(
    request: SubmitReviewRequest,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    audit_id = log_audit_event(
        action="REVIEW_SUBMIT",
        entity_type="screening_run",
        entity_id=request.screeningRunId,
        user_id=current_user.user_id,
        payload={
            "humanState": request.humanState.value,
            "overrideFlag": request.overrideFlag,
            "overrideReason": request.overrideReason,
            "reviewerRole": current_user.role.value
        }
    )

    return ApiResponse(data={
        "status": "submitted",
        "reviewId": f"rev-{audit_id[:8]}",
        "screeningRunId": request.screeningRunId,
        "humanState": request.humanState.value
    })
