from fastapi import APIRouter
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/terminology", tags=["terminology"])

@router.get("/lookup", response_model=ApiResponse[dict])
async def lookup_term(term: str):
    return ApiResponse(data={"term": term, "code": "SNOMED-12345", "label": f"Standardized {term}"})
