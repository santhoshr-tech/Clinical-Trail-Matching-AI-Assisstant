from fastapi import APIRouter
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/normalization", tags=["normalization"])

@router.post("", response_model=ApiResponse[dict])
async def normalize():
    return ApiResponse(data={"status": "normalized", "coding_system": "RxNorm"})
