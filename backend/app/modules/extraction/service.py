import uuid
import re
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.core.db import get_db_connection, init_db
from app.schemas.extraction import (
    ExtractedFact,
    ClinicalCategoryEnum,
    FactReviewStatusEnum,
    ExtractionPipelineResult
)

logger = logging.getLogger("clinical_trial_assistant")

AI_PROVIDER = "mock"
AI_MODEL = "mock-v1"
PROMPT_VERSION = "v1.0"


def detect_negation(snippet: str) -> bool:
    """Detect clinical negation cues in text snippet."""
    negation_patterns = [
        r"\bno\s+history\s+of\b",
        r"\bdenies\b",
        r"\bno\b",
        r"\bnegative\s+for\b",
        r"\bwithout\b",
        r"\babsent\b",
        r"\bnever\b"
    ]
    lowered = snippet.lower()
    return any(re.search(pat, lowered) for pat in negation_patterns)


def normalize_unit(raw_unit: str) -> str:
    """Normalize raw laboratory units to canonical representation."""
    if not raw_unit:
        return ""
    u = raw_unit.strip().lower()
    if any(k in u for k in ["10^9", "10*3", "/ul", "x10^9"]):
        return "10*3/uL"
    elif "%" in u or "percent" in u:
        return "%"
    elif "mg/dl" in u:
        return "mg/dL"
    return raw_unit


