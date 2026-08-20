import re
import uuid
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from app.core.db import get_db_connection, init_db
from app.schemas.criteria import (
    StructuredCriterion,
    CriterionTypeEnum,
    CriterionCategoryEnum,
    CriterionOperatorEnum,
    ApprovalStatusEnum,
    CriterionCreateRequest,
    CriterionUpdateRequest
)

logger = logging.getLogger("clinical_trial_assistant")

def classify_criterion(text: str) -> Tuple[CriterionCategoryEnum, float]:
    """Classify criterion into one of the 11 domain categories with confidence score."""
    lowered = text.lower()
    
    # 1. Demographic
    if any(term in lowered for term in ["age", "years old", "between 18 and", "gender", "female", "male", "adult"]):
        return CriterionCategoryEnum.DEMOGRAPHIC, 0.96
    
    # 2. Stage
    if any(term in lowered for term in ["stage iv", "stage 4", "stage iii", "metastatic", "advanced stage"]):
        return CriterionCategoryEnum.STAGE, 0.98

    # 3. Prior Treatment (Check before biomarker so 'prior anti-pd-1 therapy' is prior_treatment)
    if any(term in lowered for term in ["prior anti-", "prior pd-", "prior therapy", "received prior", "past treatment", "pre-treated"]):
        return CriterionCategoryEnum.PRIOR_TREATMENT, 0.96

    # 4. Biomarker
    if any(term in lowered for term in ["pd-l1", "tps", "egfr", "alk", "kras", "ros1", "mutation", "translocation", "expression", "tmb"]):
        return CriterionCategoryEnum.BIOMARKER, 0.97

    # 5. Laboratory
    if any(term in lowered for term in ["anc", "neutrophil", "platelet", "hemoglobin", "creatinine", "alt", "ast", "bilirubin", "10^9", "10*3", "x10^9", "mg/dl"]):
        return CriterionCategoryEnum.LABORATORY, 0.96

    # 6. Procedural
    if any(term in lowered for term in ["surgery", "biopsy", "resection", "transplant", "procedure"]):
        return CriterionCategoryEnum.PROCEDURAL, 0.95

    # 7. Medication
    if any(term in lowered for term in ["steroid", "medication", "immunosuppressive therapy", "chemotherapy", "drug"]):
        return CriterionCategoryEnum.MEDICATION, 0.94

    # 8. Comorbidity
    if any(term in lowered for term in ["autoimmune disease", "cardiac", "hypertension", "diabetes", "active infection", "cns metastases"]):
        return CriterionCategoryEnum.COMORBIDITY, 0.95

    # 9. Temporal
    if any(term in lowered for term in ["evaluation window", "within 14 days", "within 30 days", "within 6 months"]):
        return CriterionCategoryEnum.TEMPORAL, 0.95

    # 10. Administrative
    if any(term in lowered for term in ["informed consent", "willingness", "compliance", "ecog", "protocol"]):
        return CriterionCategoryEnum.ADMINISTRATIVE, 0.92

    # 11. Diagnosis (Default fallback for clinical conditions)
    return CriterionCategoryEnum.DIAGNOSIS, 0.90


