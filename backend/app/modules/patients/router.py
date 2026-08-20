from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from app.schemas.common import ApiResponse, UserRole
from app.core.security import require_role, AuthenticatedUser
from app.modules.audit.service import log_audit_event
from app.core.db import get_db_connection, calculate_stale_flag

router = APIRouter(prefix="/patients", tags=["patients"])

class PatientCreateRequest(BaseModel):
    mrnSynthetic: str
    age: int
    gender: str
    location: Optional[str] = "Synthetic Oncology Clinic - Site 01"
    primaryDiagnosis: Optional[str] = "Stage IV Non-Small Cell Lung Cancer"
    diseaseStage: Optional[str] = "Stage IV"
    comorbidities: Optional[str] = "None"
    allergies: Optional[str] = "Penicillin"

class PatientUpdateRequest(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    primaryDiagnosis: Optional[str] = None
    diseaseStage: Optional[str] = None
    comorbidities: Optional[str] = None
    allergies: Optional[str] = None
    patientStatus: Optional[str] = None

class AddClinicalFactRequest(BaseModel):
    factType: str # condition, medication, lab, biomarker
    rawValue: str
    normalizedValue: str
    code: Optional[str] = None
    numericValue: Optional[float] = None
    unit: Optional[str] = None
    factDate: Optional[str] = None

# 1. Patient List & Search API
@router.get("", response_model=ApiResponse[List[dict]])
async def list_patients(
    query: Optional[str] = Query(None, description="Search by MRN, diagnosis, or location"),
    status: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER, UserRole.VIEWER
    ]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = "SELECT * FROM patients WHERE 1=1"
    params = []

    if query:
        sql += " AND (mrn_synthetic LIKE ? OR primary_diagnosis LIKE ? OR location LIKE ?)"
        pattern = f"%{query}%"
        params.extend([pattern, pattern, pattern])

    if status:
        sql += " AND patient_status = ?"
        params.append(status)

    sql += " ORDER BY created_at DESC;"

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    patients = []
    for r in rows:
        patients.append({
            "id": r["id"],
            "mrnSynthetic": r["mrn_synthetic"],
            "age": r["age"],
            "gender": r["gender"],
            "location": r["location"],
            "primaryDiagnosis": r["primary_diagnosis"],
            "diseaseStage": r["disease_stage"],
            "comorbidities": r["comorbidities"],
            "allergies": r["allergies"],
            "patientStatus": r["patient_status"],
            "syntheticDataFlag": bool(r["synthetic_data_flag"]),
            "version": r["version"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        })

    return ApiResponse(data=patients)

# 2. Patient Details API (With sub-entities, raw vs normalized values, recency flags, and stale indicators)
@router.get("/{patient_id}", response_model=ApiResponse[dict])
async def get_patient_details(
    patient_id: str,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER, UserRole.VIEWER
    ]))
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients WHERE id = ?;", (patient_id,))
    patient = cursor.fetchone()

    if not patient:
        conn.close()
        raise HTTPException(status_code=404, detail="Patient record not found")

    # Fetch sub-entities
    cursor.execute("SELECT * FROM patient_conditions WHERE patient_id = ? ORDER BY created_at DESC;", (patient_id,))
    conditions = [dict(c) for c in cursor.fetchall()]

    cursor.execute("SELECT * FROM patient_medications WHERE patient_id = ? ORDER BY created_at DESC;", (patient_id,))
    medications = [dict(m) for m in cursor.fetchall()]

    cursor.execute("SELECT * FROM patient_labs WHERE patient_id = ? ORDER BY created_at DESC;", (patient_id,))
    raw_labs = cursor.fetchall()
    labs = []
    for l in raw_labs:
        lab_dict = dict(l)
        lab_dict["is_stale"] = bool(l["is_stale"]) or calculate_stale_flag(l["lab_date"])
        labs.append(lab_dict)

    cursor.execute("SELECT * FROM patient_biomarkers WHERE patient_id = ? ORDER BY created_at DESC;", (patient_id,))
    raw_biomarkers = cursor.fetchall()
    biomarkers = []
    for b in raw_biomarkers:
        bio_dict = dict(b)
        if b["test_date"]:
            bio_dict["is_stale"] = bool(b["is_stale"]) or calculate_stale_flag(b["test_date"])
        biomarkers.append(bio_dict)

    cursor.execute("SELECT * FROM patient_timeline WHERE patient_id = ? ORDER BY event_date DESC;", (patient_id,))
    timeline = [dict(t) for t in cursor.fetchall()]

    conn.close()

    return ApiResponse(data={
        "profile": {
            "id": patient["id"],
            "mrnSynthetic": patient["mrn_synthetic"],
            "age": patient["age"],
            "gender": patient["gender"],
            "location": patient["location"],
            "primaryDiagnosis": patient["primary_diagnosis"],
            "diseaseStage": patient["disease_stage"],
            "comorbidities": patient["comorbidities"],
            "allergies": patient["allergies"],
            "patientStatus": patient["patient_status"],
            "syntheticDataFlag": bool(patient["synthetic_data_flag"]),
            "version": patient["version"],
            "createdAt": patient["created_at"],
            "updatedAt": patient["updated_at"]
        },
        "conditions": conditions,
        "medications": medications,
        "labs": labs,
        "biomarkers": biomarkers,
        "timeline": timeline
    })

