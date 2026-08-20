import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

headers = {
    "X-User-Email": "coordinator@clinicaltrial.ai",
    "X-User-Role": "research_coordinator"
}

def test_list_patients_and_scenarios():
    response = client.get("/api/v1/patients", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    patients = data["data"]
    assert len(patients) >= 5
    
    mrns = [p["mrnSynthetic"] for p in patients]
    assert "SYNTH-SCENARIO-A" in mrns
    assert "SYNTH-SCENARIO-B" in mrns
    assert "SYNTH-SCENARIO-C" in mrns
    assert "SYNTH-SCENARIO-D" in mrns
    assert "SYNTH-SCENARIO-E" in mrns

def test_search_patients():
    response = client.get("/api/v1/patients?query=SYNTH-SCENARIO-A", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["mrnSynthetic"] == "SYNTH-SCENARIO-A"

def test_patient_details_and_facts():
    # Fetch list first to get ID of Scenario A
    res_list = client.get("/api/v1/patients?query=SYNTH-SCENARIO-A", headers=headers)
    patient_id = res_list.json()["data"][0]["id"]

    response = client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["profile"]["mrnSynthetic"] == "SYNTH-SCENARIO-A"
    assert data["profile"]["syntheticDataFlag"] is True
    assert len(data["labs"]) >= 1
    assert data["labs"][0]["raw_value"] == "ANC lab 2.8 10*3/uL"
    assert data["labs"][0]["normalized_value"] == "Absolute Neutrophil Count: 2.8 10*3/uL"

def test_create_update_delete_patient():
    # 1. Create Patient
    create_payload = {
        "mrnSynthetic": "TEST-PHASE3-PATIENT",
        "age": 45,
        "gender": "Male",
        "location": "Site 01",
        "primaryDiagnosis": "Melanoma",
        "diseaseStage": "Stage III",
        "comorbidities": "None",
        "allergies": "Latex"
    }
    res_create = client.post("/api/v1/patients", json=create_payload, headers=headers)
    assert res_create.status_code == 200
    p_data = res_create.json()["data"]
    p_id = p_data["id"]
    assert p_data["version"] == 1

    # 2. Update Patient (Increment version)
    update_payload = {
        "age": 46,
        "diseaseStage": "Stage IV"
    }
    res_update = client.put(f"/api/v1/patients/{p_id}", json=update_payload, headers=headers)
    assert res_update.status_code == 200
    assert res_update.json()["data"]["version"] == 2

    # 3. Add Clinical Fact with raw vs normalized
    fact_payload = {
        "factType": "lab",
        "rawValue": "ANC lab 3.1 10*3/uL",
        "normalizedValue": "Absolute Neutrophil Count: 3.1 10*3/uL",
        "code": "26499-4",
        "numericValue": 3.1,
        "unit": "10*3/uL",
        "factDate": "2026-08-10"
    }
    res_fact = client.post(f"/api/v1/patients/{p_id}/facts", json=fact_payload, headers=headers)
    assert res_fact.status_code == 200

    # 4. Verify Timeline Updated
    res_timeline = client.get(f"/api/v1/patients/{p_id}/timeline", headers=headers)
    assert res_timeline.status_code == 200
    timeline_events = res_timeline.json()["data"]
    assert len(timeline_events) >= 2

    # 5. Delete Patient (Admin header)
    admin_headers = {"X-User-Email": "admin@clinicaltrial.ai", "X-User-Role": "admin"}
    res_delete = client.delete(f"/api/v1/patients/{p_id}", headers=admin_headers)
    assert res_delete.status_code == 200