def extract_clinical_facts_from_text(patient_id: str, document_id: str, document_text: str) -> List[ExtractedFact]:
    """Execute multi-stage fact extraction pipeline over document text."""
    now_iso = datetime.datetime.utcnow().isoformat()
    lines = document_text.splitlines()
    facts: List[ExtractedFact] = []
    
    char_offset = 0
    for page_num, line in enumerate(lines, start=1):
        line_len = len(line)
        line_low = line.lower()

        # 1. DIAGNOSIS & DISEASE STAGE
        if "nsclc" in line_low or "lung cancer" in line_low or "carcinoma" in line_low or "stage" in line_low:
            is_neg = detect_negation(line)
            stage_match = re.search(r"stage\s+(iv|iii|ii|i)", line_low)
            stage_str = f" (Stage {stage_match.group(1).upper()})" if stage_match else ""
            
            facts.append(
                ExtractedFact(
                    id=f"fact-{uuid.uuid4()}",
                    patient_id=patient_id,
                    document_id=document_id,
                    category=ClinicalCategoryEnum.DIAGNOSIS,
                    raw_text=line.strip(),
                    canonical_label=f"Non-Small Cell Lung Cancer{stage_str}",
                    mapping_method="snomed_ct_mapping",
                    mapping_confidence=0.95,
                    is_negated=is_neg,
                    source_page=page_num,
                    start_char=char_offset,
                    end_char=char_offset + line_len,
                    ai_provider=AI_PROVIDER,
                    ai_model=AI_MODEL,
                    prompt_version=PROMPT_VERSION
                )
            )

        # 2. LABORATORY & RECENT / OLD LAB TEMPORAL RECOGNITION
        if "anc" in line_low or "neutrophil" in line_low or "creatinine" in line_low:
            is_neg = detect_negation(line)
            # Find numeric value after lab keyword or colon
            num_match = re.search(r"(?:anc|count|neutrophil|creatinine|\))\s*(\d+\.?\d*)", line_low)
            if not num_match:
                num_match = re.search(r":\s*(\d+\.?\d*)", line_low)
            num_val = float(num_match.group(1)) if num_match else None
            
            # Detect temporal recency / stale date
            is_stale_lab = "2025" in line or "old" in line_low or "prior" in line_low
            lab_date = "2025-10-01" if is_stale_lab else "2026-08-01"
            
            unit_match = re.search(r"(10\^9/L|10\*3/uL|mg/dL|%)", line)
            raw_u = unit_match.group(1) if unit_match else "10*3/uL"
            norm_u = normalize_unit(raw_u)

            facts.append(
                ExtractedFact(
                    id=f"fact-{uuid.uuid4()}",
                    patient_id=patient_id,
                    document_id=document_id,
                    category=ClinicalCategoryEnum.LAB,
                    raw_text=line.strip(),
                    canonical_label=f"Absolute Neutrophil Count: {num_val or ''} {norm_u}".strip(),
                    mapping_method="loinc_lab_mapping",
                    mapping_confidence=0.94,
                    is_negated=is_neg,
                    temporal_expression="stale_historical" if is_stale_lab else "current_recent",
                    data_date=lab_date,
                    is_stale=is_stale_lab,
                    numeric_value=num_val,
                    raw_unit=raw_u,
                    normalized_unit=norm_u,
                    source_page=page_num,
                    start_char=char_offset,
                    end_char=char_offset + line_len,
                    ai_provider=AI_PROVIDER,
                    ai_model=AI_MODEL,
                    prompt_version=PROMPT_VERSION
                )
            )

        # 3. BIOMARKERS (Positive vs Negative EGFR / PD-L1)
        if "pd-l1" in line_low or "egfr" in line_low or "alk" in line_low:
            is_neg = detect_negation(line) or "negative" in line_low or "wild" in line_low
            status_str = "NEGATIVE (WILD_TYPE)" if is_neg else "POSITIVE (MUTATED/EXPRESSED)"
            name = "PD-L1 Expression" if "pd-l1" in line_low else "EGFR Mutation"

            facts.append(
                ExtractedFact(
                    id=f"fact-{uuid.uuid4()}",
                    patient_id=patient_id,
                    document_id=document_id,
                    category=ClinicalCategoryEnum.BIOMARKER,
                    raw_text=line.strip(),
                    canonical_label=f"{name}: {status_str}",
                    mapping_method="biomarker_canonical_mapping",
                    mapping_confidence=0.96,
                    is_negated=is_neg,
                    source_page=page_num,
                    start_char=char_offset,
                    end_char=char_offset + line_len,
                    ai_provider=AI_PROVIDER,
                    ai_model=AI_MODEL,
                    prompt_version=PROMPT_VERSION
                )
            )

        # 4. MEDICATIONS & PREVIOUS TREATMENTS
        if any(k in line_low for k in ["pembrolizumab", "chemotherapy", "steroid", "cisplatin", "immunotherapy"]):
            is_neg = detect_negation(line)
            is_prev = "prior" in line_low or "previous" in line_low or "history" in line_low
            category = ClinicalCategoryEnum.PREVIOUS_TREATMENT if is_prev else ClinicalCategoryEnum.MEDICATION

            facts.append(
                ExtractedFact(
                    id=f"fact-{uuid.uuid4()}",
                    patient_id=patient_id,
                    document_id=document_id,
                    category=category,
                    raw_text=line.strip(),
                    canonical_label=f"Medication Record: {line.strip()}",
                    mapping_method="rxnorm_mapping",
                    mapping_confidence=0.91,
                    is_negated=is_neg,
                    temporal_expression="historical" if is_prev else "current",
                    source_page=page_num,
                    start_char=char_offset,
                    end_char=char_offset + line_len,
                    ai_provider=AI_PROVIDER,
                    ai_model=AI_MODEL,
                    prompt_version=PROMPT_VERSION
                )
            )

        # 5. COMORBIDITY & NEGATED HISTORY
        if any(k in line_low for k in ["hypertension", "cardiac", "diabetes", "asthma", "autoimmune"]):
            is_neg = detect_negation(line)
            facts.append(
                ExtractedFact(
                    id=f"fact-{uuid.uuid4()}",
                    patient_id=patient_id,
                    document_id=document_id,
                    category=ClinicalCategoryEnum.COMORBIDITY,
                    raw_text=line.strip(),
                    canonical_label=f"Comorbidity: {line.strip()}",
                    mapping_method="snomed_ct_mapping",
                    mapping_confidence=0.93,
                    is_negated=is_neg,
                    source_page=page_num,
                    start_char=char_offset,
                    end_char=char_offset + line_len,
                    ai_provider=AI_PROVIDER,
                    ai_model=AI_MODEL,
                    prompt_version=PROMPT_VERSION
                )
            )

        char_offset += line_len + 1

    return facts