# 3. Create Patient API
@router.post("", response_model=ApiResponse[dict])
async def create_patient(
    request: PatientCreateRequest,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    patient_id = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO patients (id, mrn_synthetic, age, gender, location, primary_diagnosis, disease_stage, comorbidities, allergies, patient_status, synthetic_data_flag, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 1, 'coordinator_entry');
        """, (
            patient_id, request.mrnSynthetic, request.age, request.gender,
            request.location, request.primaryDiagnosis, request.diseaseStage,
            request.comorbidities, request.allergies
        ))

        # Add initial diagnosis timeline event
        cursor.execute("""
            INSERT INTO patient_timeline (id, patient_id, event_type, event_date, summary, verification_status)
            VALUES (?, ?, 'DIAGNOSIS', ?, ?, 'verified');
        """, (str(uuid.uuid4()), patient_id, datetime.now().strftime("%Y-%m-%d"), f"Initial Profile Created: {request.primaryDiagnosis}"))

        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Failed to create patient: {str(e)}")
    conn.close()

    log_audit_event(
        action="DATA_CHANGE",
        entity_type="patient",
        entity_id=patient_id,
        user_id=current_user.user_id,
        payload={"event": "PATIENT_CREATED", "mrn": request.mrnSynthetic}
    )

    return ApiResponse(data={"id": patient_id, "mrnSynthetic": request.mrnSynthetic, "version": 1})

# 4. Update Patient Profile (Data Versioning)
@router.put("/{patient_id}", response_model=ApiResponse[dict])
async def update_patient(
    patient_id: str,
    request: PatientUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patients WHERE id = ?;", (patient_id,))
    patient = cursor.fetchone()
    if not patient:
        conn.close()
        raise HTTPException(status_code=404, detail="Patient not found")

    new_version = patient["version"] + 1
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE patients
        SET age = COALESCE(?, age),
            gender = COALESCE(?, gender),
            location = COALESCE(?, location),
            primary_diagnosis = COALESCE(?, primary_diagnosis),
            disease_stage = COALESCE(?, disease_stage),
            comorbidities = COALESCE(?, comorbidities),
            allergies = COALESCE(?, allergies),
            patient_status = COALESCE(?, patient_status),
            version = ?,
            updated_at = ?
        WHERE id = ?;
    """, (
        request.age, request.gender, request.location, request.primaryDiagnosis,
        request.diseaseStage, request.comorbidities, request.allergies,
        request.patientStatus, new_version, now_str, patient_id
    ))

    conn.commit()
    conn.close()

    log_audit_event(
        action="DATA_CHANGE",
        entity_type="patient",
        entity_id=patient_id,
        user_id=current_user.user_id,
        payload={"event": "PATIENT_UPDATED", "newVersion": new_version}
    )

    return ApiResponse(data={"id": patient_id, "version": new_version, "status": "updated"})

