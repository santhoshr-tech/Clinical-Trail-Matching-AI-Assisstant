from fastapi import APIRouter
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/impact", tags=["impact"])

@router.get("/trial/{trial_version_id}", response_model=ApiResponse[dict])
async def get_impact_report(trial_version_id: str):
    return ApiResponse(data={"trial_version_id": trial_version_id, "affected_patients": 2})
