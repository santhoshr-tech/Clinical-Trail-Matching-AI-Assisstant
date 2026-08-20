import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db, get_db_connection
from app.modules.criteria.service import parse_protocol_text_into_criteria, store_parsed_criteria, set_criterion_approval
from app.schemas.criteria import ApprovalStatusEnum
from app.modules.matching.service import run_patient_trial_matching
from app.modules.evidence.service import (
    generate_decision_trace,
    calculate_evidence_reliability_score,
    validate_trace_completeness
)
from app.schemas.evidence import DecisionTraceObject

client = TestClient(app)

headers = {
    "X-User-Email": "investigator@clinicaltrial.ai",
    "X-User-Role": "principal_investigator"
}

TEST_TRIAL_ID = "t-phase10-trial"
PATIENT_PASS = "11111111-1111-1111-1111-111111111111"
PATIENT_FAIL = "22222222-2222-2222-2222-222222222222"
PATIENT_CONFLICT = "33333333-3333-3333-3333-333333333333"
PATIENT_UNKNOWN = "44444444-4444-4444-4444-444444444444"


@pytest.fixture(autouse=True)
def setup_phase10_test_data():
    """Setup test criteria and run matching evaluation."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trial_criteria WHERE trial_id = ?;", (TEST_TRIAL_ID,))
        cursor.execute("DELETE FROM patient_trial_matches WHERE trial_id = ?;", (TEST_TRIAL_ID,))
        
        # Low ANC lab for patient 22222222 to trigger FAIL
        cursor.execute("INSERT OR REPLACE INTO patient_labs (id, patient_id, raw_value, normalized_value, loinc_code, numeric_value, unit, lab_date, is_stale, verification_status) VALUES ('b2222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'ANC lab 0.8 10*3/uL', 'Absolute Neutrophil Count: 0.8 10*3/uL', '26499-4', 0.8, '10*3/uL', '2026-08-01', 0, 'verified');")
        conn.commit()

    protocol_text = """
    Inclusion Criteria:
    1. Age >= 18 years old.
    2. Stage IV Non-Small Cell Lung Cancer.
    3. Absolute Neutrophil Count (ANC) >= 1.5 x 10^9/L.
    
    Exclusion Criteria:
    1. Active EGFR mutation or ALK translocation present.
    """
    
    parsed = parse_protocol_text_into_criteria(TEST_TRIAL_ID, protocol_text)
    stored = store_parsed_criteria(TEST_TRIAL_ID, parsed)
    for item in stored:
        set_criterion_approval(item["id"], ApprovalStatusEnum.APPROVED, "principal_investigator")

    # Run matching for all test scenario patients
    run_patient_trial_matching(PATIENT_PASS, TEST_TRIAL_ID)
    run_patient_trial_matching(PATIENT_FAIL, TEST_TRIAL_ID)
    run_patient_trial_matching(PATIENT_CONFLICT, TEST_TRIAL_ID)
    run_patient_trial_matching(PATIENT_UNKNOWN, TEST_TRIAL_ID)


def get_match_and_criterion_id(patient_id: str, target_status: str):
    """Helper to retrieve match_id and criterion_id matching target status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM patient_trial_matches WHERE patient_id = ? AND trial_id = ? ORDER BY evaluated_at DESC;", (patient_id, TEST_TRIAL_ID))
        match_row = cursor.fetchone()
        match_id = match_row["id"]

        cursor.execute("SELECT criterion_id, status FROM patient_criterion_evaluations WHERE match_id = ? AND status = ?;", (match_id, target_status))
        eval_row = cursor.fetchone()
        if not eval_row:
            cursor.execute("SELECT criterion_id, status FROM patient_criterion_evaluations WHERE match_id = ?;", (match_id,))
            eval_row = cursor.fetchone()
        return match_id, eval_row["criterion_id"]


def test_1_trace_pass_decision():
    """Verify decision trace for a PASS decision."""
    match_id, crit_id = get_match_and_criterion_id(PATIENT_PASS, "PASS")
    trace = generate_decision_trace(match_id, crit_id)

    assert trace.status == "PASS"
    assert trace.patient_id == PATIENT_PASS
    assert trace.completeness_score == 1.0
    assert len(trace.evidence_items) >= 1
    assert trace.matching_engine_version == "v1.0.0-deterministic"


def test_2_trace_fail_decision():
    """Verify decision trace for a FAIL decision."""
    match_id, crit_id = get_match_and_criterion_id(PATIENT_FAIL, "FAIL")
    trace = generate_decision_trace(match_id, crit_id)

    assert trace.status == "FAIL"
    assert trace.patient_id == PATIENT_FAIL
    assert trace.completeness_score == 1.0
    assert trace.reliability_score > 0.0


def test_3_trace_unknown_decision():
    """Verify decision trace for an UNKNOWN decision."""
    match_id, crit_id = get_match_and_criterion_id(PATIENT_UNKNOWN, "UNKNOWN")
    trace = generate_decision_trace(match_id, crit_id)

    assert trace.status == "UNKNOWN"
    assert trace.patient_id == PATIENT_UNKNOWN
    assert trace.completeness_score == 1.0


def test_4_trace_conflict_decision():
    """Verify decision trace for a CONFLICT decision."""
    match_id, crit_id = get_match_and_criterion_id(PATIENT_CONFLICT, "CONFLICT")
    trace = generate_decision_trace(match_id, crit_id)

    assert trace.status == "CONFLICT"
    assert trace.patient_id == PATIENT_CONFLICT
    assert trace.completeness_score == 1.0


def test_5_confirm_required_trace_fields():
    """Confirm all 13 required trace fields exist on DecisionTraceObject."""
    match_id, crit_id = get_match_and_criterion_id(PATIENT_PASS, "PASS")
    trace = generate_decision_trace(match_id, crit_id)

    assert trace.trace_id is not None
    assert trace.match_id is not None
    assert trace.criterion_id is not None
    assert trace.trial_id is not None
    assert trace.patient_id is not None
    assert trace.patient_snapshot_id is not None
    assert trace.status is not None
    assert trace.rule_used is not None
    assert trace.facts_used is not None
    assert trace.evidence_items is not None
    assert trace.reliability_score is not None
    assert trace.matching_engine_version is not None
    assert trace.decision_timestamp is not None
    assert trace.completeness_score == 1.0


def test_6_traceability_completeness_checker_raises_error():
    """Verify completeness validation raises explicit ValueError when required field is missing."""
    match_id, crit_id = get_match_and_criterion_id(PATIENT_PASS, "PASS")
    trace = generate_decision_trace(match_id, crit_id)
    
    # Invalidate a required field
    invalid_trace = trace.model_copy(update={"patient_id": ""})
    with pytest.raises(ValueError) as exc_info:
        validate_trace_completeness(invalid_trace)
    assert "Missing required trace fields" in str(exc_info.value)