def extract_operator_and_values(text: str) -> Tuple[CriterionOperatorEnum, Optional[str], Optional[str], Optional[str]]:
    """Extract operator, primary value, secondary value, and unit from criterion text."""
    lowered = text.lower()
    
    # Range / Between (e.g. "age between 18 and 75", "18-80 years")
    range_match = re.search(r'between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)', lowered)
    if range_match:
        unit = "years" if "age" in lowered or "year" in lowered else None
        return CriterionOperatorEnum.BETWEEN, range_match.group(1), range_match.group(2), unit

    range_dash = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', lowered)
    if range_dash and any(k in lowered for k in ["age", "years", "range"]):
        return CriterionOperatorEnum.BETWEEN, range_dash.group(1), range_dash.group(2), "years"

    # Greater than or equal (e.g., ">= 18", "age >= 18", "at least 18", ">= 1.5")
    gte_match = re.search(r'(?:>=|at least|greater than or equal to)\s*(\d+(?:\.\d+)?)', lowered)
    if gte_match:
        val = gte_match.group(1)
        unit = "years" if "age" in lowered else ("10*3/uL" if "anc" in lowered or "10^9" in lowered else ("%" if "%" in text else None))
        return CriterionOperatorEnum.GREATER_THAN_OR_EQUAL, val, None, unit

    # Less than or equal (e.g., "<= 80", "<= 2.0")
    lte_match = re.search(r'(?:<=|no more than|less than or equal to)\s*(\d+(?:\.\d+)?)', lowered)
    if lte_match:
        val = lte_match.group(1)
        unit = "years" if "age" in lowered else ("%" if "%" in text else None)
        return CriterionOperatorEnum.LESS_THAN_OR_EQUAL, val, None, unit

    # Greater than (e.g. "> 50%")
    gt_match = re.search(r'>\s*(\d+(?:\.\d+)?)', lowered)
    if gt_match:
        val = gt_match.group(1)
        unit = "%" if "%" in text else None
        return CriterionOperatorEnum.GREATER_THAN, val, None, unit

    # Less than (e.g. "< 10")
    lt_match = re.search(r'<\s*(\d+(?:\.\d+)?)', lowered)
    if lt_match:
        val = lt_match.group(1)
        unit = "%" if "%" in text else None
        return CriterionOperatorEnum.LESS_THAN, val, None, unit

    # Absent / Not contains
    if any(k in lowered for k in ["no prior", "absence of", "without", "negative", "no active"]):
        return CriterionOperatorEnum.ABSENT, None, None, None

    # Exists / Contains
    if any(k in lowered for k in ["confirmed", "positive", "presence of", "must have"]):
        return CriterionOperatorEnum.EXISTS, None, None, None

    return CriterionOperatorEnum.CONTAINS, None, None, None


def extract_temporal_window(text: str) -> Optional[str]:
    """Extract temporal expressions/windows from text."""
    lowered = text.lower()
    match = re.search(r'(within\s+\d+\s+(?:days|weeks|months|years)(?:\s+prior to\s+[a-z\s]+)?)', lowered)
    if match:
        return match.group(1)
    if "prior" in lowered:
        return "prior to enrollment"
    return None


def extract_negation(text: str) -> bool:
    """Detect if criterion involves negation."""
    lowered = text.lower()
    negation_keywords = ["no ", "not ", "none", "without", "absence of", "negative", "denies", "never"]
    return any(k in lowered for k in negation_keywords)


def parse_protocol_text_into_criteria(trial_id: str, protocol_text: str) -> List[StructuredCriterion]:
    """Parse unstructured eligibility criteria protocol text into validated structured criteria nodes."""
    lines = [line.strip() for line in protocol_text.split("\n") if line.strip()]
    
    current_type = CriterionTypeEnum.INCLUSION
    structured_list: List[StructuredCriterion] = []
    char_offset = 0

    for line in lines:
        line_len = len(line)
        lowered = line.lower()
        
        if "inclusion criteria" in lowered:
            current_type = CriterionTypeEnum.INCLUSION
            char_offset += line_len + 1
            continue
        elif "exclusion criteria" in lowered:
            current_type = CriterionTypeEnum.EXCLUSION
            char_offset += line_len + 1
            continue

        # Skip headers or empty bullet points
        if len(line) < 3:
            char_offset += line_len + 1
            continue

        # Clean bullet numbers
        clean_text = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
        if not clean_text:
            char_offset += line_len + 1
            continue

        category, confidence = classify_criterion(clean_text)
        operator, val1, val2, unit = extract_operator_and_values(clean_text)
        temp_window = extract_temporal_window(clean_text)
        is_neg = extract_negation(clean_text)
        
        # If type is exclusion, implicitly negate or mark operator as absent if appropriate
        if current_type == CriterionTypeEnum.EXCLUSION and operator == CriterionOperatorEnum.EXISTS:
            operator = CriterionOperatorEnum.ABSENT
            is_neg = True

        criterion = StructuredCriterion(
            id=f"crit-{uuid.uuid4()}",
            trial_id=trial_id,
            criterion_type=current_type,
            category=category,
            operator=operator,
            value_primary=val1,
            value_secondary=val2,
            unit=unit,
            temporal_window=temp_window,
            is_negated=is_neg,
            logic_group="AND",
            raw_text=clean_text,
            page_number=1,
            start_char=char_offset,
            end_char=char_offset + line_len,
            classification_confidence=confidence,
            approval_status=ApprovalStatusEnum.PENDING,
            version=1
        )
        structured_list.append(criterion)
        char_offset += line_len + 1

    return structured_list


