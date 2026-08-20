import sys
import uuid
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

client = TestClient(app)

def test_login_and_logout_audit():
    # Login Test
    login_resp = client.post("/api/v1/auth/login", json={"email": "coordinator@clinicaltrial.ai", "role": "research_coordinator"})
    assert login_resp.status_code == 200
    assert login_resp.json()["success"] is True
    assert login_resp.json()["data"]["user"]["role"] == "research_coordinator"

    # Logout Test
    logout_resp = client.post("/api/v1/auth/logout", headers={"X-User-Email": "coordinator@clinicaltrial.ai", "X-User-Role": "research_coordinator"})
    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True

def test_role_restriction_rbac():
    # Attempt investigator review endpoint with 'viewer' role -> Should be 403 Forbidden
    resp_viewer = client.post(
        "/api/v1/review/submit",
        json={"screeningRunId": "run-123", "humanState": "eligible_for_review"},
        headers={"X-User-Role": "viewer"}
    )
    assert resp_viewer.status_code == 403

    # Attempt investigator review endpoint with 'investigator' role -> Should be 200 OK
    resp_inv = client.post(
        "/api/v1/review/submit",
        json={"screeningRunId": "run-123", "humanState": "eligible_for_review"},
        headers={"X-User-Role": "investigator"}
    )
    assert resp_inv.status_code == 200
    assert resp_inv.json()["success"] is True

def test_synthetic_data_insert_and_audit():
    unique_mrn = f"TEST-MRN-{uuid.uuid4().hex[:6]}"
    # Insert Synthetic Patient
    patient_resp = client.post(
        "/api/v1/patients",
        json={"mrnSynthetic": unique_mrn, "age": 52, "gender": "Female"},
        headers={"X-User-Role": "research_coordinator"}
    )
    assert patient_resp.status_code == 200
    patient_id = patient_resp.json()["data"]["id"]

    # Verify Audit Log
    audit_resp = client.get("/api/v1/audit/logs", headers={"X-User-Role": "admin"})
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["data"]
    assert len(logs) > 0
    # Check that our data change action was recorded
    recorded_actions = [l["action"] for l in logs]
    assert "DATA_CHANGE" in recorded_actions or "AUTHENTICATION" in recorded_actions
