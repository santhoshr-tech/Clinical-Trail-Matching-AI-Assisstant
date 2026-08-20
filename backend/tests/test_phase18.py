import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_phase18_test_data():
    """Ensure db is initialized before Phase 18 e2e verification tests run."""
    init_db()

import uuid

def test_1_phase18_scenario_patient_workflow():
    """Verify steps 1-8: Login, Synthetic patient creation, facts, timeline, document upload, and conflict resolution."""
    headers = {"X-User-Role": "research_coordinator", "X-User-Email": "coordinator@clinicaltrial.ai"}
    
    # 1. Login check
    login_res = client.post("/api/v1/auth/login", json={"email": "coordinator@clinicaltrial.ai", "role": "research_coordinator"})
    assert login_res.status_code == 200
    assert login_res.json()["data"]["user"]["email"] == "coordinator@clinicaltrial.ai"

    unique_mrn = f"PAT-SYN-P18-{uuid.uuid4().hex[:6]}"
    # 2. Create synthetic patient
    patient_payload = {
        "mrnSynthetic": unique_mrn,
        "age": 62,
        "gender": "Female",
        "primaryDiagnosis": "Stage IV Non-Small Cell Lung Cancer",
        "diseaseStage": "Stage IV",
        "comorbidities": "Hypertension",
        "allergies": "Penicillin"
    }
    create_res = client.post("/api/v1/patients", json=patient_payload, headers=headers)
    assert create_res.status_code == 200
    patient_id = create_res.json()["data"]["id"]

    # 3. Add clinical facts (lab, biomarker, condition)
    fact_res = client.post(f"/api/v1/patients/{patient_id}/facts", json={
        "factType": "lab",
        "rawValue": "ANC lab 2.8 10*3/uL",
        "normalizedValue": "Absolute Neutrophil Count: 2.8 10*3/uL",
        "code": "26499-4",
        "numericValue": 2.8,
        "unit": "10*3/uL"
    }, headers=headers)
    assert fact_res.status_code == 200

    # 4. View timeline
    timeline_res = client.get(f"/api/v1/patients/{patient_id}/timeline", headers=headers)
    assert timeline_res.status_code == 200
    assert len(timeline_res.json()["data"]) >= 1

    # 5. Document upload & extraction
    doc_files = {'file': ('synthetic_report.txt', b'Patient Diagnosis: Non-Small Cell Lung Cancer. Labs: ANC 2.8. Biomarkers: PD-L1 60%.', 'text/plain')}
    doc_res = client.post(
        "/api/v1/documents/upload",
        files=doc_files,
        data={"patient_id": patient_id, "document_category": "pathology_report"},
        headers=headers
    )
    assert doc_res.status_code == 200
    assert doc_res.json()["data"]["processingStatus"] == "completed"

    # 6. Conflict Resolution
    conflicts_res = client.get(f"/api/v1/conflicts/cases/patient/{patient_id}", headers=headers)
    assert conflicts_res.status_code == 200


def test_2_phase18_trial_matching_simulator_and_analytics():
    """Verify steps 9-27: Trial search, import, screening, what-if, audit, and metrics."""
    headers = {"X-User-Role": "research_coordinator", "X-User-Email": "coordinator@clinicaltrial.ai"}

    # Search and import trial
    trials_res = client.get("/api/v1/trials/search?query=lung", headers=headers)
    assert trials_res.status_code == 200
    trials = trials_res.json()["data"]
    assert len(trials) >= 1
    trial_id = trials[0]["nctId"]

    # Create what-if scenario
    scen_res = client.post("/api/v1/what-if/scenario", json={
        "patient_id": "00000000-0000-0000-0000-000000000001",
        "trial_id": trial_id,
        "scenario_name": "Hypothetical ANC Boost",
        "modifications": [
            {
                "field_category": "lab",
                "field_name": "Absolute Neutrophil Count",
                "hypothetical_value": "3.5 10*3/uL",
                "raw_unit": "10*3/uL",
                "is_negated": False,
                "event_date": "2026-08-01"
            }
        ]
    }, headers=headers)
    assert scen_res.status_code == 200
    scen_id = scen_res.json()["data"]["scenario_id"]

    # Run what-if simulation
    sim_res = client.post(f"/api/v1/what-if/simulate/{scen_id}", headers=headers)
    assert sim_res.status_code == 200
    assert "simulated_overall_status" in sim_res.json()["data"]

    # Audit log check
    audit_res = client.get("/api/v1/audit/logs", headers=headers)
    assert audit_res.status_code == 200
    assert len(audit_res.json()["data"]) >= 1

    # Security audit check
    sec_res = client.get("/api/v1/security/review", headers=headers)
    assert sec_res.status_code == 200
    assert sec_res.json()["data"]["total_checks"] == 17