def store_parsed_criteria(trial_id: str, criteria: List[StructuredCriterion]) -> List[Dict[str, Any]]:
    """Persist structured criteria to the database."""
    init_db()
    records = []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Clear existing pending criteria for clean re-parse if needed
        cursor.execute("DELETE FROM trial_criteria WHERE trial_id = ? AND approval_status = 'pending';", (trial_id,))
        
        for c in criteria:
            if not c.id:
                c.id = f"crit-{uuid.uuid4()}"

            cursor.execute("""
            INSERT INTO trial_criteria (
                id, trial_id, criterion_type, category, operator, value_primary, value_secondary,
                unit, temporal_window, is_negated, logic_group, raw_text, page_number, start_char, end_char,
                classification_confidence, approval_status, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                c.id, c.trial_id, c.criterion_type.value, c.category.value, c.operator.value,
                c.value_primary, c.value_secondary, c.unit, c.temporal_window,
                1 if c.is_negated else 0, c.logic_group, c.raw_text, c.page_number,
                c.start_char, c.end_char, c.classification_confidence, c.approval_status.value, c.version
            ))
            
            # Insert initial version snapshot
            snapshot = json.dumps(c.model_dump(mode="json"))
            cursor.execute("""
            INSERT INTO trial_criteria_versions (id, criterion_id, version_number, snapshot_json, change_summary)
            VALUES (?, ?, 1, ?, 'Initial parsed criterion');
            """, (f"v1-{c.id}", c.id, snapshot))
            
            records.append(c.model_dump(mode="json"))
        conn.commit()

    return records


def get_trial_criteria(trial_id: str, approved_only: bool = False) -> List[Dict[str, Any]]:
    """Fetch criteria for a trial."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if approved_only:
            cursor.execute("SELECT * FROM trial_criteria WHERE trial_id = ? AND approval_status = 'approved' ORDER BY criterion_type, created_at;", (trial_id,))
        else:
            cursor.execute("SELECT * FROM trial_criteria WHERE trial_id = ? ORDER BY criterion_type, created_at;", (trial_id,))
            
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_criterion(criterion_id: str, update_req: CriterionUpdateRequest, user_id: str = "system") -> Dict[str, Any]:
    """Edit criterion and create a new version snapshot."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trial_criteria WHERE id = ?;", (criterion_id,))
        existing = cursor.fetchone()
        if not existing:
            raise ValueError(f"Criterion with ID {criterion_id} not found.")

        current = dict(existing)
        new_version = current["version"] + 1
        
        category = update_req.category.value if update_req.category else current["category"]
        operator = update_req.operator.value if update_req.operator else current["operator"]
        val1 = update_req.value_primary if update_req.value_primary is not None else current["value_primary"]
        val2 = update_req.value_secondary if update_req.value_secondary is not None else current["value_secondary"]
        unit = update_req.unit if update_req.unit is not None else current["unit"]
        temp_win = update_req.temporal_window if update_req.temporal_window is not None else current["temporal_window"]
        is_neg = 1 if update_req.is_negated else 0 if update_req.is_negated is False else current["is_negated"]
        logic_grp = update_req.logic_group if update_req.logic_group else current["logic_group"]
        raw_text = update_req.raw_text if update_req.raw_text else current["raw_text"]

        cursor.execute("""
        UPDATE trial_criteria
        SET category = ?, operator = ?, value_primary = ?, value_secondary = ?, unit = ?,
            temporal_window = ?, is_negated = ?, logic_group = ?, raw_text = ?, version = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (category, operator, val1, val2, unit, temp_win, is_neg, logic_grp, raw_text, new_version, criterion_id))

        # Fetch updated record
        cursor.execute("SELECT * FROM trial_criteria WHERE id = ?;", (criterion_id,))
        updated_dict = dict(cursor.fetchone())
        
        # Store version snapshot
        snapshot_json = json.dumps(updated_dict)
        cursor.execute("""
        INSERT INTO trial_criteria_versions (id, criterion_id, version_number, snapshot_json, edited_by, change_summary)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (f"v{new_version}-{criterion_id}", criterion_id, new_version, snapshot_json, user_id, update_req.change_summary))

        conn.commit()
        return updated_dict


def set_criterion_approval(criterion_id: str, status: ApprovalStatusEnum, user_id: str = "system") -> Dict[str, Any]:
    """Approve or reject a criterion."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE trial_criteria SET approval_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (status.value, criterion_id))
        cursor.execute("SELECT * FROM trial_criteria WHERE id = ?;", (criterion_id,))
        updated = cursor.fetchone()
        conn.commit()
        if not updated:
            raise ValueError(f"Criterion {criterion_id} not found.")
        return dict(updated)
