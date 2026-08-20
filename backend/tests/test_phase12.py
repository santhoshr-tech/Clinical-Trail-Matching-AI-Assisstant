import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db, get_db_connection
from app.modules.temporal.service import (
    evaluate_temporal_rule,
    record_timeline_event,
    get_patient_eligibility_timeline
)
from app.schemas.temporal import (
    TemporalValidationRequest,
    TemporalRuleTypeEnum,
    DateQualityStatusEnum
)

client = TestClient(app)

TEST_PATIENT_ID = "99999999-9999-9999-9999-999999999999"
TEST_TRIAL_ID = "t-phase12-trial"


@pytest.fixture(autouse=True)
def setup_phase12_test_data():
    """Setup patient record for temporal testing."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM temporal_validations WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("DELETE FROM patient_eligibility_timeline WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("INSERT OR REPLACE INTO patients (id, mrn_synthetic, age, gender) VALUES (?, 'MRN-9999', 58, 'Male');", (TEST_PATIENT_ID,))
        conn.commit()


def test_1_boundary_exactly_at_time_limit():
    """Verify event date exactly at 30-day window limit returns is_valid=True."""
    # Reference date: 2026-08-15, Event date: 2026-07-16 (exactly 30 days prior)
    req = TemporalValidationRequest(
        rule_type=TemporalRuleTypeEnum.WITHIN_LAST_N_DAYS,
        event_date="2026-07-16",
        reference_date="2026-08-15",
        window_days=30
    )
    res = evaluate_temporal_rule(req, TEST_PATIENT_ID)
    assert res.days_difference == 30
    assert res.is_valid is True
    assert res.date_quality == DateQualityStatusEnum.VALID


def test_2_boundary_just_outside_time_limit():
    """Verify event date just outside 30-day limit (31 days) returns is_valid=False."""
    # Reference date: 2026-08-15, Event date: 2026-07-15 (31 days prior)
    req = TemporalValidationRequest(
        rule_type=TemporalRuleTypeEnum.WITHIN_LAST_N_DAYS,
        event_date="2026-07-15",
        reference_date="2026-08-15",
        window_days=30
    )
    res = evaluate_temporal_rule(req, TEST_PATIENT_ID)
    assert res.days_difference == 31
    assert res.is_valid is False
    assert res.date_quality == DateQualityStatusEnum.VALID


def test_3_missing_date_quality_handling():
    """Verify missing event date returns DateQualityStatusEnum.MISSING and requires_human_review=True."""
    req = TemporalValidationRequest(
        rule_type=TemporalRuleTypeEnum.RECENT_LAB,
        event_date="",
        reference_date="2026-08-15"
    )
    res = evaluate_temporal_rule(req, TEST_PATIENT_ID)
    assert res.is_valid is False
    assert res.date_quality == DateQualityStatusEnum.MISSING
    assert res.requires_human_review is True


def test_4_ambiguous_date_quality_handling():
    """Verify partial ambiguous date expression (e.g. Summer 2026) flags human review."""
    req = TemporalValidationRequest(
        rule_type=TemporalRuleTypeEnum.AFTER_DIAGNOSIS,
        event_date="Summer 2026",
        reference_date="2026-08-15"
    )
    res = evaluate_temporal_rule(req, TEST_PATIENT_ID)
    assert res.is_valid is False
    assert res.date_quality == DateQualityStatusEnum.AMBIGUOUS
    assert res.requires_human_review is True


def test_5_future_date_anomaly():
    """Verify future event date relative to reference date is flagged invalid."""
    req = TemporalValidationRequest(
        rule_type=TemporalRuleTypeEnum.WITHIN_LAST_N_DAYS,
        event_date="2026-09-01",
        reference_date="2026-08-15"
    )
    res = evaluate_temporal_rule(req, TEST_PATIENT_ID)
    assert res.is_valid is False
    assert res.date_quality == DateQualityStatusEnum.FUTURE_DATE_INVALID
    assert res.requires_human_review is True


def test_6_timeline_state_transitions_recorded():
    """Verify timeline state transitions show old and new values."""
    e1 = record_timeline_event(TEST_PATIENT_ID, TEST_TRIAL_ID, "crit-anc", "UNKNOWN", "FAIL", "ANC 0.8", "ANC 0.8 10*3/uL", "Lab Extraction")
    e2 = record_timeline_event(TEST_PATIENT_ID, TEST_TRIAL_ID, "crit-anc", "FAIL", "PASS", "ANC 0.8", "ANC 2.8 10*3/uL", "Conflict Resolution")
    
    tl = get_patient_eligibility_timeline(TEST_PATIENT_ID, TEST_TRIAL_ID)
    assert len(tl.events) == 2
    assert tl.events[0].new_status == "FAIL"
    assert tl.events[1].new_status == "PASS"
    assert tl.events[1].old_value == "ANC 0.8"
    assert tl.events[1].new_value == "ANC 2.8 10*3/uL"
