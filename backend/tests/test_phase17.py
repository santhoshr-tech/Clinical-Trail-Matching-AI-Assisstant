import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db
from app.modules.security.service import run_phase17_security_audit

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_phase17_test_data():
    """Ensure db is initialized before security tests run."""
    init_db()


def test_1_phase17_security_audit_execution():
    """Verify Phase 17 security audit suite executes and checks all 17 requirements."""
    report = run_phase17_security_audit()
    assert report.total_checks == 17
    assert len(report.security_checklist) == 17
    assert report.passed_checks + report.remediated_checks >= 17
    assert report.failed_checks == 0


def test_2_security_review_api_endpoint():
    """Verify GET /api/v1/security/review returns 200 OK and structured security report."""
    response = client.get("/api/v1/security/review", headers={"X-User-Role": "admin"})
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["phase"] == "Phase 17: Security & Privacy Review"
    assert data["total_checks"] == 17
    assert data["deployment_status"].startswith("STOPPED")


def test_3_export_access_control_rbac():
    """Verify export endpoints enforce RBAC access control."""
    # Attempt unauthorized access or test RBAC header validation
    response = client.get("/api/v1/feedback/export/deidentified", headers={"X-User-Role": "viewer"})
    assert response.status_code == 403

    response_auth = client.get("/api/v1/feedback/export/deidentified", headers={"X-User-Role": "admin"})
    assert response_auth.status_code == 200


def test_4_sanitized_config_status_no_secrets():
    """Verify /api/config/status reports sanitized state flags only."""
    response = client.get("/api/config/status")
    assert response.status_code == 200
    res_data = response.json()["data"]
    assert "aiProvider" in res_data
    assert res_data["status"] in ["configured", "missing", "invalid"]
    assert "gemini_key" not in res_data
    assert "service_role_key" not in res_data


def test_5_document_upload_file_validation():
    """Verify illegal file extensions or oversized files are rejected with 400 Bad Request."""
    files = {'file': ('malicious.exe', b'binary content', 'application/x-msdownload')}
    data = {'patient_id': '00000000-0000-0000-0000-000000000001', 'document_category': 'patient_report'}
    
    response = client.post(
        "/api/v1/documents/upload",
        files=files,
        data=data,
        headers={"X-User-Role": "research_coordinator"}
    )
    assert response.status_code == 400
    assert "Only .pdf and .txt files are supported" in response.json()["detail"]


def test_6_regulatory_disclaimers_and_limitations_present():
    """Verify non-regulatory compliance disclaimer and known limitations are documented."""
    report = run_phase17_security_audit()
    assert "NON-REGULATORY" in report.regulatory_disclaimer
    assert len(report.known_limitations) >= 4