# 5. Delete / Archive Patient API
@router.delete("/{patient_id}", response_model=ApiResponse[dict])
async def delete_patient(
    patient_id: str,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.ADMIN]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients WHERE id = ?;", (patient_id,))
    conn.commit()
    conn.close()

    log_audit_event(
        action="DATA_CHANGE",
        entity_type="patient",
        entity_id=patient_id,
        user_id=current_user.user_id,
        payload={"event": "PATIENT_DELETED"}
    )

    return ApiResponse(data={"id": patient_id, "status": "deleted"})

# 6. Add Clinical Fact (Preserves raw vs normalized)
@router.post("/{patient_id}/facts", response_model=ApiResponse[dict])
async def add_clinical_fact(
    patient_id: str,
    request: AddClinicalFactRequest,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    fact_id = str(uuid.uuid4())
    today_str = datetime.now().strftime("%Y-%m-%d")
    fact_date = request.factDate or today_str
    is_stale = calculate_stale_flag(fact_date)

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.factType == "lab":
        cursor.execute("""
            INSERT INTO patient_labs (id, patient_id, raw_value, normalized_value, loinc_code, numeric_value, unit, lab_date, is_stale, verification_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'unverified');
        """, (fact_id, patient_id, request.rawValue, request.normalizedValue, request.code, request.numericValue, request.unit, fact_date, int(is_stale)))
    elif request.factType == "biomarker":
        cursor.execute("""
            INSERT INTO patient_biomarkers (id, patient_id, raw_value, normalized_value, biomarker_name, status_value, test_date, is_stale, verification_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unverified');
        """, (fact_id, patient_id, request.rawValue, request.normalizedValue, request.rawValue, request.normalizedValue, fact_date, int(is_stale)))
    else:
        cursor.execute("""
            INSERT INTO patient_conditions (id, patient_id, raw_value, normalized_value, coding_system, concept_code, verification_status)
            VALUES (?, ?, ?, ?, 'SNOMED-CT', ?, 'unverified');
        """, (fact_id, patient_id, request.rawValue, request.normalizedValue, request.code))

    # Add to clinical timeline
    cursor.execute("""
        INSERT INTO patient_timeline (id, patient_id, event_type, event_date, summary, raw_snippet, verification_status)
        VALUES (?, ?, ?, ?, ?, ?, 'verified');
    """, (str(uuid.uuid4()), patient_id, request.factType.upper(), fact_date, request.normalizedValue, request.rawValue))

    conn.commit()
    conn.close()

    log_audit_event(
        action="DATA_CHANGE",
        entity_type="clinical_fact",
        entity_id=fact_id,
        user_id=current_user.user_id,
        payload={"factType": request.factType, "rawValue": request.rawValue, "normalizedValue": request.normalizedValue}
    )

    return ApiResponse(data={"id": fact_id, "isStale": is_stale, "status": "added"})

# 7. Patient Timeline API
@router.get("/{patient_id}/timeline", response_model=ApiResponse[List[dict]])
async def get_patient_timeline(
    patient_id: str,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER, UserRole.VIEWER
    ]))
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patient_timeline WHERE patient_id = ? ORDER BY event_date DESC;", (patient_id,))
    rows = cursor.fetchall()
    conn.close()

    events = [
        {
            "id": r["id"],
            "eventType": r["event_type"],
            "eventDate": r["event_date"],
            "summary": r["summary"],
            "rawSnippet": r["raw_snippet"],
            "verificationStatus": r["verification_status"]
        } for r in rows
    ]

    return ApiResponse(data=events)
