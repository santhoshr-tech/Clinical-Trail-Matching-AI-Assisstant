from fastapi import APIRouter
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary", response_model=ApiResponse[dict])
async def get_dashboard_summary():
    return ApiResponse(data={
        "totalPatients": 24,
        "activeTrials": 12,
        "pendingCRCReviews": 5,
        "aiProvider": "mock"
    })
