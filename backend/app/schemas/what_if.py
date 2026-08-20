from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class WhatIfFieldCategoryEnum(str, Enum):
    LAB = "lab"
    BIOMARKER = "biomarker"
    DISEASE_STAGE = "disease_stage"
    MEDICATION = "medication"
    PRIOR_TREATMENT = "prior_treatment"
    EVENT_DATE = "event_date"

class WhatIfModification(BaseModel):
    field_category: WhatIfFieldCategoryEnum
    field_name: str
    hypothetical_value: str
    raw_unit: Optional[str] = None
    is_negated: bool = False
    event_date: Optional[str] = "2026-08-01"

class WhatIfScenario(BaseModel):
    scenario_id: Optional[str] = None
    patient_id: str
    trial_id: str
    scenario_name: str
    status: str = "active"
    modifications: List[WhatIfModification] = Field(default_factory=list)
    created_by: str = "investigator@clinicaltrial.ai"
    created_at: Optional[str] = None

class CriterionDelta(BaseModel):
    criterion_id: str
    criterion_text: str
    old_state: str
    new_state: str
    delta_explanation: str
    cause_field: str

class WhatIfSimulationResult(BaseModel):
    scenario_id: str
    patient_id: str
    trial_id: str
    original_overall_status: str
    simulated_overall_status: str
    original_score: float
    simulated_score: float
    criteria_deltas: List[CriterionDelta] = Field(default_factory=list)
    audit_event_id: str
