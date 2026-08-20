from fastapi import APIRouter
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/protocols", tags=["protocols"])

@router.get("/versions/{trial_id}", response_model=ApiResponse[dict])
async def get_protocol_versions(trial_id: str):
    return ApiResponse(data={"trial_id": trial_id, "versions": [{"version": 1, "date": "2026-01-01"}]})
