import logging
from fastapi import APIRouter, HTTPException, Header
from typing import Dict, Any, Optional
from app.schemas.what_if import WhatIfScenario, WhatIfSimulationResult
from app.modules.what_if.service import (
    create_what_if_scenario,
    run_what_if_simulation,
    duplicate_scenario,
    archive_scenario,
    get_patient_scenarios
)

router = APIRouter(prefix="/what-if", tags=["what-if"])
logger = logging.getLogger("clinical_trial_assistant")


@router.post("/scenario", response_model=Dict[str, Any])
def create_scenario_endpoint(scenario: WhatIfScenario):
    """Create a new hypothetical what-if scenario record."""
    try:
        scen = create_what_if_scenario(scenario)
        return {
            "success": True,
            "data": scen.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Error creating what-if scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate/{scenario_id}", response_model=Dict[str, Any])
def simulate_scenario_endpoint(
    scenario_id: str,
    x_user_email: Optional[str] = Header("investigator@clinicaltrial.ai")
):
    """Run sandboxed hypothetical matching simulation without updating canonical patient records."""
    try:
        res = run_what_if_simulation(scenario_id, user_email=x_user_email or "investigator@clinicaltrial.ai")
        return {
            "success": True,
            "data": res.model_dump(mode="json")
        }
    except ValueError as ve:
        logger.warning(f"Validation error in what-if simulation: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error running what-if simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenarios/patient/{patient_id}", response_model=Dict[str, Any])
def get_patient_scenarios_endpoint(patient_id: str):
    """Retrieve active and archived what-if scenarios for a patient."""
    try:
        scenarios = get_patient_scenarios(patient_id)
        return {
            "success": True,
            "data": [s.model_dump(mode="json") for s in scenarios]
        }
    except Exception as e:
        logger.error(f"Error retrieving scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scenario/{scenario_id}/duplicate", response_model=Dict[str, Any])
def duplicate_scenario_endpoint(scenario_id: str):
    """Duplicate an existing scenario."""
    try:
        new_scen = duplicate_scenario(scenario_id)
        return {
            "success": True,
            "data": new_scen.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Error duplicating scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scenario/{scenario_id}/archive", response_model=Dict[str, Any])
def archive_scenario_endpoint(scenario_id: str):
    """Archive a scenario."""
    try:
        res = archive_scenario(scenario_id)
        return {
            "success": True,
            "data": res
        }
    except Exception as e:
        logger.error(f"Error archiving scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))
