import pytest
import os
import sys
import sqlite3

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db, get_db_connection
from app.modules.criteria.service import parse_protocol_text_into_criteria, store_parsed_criteria, set_criterion_approval
from app.schemas.criteria import ApprovalStatusEnum
from app.modules.matching.service import run_patient_trial_matching, evaluate_criterion
from app.schemas.matching import CriterionMatchStatusEnum, OverallEligibilityStatusEnum, EvidenceReliabilityEnum

client = TestClient(app)

headers = {
    "X-User-Email": "investigator@clinicaltrial.ai",
    "X-User-Role": "principal_investigator"
}

TEST_TRIAL_ID = "t-phase9-trial"
TEST_PATIENT_PASS = "11111111-1111-1111-1111-111111111111"
TEST_PATIENT_EXCLUDED = "22222222-2222-2222-2222-222222222222"
TEST_PATIENT_CONFLICT = "33333333-3333-3333-3333-333333333333"
TEST_PATIENT_STALE = "44444444-4444-4444-4444-444444444444"


@pytest.fixture(autouse=True)
def setup_phase9_test_data():
    """Setup approved criteria for TEST_TRIAL_ID and seed test patient facts."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trial_criteria WHERE trial_id = ?;", (TEST_TRIAL_ID,))
        cursor.execute("DELETE FROM patient_trial_matches WHERE trial_id = ?;", (TEST_TRIAL_ID,))
        
        # Seed low ANC lab for patient 22222222 to trigger FAIL
        cursor.execute("INSERT OR REPLACE INTO patient_labs (id, patient_id, raw_value, normalized_value, loinc_code, numeric_value, unit, lab_date, is_stale, verification_status) VALUES ('b2222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'ANC lab 0.8 10*3/uL', 'Absolute Neutrophil Count: 0.8 10*3/uL', '26499-4', 0.8, '10*3/uL', '2026-08-01', 0, 'verified');")
        conn.commit()

    protocol_text = """
    Inclusion Criteria:
    1. Age >= 18 years old.
    2. Stage IV Non-Small Cell Lung Cancer.
    3. Absolute Neutrophil Count (ANC) >= 1.5 x 10^9/L.
    4. PD-L1 expression TPS >= 50%.
    
    Exclusion Criteria:
    1. Active EGFR mutation or ALK translocation present.
    2. Severe cardiac disease or active infection.
    """
    
    parsed = parse_protocol_text_into_criteria(TEST_TRIAL_ID, protocol_text)
    stored = store_parsed_criteria(TEST_TRIAL_ID, parsed)
    
    # Approve all criteria for TEST_TRIAL_ID
    for item in stored:
        set_criterion_approval(item["id"], ApprovalStatusEnum.APPROVED, "principal_investigator")


def test_1_fully_eligible_patient_pass():
    """Verify that a fully eligible patient passes all criteria and achieves INVESTIGATOR_REVIEW_REQUIRED overall status."""
    res = run_patient_trial_matching(TEST_PATIENT_PASS, TEST_TRIAL_ID)
    
    assert res.patient_id == TEST_PATIENT_PASS
    assert res.total_criteria >= 4
    assert res.failed_count == 0
    assert res.conflict_count == 0
    assert res.overall_status in [
        OverallEligibilityStatusEnum.INVESTIGATOR_REVIEW_REQUIRED,
        OverallEligibilityStatusEnum.ELIGIBLE_FOR_REVIEW
    ]
    assert res.match_score == 100.0


def test_2_failing_lab_threshold_fail():
    """Verify that a patient failing a requirement returns FAIL criterion status and NOT_ELIGIBLE overall status."""
    # Patient 22222222 has severe cardiac comorbidity which triggers exclusion fail
    res = run_patient_trial_matching(TEST_PATIENT_EXCLUDED, TEST_TRIAL_ID)
    
    assert res.failed_count >= 1
    assert res.overall_status == OverallEligibilityStatusEnum.NOT_ELIGIBLE


def test_3_missing_data_unknown():
    """Verify that missing patient facts yield UNKNOWN criterion status and POTENTIALLY_ELIGIBLE overall status."""
    # Create a new patient with no lab/biomarker data
    empty_patient_id = "99999999-9999-9999-9999-999999999999"
    with get_db_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO patients (id, mrn_synthetic, age, gender) VALUES (?, 'MRN-9999', 45, 'Female');", (empty_patient_id,))
        conn.commit()

    res = run_patient_trial_matching(empty_patient_id, TEST_TRIAL_ID)
    
    assert res.unknown_count >= 1
    assert res.failed_count == 0
    assert res.overall_status == OverallEligibilityStatusEnum.POTENTIALLY_ELIGIBLE


def test_4_conflicting_patient_facts_conflict():
    """Verify that flagged/conflicting facts yield CONFLICT criterion status and MANUAL_REVIEW_REQUIRED overall status."""
    res = run_patient_trial_matching(TEST_PATIENT_CONFLICT, TEST_TRIAL_ID)
    
    assert res.conflict_count >= 1
    assert res.overall_status == OverallEligibilityStatusEnum.MANUAL_REVIEW_REQUIRED


def test_5_stale_lab_date_unknown():
    """Verify that stale lab reports yield UNKNOWN status and STALE evidence reliability."""
    res = run_patient_trial_matching(TEST_PATIENT_STALE, TEST_TRIAL_ID)
    
    # Locate lab criterion result
    lab_results = [r for r in res.criterion_results if r.category == "laboratory"]
    assert len(lab_results) > 0
    lab_res = lab_results[0]
    
    assert lab_res.status == CriterionMatchStatusEnum.UNKNOWN
    assert lab_res.evidence_reliability == EvidenceReliabilityEnum.STALE


def test_6_evaluate_matching_api_endpoint():
    """Verify POST /api/v1/matching/evaluate endpoint."""
    payload = {
        "patient_id": TEST_PATIENT_PASS,
        "trial_id": TEST_TRIAL_ID
    }
    res = client.post("/api/v1/matching/evaluate", json=payload, headers=headers)
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    data = json_data["data"]
    assert "overall_status" in data
    assert "match_score" in data
    assert "criterion_results" in data