def detect_and_store_conflicts(patient_id: str, new_facts: List[ExtractedFact], conn) -> int:
    """Detect conflicts between new facts and existing patient facts without overwriting."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM extracted_clinical_facts WHERE patient_id = ?;", (patient_id,))
    existing_rows = cursor.fetchall()
    existing_facts = [dict(r) for r in existing_rows]

    conflict_count = 0
    for new_f in new_facts:
        for old_f in existing_facts:
            # Check for biomarker contradiction (e.g. POSITIVE vs NEGATIVE for same biomarker)
            if new_f.category == old_f["category"] and "EGFR" in new_f.raw_text and "EGFR" in old_f["raw_text"]:
                if new_f.is_negated != bool(old_f["is_negated"]):
                    new_f.has_conflict = True
                    new_f.conflict_details = f"Contradictory EGFR biomarker result with existing record '{old_f['canonical_label']}'"
                    conflict_count += 1
                    
                    conflict_id = f"conf-{uuid.uuid4()}"
                    cursor.execute("""
                    INSERT INTO fact_conflicts (id, patient_id, category, existing_fact_id, new_fact_id, conflict_description, resolution_status)
                    VALUES (?, ?, ?, ?, ?, ?, 'unresolved');
                    """, (conflict_id, patient_id, new_f.category.value, old_f["id"], new_f.id, new_f.conflict_details))

    return conflict_count


def process_document_extraction(patient_id: str, document_id: str, document_text: str) -> ExtractionPipelineResult:
    """Run full extraction pipeline and save facts & conflicts to SQLite database."""
    extracted_facts = extract_clinical_facts_from_text(patient_id, document_id, document_text)
    now_iso = datetime.datetime.utcnow().isoformat()

    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        conflict_count = detect_and_store_conflicts(patient_id, extracted_facts, conn)

        for fact in extracted_facts:
            cursor.execute("""
            INSERT OR REPLACE INTO extracted_clinical_facts (
                id, patient_id, document_id, category, raw_text, canonical_label, mapping_method,
                mapping_confidence, is_negated, temporal_expression, data_date, is_stale,
                numeric_value, raw_unit, normalized_unit, source_page, start_char, end_char,
                ai_provider, ai_model, prompt_version, review_status, has_conflict, conflict_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                fact.id, fact.patient_id, fact.document_id, fact.category.value, fact.raw_text,
                fact.canonical_label, fact.mapping_method, fact.mapping_confidence, int(fact.is_negated),
                fact.temporal_expression, fact.data_date, int(fact.is_stale), fact.numeric_value,
                fact.raw_unit, fact.normalized_unit, fact.source_page, fact.start_char, fact.end_char,
                fact.ai_provider, fact.ai_model, fact.prompt_version, fact.review_status.value,
                int(fact.has_conflict), fact.conflict_details
            ))
        conn.commit()

    return ExtractionPipelineResult(
        document_id=document_id,
        patient_id=patient_id,
        extracted_facts=extracted_facts,
        conflict_count=conflict_count,
        processed_at=now_iso
    )


def review_fact(fact_id: str, review_status: str, edited_canonical_label: Optional[str] = None) -> Dict[str, Any]:
    """Approve, edit, or reject an extracted clinical fact."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if edited_canonical_label:
            cursor.execute(
                "UPDATE extracted_clinical_facts SET review_status = ?, canonical_label = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (review_status, edited_canonical_label, fact_id)
            )
        else:
            cursor.execute(
                "UPDATE extracted_clinical_facts SET review_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (review_status, fact_id)
            )
        conn.commit()

        cursor.execute("SELECT * FROM extracted_clinical_facts WHERE id = ?;", (fact_id,))
        row = cursor.fetchone()
        return dict(row) if row else {}
