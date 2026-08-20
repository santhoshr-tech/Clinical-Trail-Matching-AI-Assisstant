from fastapi import APIRouter, Depends
from typing import List
from app.schemas.common import ApiResponse, UserRole
from app.core.security import require_role, AuthenticatedUser
from app.modules.audit.service import get_recent_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/logs", response_model=ApiResponse[List[dict]])
async def list_audit_logs(
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER
    ]))
):
    logs = get_recent_audit_logs(limit=50)
    return ApiResponse(data=logs)
