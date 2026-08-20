import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db, get_db_connection
from app.modules.extraction.service import process_document_extraction, review_fact
from app.schemas.extraction import ClinicalCategoryEnum, FactReviewStatusEnum

client = TestClient(app)

headers = {
    "X-User-Email": "coordinator@clinicaltrial.ai",
    "X-User-Role": "research_coordinator"
}

TEST_PATIENT_ID = "77777777-7777-7777-7777-777777777777"
TEST_DOC_ID = "doc-phase7-001"


@pytest.fixture(autouse=True)
def setup_phase7_test_data():
    """Setup patient record for extraction testing."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM extracted_clinical_facts WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("DELETE FROM fact_conflicts WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("INSERT OR REPLACE INTO patients (id, mrn_synthetic, age, gender) VALUES (?, 'MRN-7777', 60, 'Female');", (TEST_PATIENT_ID,))
        conn.commit()


def test_1_negated_history_extraction():
    """Verify negation cues set is_negated=True."""
    sample_text = "Patient denies any history of hypertension or cardiac failure."
    res = process_document_extraction(TEST_PATIENT_ID, TEST_DOC_ID, sample_text)
    
    assert len(res.extracted_facts) >= 1
    negated_fact = [f for f in res.extracted_facts if f.category == ClinicalCategoryEnum.COMORBIDITY][0]
    assert negated_fact.is_negated is True
    assert "hypertension" in negated_fact.raw_text.lower()


def test_2_current_medication_extraction():
    """Verify current medication classification."""
    sample_text = "Current Medication: Pembrolizumab 200mg IV infusion every 3 weeks."
    res = process_document_extraction(TEST_PATIENT_ID, TEST_DOC_ID, sample_text)
    
    med_facts = [f for f in res.extracted_facts if f.category == ClinicalCategoryEnum.MEDICATION]
    assert len(med_facts) >= 1
    assert med_facts[0].is_negated is False
    assert med_facts[0].temporal_expression == "current"


def test_3_previous_treatment_extraction():
    """Verify prior treatment historical classification."""
    sample_text = "Patient received previous treatment with cisplatin chemotherapy in 2024."
    res = process_document_extraction(TEST_PATIENT_ID, TEST_DOC_ID, sample_text)
    
    prev_facts = [f for f in res.extracted_facts if f.category == ClinicalCategoryEnum.PREVIOUS_TREATMENT]
    assert len(prev_facts) >= 1
    assert prev_facts[0].temporal_expression == "historical"


def test_4_recent_lab_extraction():
    """Verify recent lab extraction and normalized units."""
    sample_text = "Laboratory Report 2026-08-01: Absolute Neutrophil Count (ANC) 2.8 10*3/uL."
    res = process_document_extraction(TEST_PATIENT_ID, TEST_DOC_ID, sample_text)
    
    lab_facts = [f for f in res.extracted_facts if f.category == ClinicalCategoryEnum.LAB]
    assert len(lab_facts) >= 1
    assert lab_facts[0].is_stale is False
    assert lab_facts[0].numeric_value == 2.8
    assert lab_facts[0].normalized_unit == "10*3/uL"


def test_5_old_lab_extraction():
    """Verify historical lab date sets is_stale=True."""
    sample_text = "Old Laboratory Report 2025-10-01: ANC 1.9 x10^9/L."
    res = process_document_extraction(TEST_PATIENT_ID, TEST_DOC_ID, sample_text)
    
    lab_facts = [f for f in res.extracted_facts if f.category == ClinicalCategoryEnum.LAB]
    assert len(lab_facts) >= 1
    assert lab_facts[0].is_stale is True
    assert lab_facts[0].data_date == "2025-10-01"


def test_6_positive_and_negative_biomarker_extraction():
    """Verify positive vs negative biomarker status classification."""
    sample_text = """
    Biomarker Panel:
    PD-L1 IHC TPS 60% POSITIVE.
    EGFR Mutation NEGATIVE wild-type.
    """
    res = process_document_extraction(TEST_PATIENT_ID, TEST_DOC_ID, sample_text)
    
    bm_facts = [f for f in res.extracted_facts if f.category == ClinicalCategoryEnum.BIOMARKER]
    assert len(bm_facts) >= 2
    
    pd_l1 = [f for f in bm_facts if "PD-L1" in f.canonical_label][0]
    egfr = [f for f in bm_facts if "EGFR" in f.canonical_label][0]
    
    assert pd_l1.is_negated is False
    assert egfr.is_negated is True


def test_7_conflicting_facts_detection():
    """Verify detection of conflicting facts without overwriting existing data."""
    # First extract positive EGFR fact
    process_document_extraction(TEST_PATIENT_ID, "doc-01", "Biopsy 1: EGFR Exon 19 Deletion POSITIVE.")
    
    # Second extract negative EGFR fact for same patient
    res2 = process_document_extraction(TEST_PATIENT_ID, "doc-02", "Biopsy 2: EGFR Wild-Type NEGATIVE.")
    
    assert res2.conflict_count >= 1
    conflicting_fact = [f for f in res2.extracted_facts if f.has_conflict][0]
    assert conflicting_fact.has_conflict is True
    assert "Contradictory EGFR biomarker result" in conflicting_fact.conflict_details
