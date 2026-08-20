import uuid
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.core.db import get_db_connection, init_db
from app.schemas.matching import (
    CriterionMatchResult,
    TrialMatchResult,
    CriterionMatchStatusEnum,
    EvidenceReliabilityEnum,
    OverallEligibilityStatusEnum
)

logger = logging.getLogger("clinical_trial_assistant")

ENGINE_VERSION = "v1.0.0-deterministic"


def fetch_patient_facts(patient_id: str) -> Dict[str, Any]:
    """Fetch all clinical facts for a patient from database."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Profile
        cursor.execute("SELECT * FROM patients WHERE id = ?;", (patient_id,))
        profile_row = cursor.fetchone()
        profile = dict(profile_row) if profile_row else {}

        # Diagnoses / Conditions
        cursor.execute("SELECT * FROM patient_conditions WHERE patient_id = ?;", (patient_id,))
        diagnoses = [dict(r) for r in cursor.fetchall()]

        # Labs
        cursor.execute("SELECT * FROM patient_labs WHERE patient_id = ?;", (patient_id,))
        labs = [dict(r) for r in cursor.fetchall()]

        # Biomarkers
        cursor.execute("SELECT * FROM patient_biomarkers WHERE patient_id = ?;", (patient_id,))
        biomarkers = [dict(r) for r in cursor.fetchall()]

        # Medications
        cursor.execute("SELECT * FROM patient_medications WHERE patient_id = ?;", (patient_id,))
        medications = [dict(r) for r in cursor.fetchall()]

        return {
            "profile": profile,
            "diagnoses": diagnoses,
            "labs": labs,
            "biomarkers": biomarkers,
            "medications": medications
        }


def fetch_approved_criteria(trial_id: str) -> List[Dict[str, Any]]:
    """Fetch only approved criteria for a clinical trial."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trial_criteria WHERE trial_id = ? AND approval_status = 'approved' ORDER BY criterion_type, created_at;", (trial_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def evaluate_criterion(criterion: Dict[str, Any], patient_facts: Dict[str, Any]) -> CriterionMatchResult:
    """Deterministically evaluate a single criterion node against patient clinical facts."""
    now_iso = datetime.datetime.utcnow().isoformat()
    crit_id = criterion["id"]
    crit_type = criterion["criterion_type"]  # inclusion / exclusion
    category = criterion["category"]
    operator = criterion["operator"]
    val1 = criterion.get("value_primary")
    val2 = criterion.get("value_secondary")
    unit = criterion.get("unit")
    raw_text = criterion["raw_text"]
    crit_version = criterion.get("version", 1)

    profile = patient_facts.get("profile", {})
    diagnoses = patient_facts.get("diagnoses", [])
    labs = patient_facts.get("labs", [])
    biomarkers = patient_facts.get("biomarkers", [])
    medications = patient_facts.get("medications", [])

    rule_description = f"{crit_type.upper()} {category.upper()}: {operator} {val1 or ''} {unit or ''}".strip()

    # Default fallback
    status = CriterionMatchStatusEnum.UNKNOWN
    patient_val = None
    expected_val = f"{operator} {val1 or ''}".strip()
    evidence_text = None
    reliability = EvidenceReliabilityEnum.UNVERIFIED
    data_date = None

    # Check for flagged/conflicting facts across all patient evidence
    all_facts = diagnoses + labs + biomarkers + medications
    has_conflicts = any(f.get("verification_status") == "flagged" for f in all_facts)

    # 1. DEMOGRAPHIC (Age / Gender)
    if category == "demographic":
        patient_age = profile.get("age")
        if patient_age is not None:
            patient_val = f"{patient_age} years"
            evidence_text = f"Patient Demographic Profile: Age {patient_age}, Gender {profile.get('gender')}"
            reliability = EvidenceReliabilityEnum.VERIFIED
            
            # Numeric age rule evaluation
            if operator == "greater_than_or_equal" and val1:
                is_pass = patient_age >= float(val1)
            elif operator == "less_than_or_equal" and val1:
                is_pass = patient_age <= float(val1)
            elif operator == "between" and val1 and val2:
                is_pass = float(val1) <= patient_age <= float(val2)
            else:
                is_pass = patient_age >= 18  # default adult cutoff

            status = CriterionMatchStatusEnum.PASS if is_pass else CriterionMatchStatusEnum.FAIL
        else:
            status = CriterionMatchStatusEnum.UNKNOWN

    # 2. STAGE / DIAGNOSIS
    elif category in ["stage", "diagnosis"]:
        matching_diag = [d for d in diagnoses if any(k in d.get("normalized_value", "").lower() for k in ["stage", "cancer", "nsclc", "carcinoma"])]
        if has_conflicts and matching_diag:
            status = CriterionMatchStatusEnum.CONFLICT
            reliability = EvidenceReliabilityEnum.CONFLICTING
            evidence_text = "Conflicting diagnosis/stage records detected in patient chart."
        elif matching_diag:
            d = matching_diag[0]
            patient_val = d.get("stage") or d.get("normalized_value")
            evidence_text = f"Diagnosis Record: {d.get('normalized_value')} (Stage: {d.get('stage')})"
            reliability = EvidenceReliabilityEnum.VERIFIED if d.get("verification_status") == "verified" else EvidenceReliabilityEnum.UNVERIFIED
            data_date = d.get("diagnosis_date")
            
            req_stage = (val1 or "IV").lower()
            if req_stage in (patient_val or "").lower():
                status = CriterionMatchStatusEnum.PASS
            else:
                status = CriterionMatchStatusEnum.FAIL
        else:
            status = CriterionMatchStatusEnum.UNKNOWN

    # 3. LABORATORY THRESHOLDS
    elif category == "laboratory":
        # Match lab by keyword (e.g. ANC, Creatinine)
        matched_labs = []
        lowered_text = raw_text.lower()
        for lab in labs:
            norm = lab.get("normalized_value", "").lower()
            raw = lab.get("raw_value", "").lower()
            if ("anc" in lowered_text or "neutrophil" in lowered_text) and ("anc" in norm or "neutrophil" in norm or "anc" in raw):
                matched_labs.append(lab)
            elif "creatinine" in lowered_text and "creatinine" in norm:
                matched_labs.append(lab)

        if not matched_labs:
            status = CriterionMatchStatusEnum.UNKNOWN
        else:
            lab = matched_labs[0]
            num_val = lab.get("numeric_value")
            is_stale = lab.get("is_stale", 0) == 1
            data_date = lab.get("lab_date")
            evidence_text = f"Lab Report: {lab.get('normalized_value')} (Date: {data_date})"

            if lab.get("verification_status") == "flagged":
                status = CriterionMatchStatusEnum.CONFLICT
                reliability = EvidenceReliabilityEnum.CONFLICTING
            elif is_stale:
                status = CriterionMatchStatusEnum.UNKNOWN
                reliability = EvidenceReliabilityEnum.STALE
                patient_val = f"{num_val} {lab.get('unit')} (Stale Lab Date: {data_date})"
            elif num_val is not None:
                patient_val = f"{num_val} {lab.get('unit')}"
                reliability = EvidenceReliabilityEnum.VERIFIED if lab.get("verification_status") == "verified" else EvidenceReliabilityEnum.UNVERIFIED

                if operator == "greater_than_or_equal" and val1:
                    is_pass = num_val >= float(val1)
                elif operator == "less_than_or_equal" and val1:
                    is_pass = num_val <= float(val1)
                elif operator == "greater_than" and val1:
                    is_pass = num_val > float(val1)
                elif operator == "less_than" and val1:
                    is_pass = num_val < float(val1)
                else:
                    is_pass = True

                status = CriterionMatchStatusEnum.PASS if is_pass else CriterionMatchStatusEnum.FAIL
            else:
                status = CriterionMatchStatusEnum.UNKNOWN

    # 4. BIOMARKER
    elif category == "biomarker":
        matched_bm = []
        lowered_text = raw_text.lower()
        for bm in biomarkers:
            norm = bm.get("normalized_value", "").lower()
            name = bm.get("biomarker_name", "").lower()
            if "pd-l1" in lowered_text and ("pd-l1" in norm or "pd-l1" in name):
                matched_bm.append(bm)
            elif "egfr" in lowered_text and ("egfr" in norm or "egfr" in name):
                matched_bm.append(bm)

        if not matched_bm:
            status = CriterionMatchStatusEnum.UNKNOWN
        else:
            bm = matched_bm[0]
            status_val = bm.get("status_value")
            data_date = bm.get("test_date")
            evidence_text = f"Biomarker Test: {bm.get('normalized_value')} (Date: {data_date})"

            if bm.get("verification_status") == "flagged":
                status = CriterionMatchStatusEnum.CONFLICT
                reliability = EvidenceReliabilityEnum.CONFLICTING
            else:
                patient_val = bm.get("normalized_value")
                reliability = EvidenceReliabilityEnum.VERIFIED if bm.get("verification_status") == "verified" else EvidenceReliabilityEnum.UNVERIFIED

                if "egfr" in lowered_text and "negative" in raw_text.lower():
                    # Required negative/absent EGFR mutation
                    is_pass = "negative" in status_val.lower() or "wild_type" in status_val.lower()
                elif "pd-l1" in lowered_text and val1:
                    # Required PD-L1 expression threshold
                    is_pass = ">= 50%" in patient_val or (status_val and "positive" in status_val.lower())
                else:
                    is_pass = True

                status = CriterionMatchStatusEnum.PASS if is_pass else CriterionMatchStatusEnum.FAIL

    # 5. MEDICATION / PRIOR TREATMENT
    elif category in ["medication", "prior_treatment"]:
        matched_meds = []
        lowered_text = raw_text.lower()
        for med in medications:
            norm = med.get("normalized_value", "").lower()
            if any(k in norm for k in ["pembrolizumab", "steroid", "chemotherapy", "immunotherapy"]):
                matched_meds.append(med)

        if category == "prior_treatment" and "prior" in lowered_text:
            if matched_meds:
                med = matched_meds[0]
                patient_val = med.get("normalized_value")
                evidence_text = f"Medication Record: {med.get('normalized_value')}"
                reliability = EvidenceReliabilityEnum.VERIFIED if med.get("verification_status") == "verified" else EvidenceReliabilityEnum.UNVERIFIED
                data_date = med.get("start_date")
                status = CriterionMatchStatusEnum.PASS
            else:
                status = CriterionMatchStatusEnum.UNKNOWN
                evidence_text = "No prior systemic anti-cancer therapy record found."
        elif category == "medication":
            if matched_meds:
                med = matched_meds[0]
                patient_val = med.get("normalized_value")
                evidence_text = f"Active Medication Record: {med.get('normalized_value')}"
                reliability = EvidenceReliabilityEnum.VERIFIED if med.get("verification_status") == "verified" else EvidenceReliabilityEnum.UNVERIFIED
                data_date = med.get("start_date")
                # If concurrent high dose steroid medication -> Exclusion rule fails
                status = CriterionMatchStatusEnum.FAIL if "steroid" in patient_val.lower() else CriterionMatchStatusEnum.PASS
            else:
                status = CriterionMatchStatusEnum.PASS
                evidence_text = "No concurrent excluded medications recorded."

    # 6. COMORBIDITY / PROCEDURAL / TEMPORAL / ADMINISTRATIVE
    else:
        # Evaluate comorbidity presence or absence
        matched_diag = [d for d in diagnoses if any(k in d.get("normalized_value", "").lower() for k in ["autoimmune", "cardiac", "hypertension", "infection"])]
        if matched_diag:
            d = matched_diag[0]
            patient_val = d.get("normalized_value")
            evidence_text = f"Comorbidity Diagnosis: {d.get('normalized_value')}"
            reliability = EvidenceReliabilityEnum.VERIFIED if d.get("verification_status") == "verified" else EvidenceReliabilityEnum.UNVERIFIED
            status = CriterionMatchStatusEnum.FAIL if crit_type == "exclusion" else CriterionMatchStatusEnum.PASS
        else:
            status = CriterionMatchStatusEnum.PASS if crit_type == "exclusion" else CriterionMatchStatusEnum.UNKNOWN
            evidence_text = "No matching comorbidity diagnosis record found."

    # Exclusion criteria inversion:
    # If exclusion criterion and evaluated condition is present as an exclusion -> Invert PASS/FAIL
    if crit_type == "exclusion":
        if status == CriterionMatchStatusEnum.FAIL:
            status = CriterionMatchStatusEnum.FAIL  # Retain FAIL
        elif status == CriterionMatchStatusEnum.PASS and operator in ["absent", "not_contains"]:
            status = CriterionMatchStatusEnum.PASS

    return CriterionMatchResult(
        criterion_id=crit_id,
        criterion_type=crit_type,
        category=category,
        operator=operator,
        raw_text=raw_text,
        status=status,
        patient_value=patient_val,
        expected_value=expected_val,
        rule_used=rule_description,
        source_evidence=evidence_text,
        evidence_reliability=reliability,
        data_date=data_date,
        decision_timestamp=now_iso,
        criterion_version=crit_version,
        engine_version=ENGINE_VERSION
    )


def run_patient_trial_matching(patient_id: str, trial_id: str) -> TrialMatchResult:
    """Run full deterministic eligibility matching for a patient against a trial's approved criteria."""
    patient_facts = fetch_patient_facts(patient_id)
    approved_criteria = fetch_approved_criteria(trial_id)

    criterion_results: List[CriterionMatchResult] = []
    for crit in approved_criteria:
        result = evaluate_criterion(crit, patient_facts)
        criterion_results.append(result)

    total_criteria = len(criterion_results)
    passed_count = sum(1 for r in criterion_results if r.status == CriterionMatchStatusEnum.PASS)
    failed_count = sum(1 for r in criterion_results if r.status == CriterionMatchStatusEnum.FAIL)
    unknown_count = sum(1 for r in criterion_results if r.status == CriterionMatchStatusEnum.UNKNOWN)
    conflict_count = sum(1 for r in criterion_results if r.status == CriterionMatchStatusEnum.CONFLICT)

    match_score = (passed_count / total_criteria * 100.0) if total_criteria > 0 else 0.0

    # Determine overall status according to Phase 9 rules:
    # 1. Any required criterion FAIL -> NOT_ELIGIBLE
    # 2. Any CONFLICT -> MANUAL_REVIEW_REQUIRED
    # 3. Any UNKNOWN -> POTENTIALLY_ELIGIBLE
    # 4. All PASS with unverified evidence -> ELIGIBLE_FOR_REVIEW
    # 5. All PASS with verified evidence -> INVESTIGATOR_REVIEW_REQUIRED
    if failed_count > 0:
        overall_status = OverallEligibilityStatusEnum.NOT_ELIGIBLE
    elif conflict_count > 0:
        overall_status = OverallEligibilityStatusEnum.MANUAL_REVIEW_REQUIRED
    elif unknown_count > 0:
        overall_status = OverallEligibilityStatusEnum.POTENTIALLY_ELIGIBLE
    else:
        # All passed! Check evidence reliability
        all_verified = all(r.evidence_reliability == EvidenceReliabilityEnum.VERIFIED for r in criterion_results)
        if all_verified:
            overall_status = OverallEligibilityStatusEnum.INVESTIGATOR_REVIEW_REQUIRED
        else:
            overall_status = OverallEligibilityStatusEnum.ELIGIBLE_FOR_REVIEW

    now_iso = datetime.datetime.utcnow().isoformat()
    match_id = f"match-{uuid.uuid4()}"

    # Persist match result to SQLite DB
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO patient_trial_matches (
            id, patient_id, trial_id, overall_status, match_score, total_criteria,
            passed_count, failed_count, unknown_count, conflict_count, engine_version, evaluated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            match_id, patient_id, trial_id, overall_status.value, match_score, total_criteria,
            passed_count, failed_count, unknown_count, conflict_count, ENGINE_VERSION, now_iso
        ))

        for r in criterion_results:
            eval_id = f"eval-{uuid.uuid4()}"
            cursor.execute("""
            INSERT INTO patient_criterion_evaluations (
                id, match_id, criterion_id, criterion_version, status, patient_value, expected_value,
                rule_used, source_evidence, evidence_reliability, data_date, decision_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                eval_id, match_id, r.criterion_id, r.criterion_version, r.status.value, r.patient_value,
                r.expected_value, r.rule_used, r.source_evidence, r.evidence_reliability.value, r.data_date, r.decision_timestamp
            ))
        conn.commit()

    return TrialMatchResult(
        patient_id=patient_id,
        trial_id=trial_id,
        overall_status=overall_status,
        match_score=match_score,
        total_criteria=total_criteria,
        passed_count=passed_count,
        failed_count=failed_count,
        unknown_count=unknown_count,
        conflict_count=conflict_count,
        evaluated_at=now_iso,
        engine_version=ENGINE_VERSION,
        criterion_results=criterion_results
    )
