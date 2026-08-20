from fastapi import APIRouter, Query, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from app.modules.location import location_service

router = APIRouter(prefix="/location", tags=["location"])

class SaveLocationRequest(BaseModel):
    patient_id: str
    address_text: str

@router.get("/nearby-sites")
def get_nearby_sites(
    lat: float = Query(..., description="Latitude of user/location"),
    lon: float = Query(..., description="Longitude of user/location"),
    radius_km: float = Query(50.0, description="Filter radius in kilometers"),
    condition: Optional[str] = Query(None, description="Optional condition filter")
):
    try:
        sites = location_service.get_nearby_trial_sites(
            user_lat=lat,
            user_lon=lon,
            radius_km=radius_km,
            condition=condition
        )
        return {
            "success": True,
            "user_location": {"latitude": lat, "longitude": lon},
            "radius_km": radius_km,
            "total_sites": len(sites),
            "data": sites
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-patient-location")
def save_patient_location(request: SaveLocationRequest):
    try:
        res = location_service.save_patient_address_location(
            patient_id=request.patient_id,
            address_text=request.address_text
        )
        return {"success": True, "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
