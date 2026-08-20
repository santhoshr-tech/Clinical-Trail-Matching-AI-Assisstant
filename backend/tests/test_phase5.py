import pytest
import os
import sys
import sqlite3

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

headers = {
    "X-User-Email": "coordinator@clinicaltrial.ai",
    "X-User-Role": "research_coordinator"
}

PATIENT_ID = "11111111-1111-1111-1111-111111111111"

def test_1_valid_text_document_upload_and_spans():
    file_content = b"Pathology Report for Synthetic Patient.\nDiagnosis: Non-Small Cell Lung Cancer Stage IV.\nLabs: ANC lab 2.8 10*3/uL.\nBiomarkers: EGFR Mutation Negative, PD-L1 TPS 60% Positive."
    files = {"file": ("pathology_report_v1.txt", file_content, "text/plain")}
    data = {
        "patient_id": PATIENT_ID,
        "document_category": "pathology_report",
        "apply_ocr": "false"
    }

    res = client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["success"] is True
    doc_data = res_data["data"]
    assert doc_data["documentCategory"] == "pathology_report"
    assert doc_data["version"] >= 1
    assert doc_data["pageCount"] >= 1
    doc_id = doc_data["documentId"]

    # Retrieve Page Spans & Document Preview
    res_get = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert res_get.status_code == 200
    details = res_get.json()["data"]
    assert len(details["pages"]) >= 1
    assert "sourceSpans" in details["pages"][0]
    assert details["storagePath"].startswith("supabase://")

def test_2_scanned_pdf_tesseract_ocr_fallback():
    # Sparse text simulates scanned PDF requiring OCR fallback
    file_content = b"Scanned PDF"
    files = {"file": ("scanned_radiology_report.pdf", file_content, "application/pdf")}
    data = {
        "patient_id": PATIENT_ID,
        "document_category": "radiology_report",
        "apply_ocr": "true"
    }

    res = client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["ocrApplied"] is True

def test_3_invalid_file_extension_rejection():
    file_content = b"EXE content"
    files = {"file": ("malicious_file.exe", file_content, "application/octet-stream")}
    data = {"patient_id": PATIENT_ID, "document_category": "clinical_note"}

    res = client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
    assert res.status_code == 400
    assert "Invalid file extension" in res.json()["detail"]

def test_4_oversized_file_rejection():
    # Create 11MB dummy content
    file_content = b"A" * (11 * 1024 * 1024)
    files = {"file": ("huge_report.pdf", file_content, "application/pdf")}
    data = {"patient_id": PATIENT_ID, "document_category": "patient_report"}

    res = client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
    assert res.status_code == 400
    assert "exceeds maximum limit" in res.json()["detail"]

def test_5_document_retry_processing():
    file_content = b"Initial note text"
    files = {"file": ("lab_report.txt", file_content, "text/plain")}
    data = {"patient_id": PATIENT_ID, "document_category": "lab_report"}

    res = client.post("/api/v1/documents/upload", files=files, data=data, headers=headers)
    doc_id = res.json()["data"]["documentId"]

    # Retry endpoint
    res_retry = client.post(f"/api/v1/documents/{doc_id}/retry", json={"forceOcr": True}, headers=headers)
    assert res_retry.status_code == 200
    assert res_retry.json()["data"]["status"] == "completed"

def test_6_audit_log_zero_document_content_leak():
    # Verify audit logs record metadata without storing raw document text in audit payloads
    db_path = os.path.join(os.path.dirname(__file__), "..", "local_prototype.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT payload_json FROM audit_logs WHERE entity_type = 'document' ORDER BY timestamp DESC LIMIT 1;")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    payload_str = row[0]
    # Document raw medical text must NOT be present in audit payload
    assert "Stage IV Non-Small Cell Lung Cancer" not in payload_str
    assert "event" in payload_str

