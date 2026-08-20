from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import json
import re
import os
import io
import logging
from datetime import datetime

logger = logging.getLogger("clinical_trial_assistant")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True

    # Eagerly resolve and set tesseract binary at module load time.
    # This ensures pytesseract works even when PATH hasn't been refreshed in the server's shell.
    _TESSERACT_COMMON_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.path.expandvars("%LOCALAPPDATA%"), r"Programs\Tesseract-OCR\tesseract.exe"),
        r"C:\tesseract\tesseract.exe",
    ]
    _tess_resolved = False
    try:
        pytesseract.get_tesseract_version()
        _tess_resolved = True
        logger.info("[TESSERACT] Found on system PATH")
    except Exception:
        for _p in _TESSERACT_COMMON_PATHS:
            if os.path.exists(_p):
                pytesseract.pytesseract.tesseract_cmd = _p
                try:
                    pytesseract.get_tesseract_version()
                    _tess_resolved = True
                    logger.info(f"[TESSERACT] Resolved binary at startup: {_p}")
                    print(f"[TESSERACT] Resolved binary at startup: {_p}")
                    break
                except Exception:
                    pass
    if not _tess_resolved:
        logger.warning("[TESSERACT] Binary not found at startup — OCR will fail for scanned PDFs")
        print("[TESSERACT] WARNING: Binary not found at startup")

except ImportError:
    PYTESSERACT_AVAILABLE = False

from app.schemas.common import ApiResponse, UserRole
from app.core.security import require_role, AuthenticatedUser
from app.modules.audit.service import log_audit_event
from app.core.db import get_db_connection

router = APIRouter(prefix="/documents", tags=["documents"])

# Allowed Document Categories per requirement
VALID_DOCUMENT_CATEGORIES = [
    "patient_report",
    "lab_report",
    "pathology_report",
    "radiology_report",
    "clinical_note",
    "protocol"
]

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_EXTENSIONS = [".pdf", ".txt"]

class FactApproveRequest(BaseModel):
    approvedFactIds: List[str]

class DocumentRetryRequest(BaseModel):
    forceOcr: Optional[bool] = False

def resolve_tesseract_cmd() -> Optional[str]:
    """Check system PATH and common Windows installation paths for tesseract binary."""
    if not PYTESSERACT_AVAILABLE:
        return None
    try:
        pytesseract.get_tesseract_version()
        return "System PATH"
    except Exception:
        pass

    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        r"C:\tesseract\tesseract.exe"
    ]
    for p in common_paths:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            try:
                pytesseract.get_tesseract_version()
                logger.info(f"Resolved Tesseract OCR binary at: {p}")
                return p
            except Exception:
                pass
    return None

def extract_pages_with_pymupdf(file_bytes: bytes, file_name: str, force_ocr: bool = False) -> List[dict]:
    """
    Extract text page-by-page using PyMuPDF (fitz) with source text span offsets.
    If extracted page text < 20 characters or force_ocr is True, run REAL Tesseract OCR.
    Provides detailed logging and informative warning if system OCR binaries are unconfigured.
    """
    pages = []
    tess_path = resolve_tesseract_cmd()
    
    if file_name.lower().endswith(".pdf") and PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_text = page.get_text() or ""
                
                needs_ocr = force_ocr or len(page_text.strip()) < 20
                ocr_applied = 1 if needs_ocr else 0
                ocr_error = None
                
                if needs_ocr:
                    if PYTESSERACT_AVAILABLE and tess_path:
                        try:
                            # Render PDF page to image pixmap at 150 DPI for OCR
                            pix = page.get_pixmap(dpi=150)
                            img = Image.open(io.BytesIO(pix.tobytes("png")))
                            ocr_text = pytesseract.image_to_string(img)
                            if ocr_text and len(ocr_text.strip()) > 0:
                                page_text = ocr_text
                            else:
                                ocr_error = "Tesseract OCR executed but produced empty text."
                        except Exception as e:
                            ocr_error = f"Tesseract execution error ({type(e).__name__}): {e}"
                            logger.error(f"[OCR ERROR] Failed on page {page_idx + 1} of {file_name}: {ocr_error}")
                    else:
                        ocr_error = "Tesseract binary (tesseract.exe) is not installed or not found on system PATH."
                        logger.error(f"[OCR ERROR] {ocr_error}")

                # If page_text is empty and OCR error occurred, populate informative error status
                if len(page_text.strip()) == 0 and ocr_error:
                    page_text = f"[OCR System Warning: Scanned page text could not be extracted. Cause: {ocr_error}]"

                # Extract text spans & character offsets
                spans = []
                words = page.get_text("words") if not needs_ocr else []
                if words:
                    for w in words[:15]:
                        spans.append({"text": w[4], "bbox": [w[0], w[1], w[2], w[3]]})
                else:
                    spans.append({"text": page_text[:60] if page_text else "", "bbox": [0, 0, 100, 20]})

                pages.append({
                    "page_number": page_idx + 1,
                    "page_text": page_text,
                    "char_count": len(page_text),
                    "source_spans": spans,
                    "ocr_applied": ocr_applied
                })
            doc.close()
            if pages:
                return pages
        except Exception as e:
            logger.error(f"[PyMuPDF ERROR] Failed to parse PDF {file_name}: {type(e).__name__} - {e}")

    # Non-PDF or PyMuPDF fallback: read actual file bytes
    raw_str = file_bytes.decode("utf-8", errors="ignore")
    needs_ocr = force_ocr or len(raw_str.strip()) < 20
    ocr_flag = 1 if needs_ocr else 0
    fallback_ocr_error = None

    if needs_ocr:
        if PYTESSERACT_AVAILABLE and tess_path:
            try:
                img = Image.open(io.BytesIO(file_bytes))
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text and len(ocr_text.strip()) > 0:
                    raw_str = ocr_text
                else:
                    fallback_ocr_error = "Tesseract OCR produced empty text."
            except Exception as e:
                fallback_ocr_error = f"Tesseract error ({type(e).__name__}): {e}"
                logger.error(f"[OCR FALLBACK ERROR] {fallback_ocr_error}")
        else:
            fallback_ocr_error = "Tesseract binary (tesseract.exe) is not installed or not found on system PATH."
            logger.error(f"[OCR FALLBACK ERROR] {fallback_ocr_error}")

    if len(raw_str.strip()) == 0 and fallback_ocr_error:
        raw_str = f"[OCR System Warning: File text could not be extracted. Cause: {fallback_ocr_error}]"

    spans = [{"text": raw_str[:60] if raw_str else "", "bbox": [0, 0, 100, 20]}]
    pages.append({
        "page_number": 1,
        "page_text": raw_str,
        "char_count": len(raw_str),
        "source_spans": spans,
        "ocr_applied": ocr_flag
    })
    return pages

async def extract_clinical_facts_from_text(raw_text: str, page_number: int = 1) -> List[dict]:
    """Extract clinical facts using configured AI provider (Gemini API) with regex fallback."""
    facts = []

    # 1. Attempt AI Provider (Gemini API) extraction
    try:
        from app.ai.base import get_ai_provider
        provider = get_ai_provider()
        logger.info(f"[AI EXTRACTION] Invoking AI Provider ({provider.__class__.__name__}) for page {page_number} (Length: {len(raw_text)})")
        ai_res = await provider.extract_patient_facts(raw_text)
        
        if ai_res and ai_res.facts:
            logger.info(f"[AI EXTRACTION SUCCESS] AI Provider returned {len(ai_res.facts)} facts for page {page_number}")
            for item in ai_res.facts:
                if isinstance(item, dict):
                    f_type = str(item.get("factType") or item.get("type") or "condition").lower()
                    if f_type not in ["condition", "lab", "biomarker", "medication", "procedure", "observation"]:
                        f_type = "condition"

                    raw_v = item.get("rawValue") or item.get("raw_text") or item.get("entity") or ""
                    norm_v = item.get("normalizedValue") or item.get("canonical_label") or item.get("entity") or raw_v
                    code_v = item.get("code") or "N/A"
                    conf_v = float(item.get("confidenceScore") or item.get("confidence") or 0.95)
                    neg_v = 1 if item.get("isNegated") else 0
                    temp_v = str(item.get("temporality") or "current")

                    facts.append({
                        "id": str(uuid.uuid4()),
                        "factType": f_type,
                        "rawValue": raw_v,
                        "normalizedValue": norm_v,
                        "code": code_v,
                        "confidenceScore": conf_v,
                        "isNegated": neg_v,
                        "temporality": temp_v,
                        "pageNumber": page_number,
                        "verificationStatus": "unverified"
                    })
    except Exception as e:
        logger.error(f"[AI EXTRACTION EXCEPTION] Gemini API extraction failed: {type(e).__name__} - {e}")
        print(f"[AI EXTRACTION EXCEPTION] Gemini API extraction failed: {type(e).__name__} - {e}")

    # 2. Regex pattern extraction (as fallback or addition if 0 facts returned)
    if not facts:
        diag_matches = re.finditer(r"(non-small cell lung cancer|nsclc|adenocarcinoma|melanoma|hypertension|diabetes|asthma|carcinoma|lesion|nodule|mass|effusion|infiltrate|consolidation|opacity)", raw_text, re.IGNORECASE)
        for m in diag_matches:
            match_str = m.group(0)
            start = max(0, m.start() - 30)
            context_window = raw_text[start:m.end() + 20].lower()
            is_negated = 1 if any(neg in context_window for neg in ["no history of", "negative for", "denies", "no evidence of", "without", "clear of"]) else 0
            temporality = "historical" if any(t in context_window for t in ["prior", "history of", "previously", "past"]) else "current"

            facts.append({
                "id": str(uuid.uuid4()),
                "factType": "condition",
                "rawValue": f"Extracted: '{match_str}' in context: '{context_window.strip()}'",
                "normalizedValue": match_str.upper(),
                "code": "254837009" if "lung" in match_str.lower() else "38341003",
                "confidenceScore": 0.96,
                "isNegated": is_negated,
                "temporality": temporality,
                "pageNumber": page_number,
                "verificationStatus": "unverified"
            })

        lab_matches = re.finditer(r"(anc|absolute neutrophil count|wbc|platelets|hemoglobin|creatinine)\s*(?:lab|level|count)?\s*(?:is|=|:)?\s*([\d\.]+)\s*(10\*3/ul|k/ul|g/dl|mg/dl)?", raw_text, re.IGNORECASE)
        for m in lab_matches:
            raw_val = m.group(0)
            lab_name = m.group(1)
            num_val = m.group(2)
            unit = m.group(3) or "10*3/uL"

            facts.append({
                "id": str(uuid.uuid4()),
                "factType": "lab",
                "rawValue": raw_val,
                "normalizedValue": f"{lab_name.upper()}: {num_val} {unit}",
                "code": "26499-4",
                "confidenceScore": 0.98,
                "isNegated": 0,
                "temporality": "current",
                "pageNumber": page_number,
                "verificationStatus": "unverified"
            })

        bio_matches = re.finditer(r"(egfr|pd-l1|alk|kras)\s*(mutation|expression|ihc|tps)?\s*(positive|negative|wild-type|wild type|mutated|\d+%)", raw_text, re.IGNORECASE)
        for m in bio_matches:
            raw_val = m.group(0)
            b_name = m.group(1).upper()
            b_status = m.group(3).upper()

            facts.append({
                "id": str(uuid.uuid4()),
                "factType": "biomarker",
                "rawValue": raw_val,
                "normalizedValue": f"{b_name} Status: {b_status}",
                "code": "8251-1",
                "confidenceScore": 0.94,
                "isNegated": 1 if "NEGATIVE" in b_status or "WILD" in b_status else 0,
                "temporality": "current",
                "pageNumber": page_number,
                "verificationStatus": "unverified"
            })

    return facts

# 1. Upload & Ingest Document API (Strict Validation, PyMuPDF, OCR Fallback & Versioning)
@router.post("/upload", response_model=ApiResponse[dict])
async def upload_document(
    file: UploadFile = File(...),
    patient_id: str = Form(...),
    document_category: str = Form("patient_report"),
    apply_ocr: bool = Form(False),
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    # Validate Document Category
    if document_category not in VALID_DOCUMENT_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document_category '{document_category}'. Must be one of: {', '.join(VALID_DOCUMENT_CATEGORIES)}"
        )

    # Validate File Extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Only .pdf and .txt files are supported."
        )

    # Read File Bytes & Validate File Size
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({file_size} bytes) exceeds maximum limit of 10MB."
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM patients WHERE id = ? OR mrn_synthetic = ?;", (patient_id, patient_id))
    patient = cursor.fetchone()
    if not patient:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    p_id = patient["id"]

    # Check for existing document with same name for versioning
    cursor.execute("SELECT id, version FROM patient_documents WHERE patient_id = ? AND file_name = ?;", (p_id, file.filename))
    existing_doc = cursor.fetchone()

    if existing_doc:
        doc_id = existing_doc["id"]
        doc_version = existing_doc["version"] + 1
        # Insert version history record
        cursor.execute("""
            INSERT INTO document_versions (id, document_id, version_number, file_name, change_summary)
            VALUES (?, ?, ?, ?, 'New file version uploaded');
        """, (str(uuid.uuid4()), doc_id, doc_version, file.filename))
        
        # Clear old pages & facts for re-upload
        cursor.execute("DELETE FROM document_pages WHERE document_id = ?;", (doc_id,))
        cursor.execute("DELETE FROM extracted_facts WHERE document_id = ?;", (doc_id,))
        
        cursor.execute("""
            UPDATE patient_documents
            SET version = ?, file_size_bytes = ?, document_category = ?, processing_status = 'processing'
            WHERE id = ?;
        """, (doc_version, file_size, document_category, doc_id))
    else:
        doc_id = f"doc-{str(uuid.uuid4())[:8]}"
        doc_version = 1
        storage_path = f"supabase://patient_documents/{p_id}/{doc_id}/{file.filename}"
        
        cursor.execute("""
            INSERT INTO patient_documents (
                id, patient_id, file_name, file_type, document_category,
                file_size_bytes, mime_type, file_path, storage_path, page_count,
                ocr_applied, processing_status, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 'processing', 1);
        """, (
            doc_id, p_id, file.filename, ext.replace(".", ""), document_category,
            file_size, file.content_type or "application/pdf", f"/uploads/{file.filename}",
            storage_path
        ))
        
        # Insert version 1 history
        cursor.execute("""
            INSERT INTO document_versions (id, document_id, version_number, file_name, change_summary)
            VALUES (?, ?, 1, ?, 'Initial document upload');
        """, (str(uuid.uuid4()), doc_id, file.filename))

    # Save original file bytes to disk for genuine retry & OCR reprocessing
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    disk_file_path = os.path.join(uploads_dir, f"{doc_id}_{file.filename}")
    with open(disk_file_path, "wb") as f_out:
        f_out.write(content)

    # Extract Pages with PyMuPDF & Tesseract fallback
    pages = extract_pages_with_pymupdf(content, file.filename, force_ocr=apply_ocr)
    ocr_any = 0
    all_facts = []

    for p in pages:
        p_id_db = str(uuid.uuid4())
        if p["ocr_applied"]:
            ocr_any = 1

        cursor.execute("""
            INSERT INTO document_pages (id, document_id, page_number, page_text, char_count, source_spans_json, ocr_applied)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            p_id_db, doc_id, p["page_number"], p["page_text"], p["char_count"],
            json.dumps(p["source_spans"]), p["ocr_applied"]
        ))

        # Perform fact extraction using AI Provider / Gemini API
        p_facts = await extract_clinical_facts_from_text(p["page_text"], page_number=p["page_number"])
        all_facts.extend(p_facts)

    for f in all_facts:
        cursor.execute("""
            INSERT INTO extracted_facts (
                id, document_id, patient_id, fact_type, raw_value, normalized_value,
                code, confidence_score, is_negated, temporality, page_number, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            f["id"], doc_id, p_id, f["factType"], f["rawValue"], f["normalizedValue"],
            f["code"], f["confidenceScore"], f["isNegated"], f["temporality"],
            f["pageNumber"], f["verificationStatus"]
        ))

    # Mark document processing completed
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE patient_documents
        SET page_count = ?, ocr_applied = ?, processing_status = 'completed', uploaded_at = ?
        WHERE id = ?;
    """, (len(pages), ocr_any, now_str, doc_id))

    conn.commit()
    conn.close()

    # AUDIT LOG: Crucial Requirement -> NEVER LOG DOCUMENT CONTENT TEXT
    log_audit_event(
        action="DATA_CHANGE",
        entity_type="document",
        entity_id=doc_id,
        user_id=current_user.user_id,
        payload={
            "event": "DOCUMENT_UPLOADED",
            "fileName": file.filename,
            "documentCategory": document_category,
            "fileSizeBytes": file_size,
            "pageCount": len(pages),
            "ocrApplied": bool(ocr_any),
            "version": doc_version
        }
    )

    return ApiResponse(data={
        "documentId": doc_id,
        "patientId": p_id,
        "fileName": file.filename,
        "documentCategory": document_category,
        "fileSizeBytes": file_size,
        "pageCount": len(pages),
        "ocrApplied": bool(ocr_any),
        "processingStatus": "completed",
        "version": doc_version,
        "factsExtractedCount": len(all_facts)
    })

# 2. Get Document Details & Preview Pages API
@router.get("/{document_id}", response_model=ApiResponse[dict])
async def get_document_details(
    document_id: str,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER, UserRole.VIEWER
    ]))
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patient_documents WHERE id = ?;", (document_id,))
    doc = cursor.fetchone()

    if not doc:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document record not found")

    cursor.execute("SELECT * FROM document_pages WHERE document_id = ? ORDER BY page_number ASC;", (document_id,))
    pages_rows = cursor.fetchall()

    cursor.execute("SELECT * FROM extracted_facts WHERE document_id = ?;", (document_id,))
    facts_rows = cursor.fetchall()
    
    cursor.execute("SELECT * FROM document_versions WHERE document_id = ? ORDER BY version_number DESC;", (document_id,))
    versions_rows = cursor.fetchall()
    
    conn.close()

    pages = [
        {
            "id": r["id"],
            "pageNumber": r["page_number"],
            "pageText": r["page_text"],
            "charCount": r["char_count"],
            "sourceSpans": json.loads(r["source_spans_json"] or "[]"),
            "ocrApplied": bool(r["ocr_applied"])
        } for r in pages_rows
    ]

    facts = [
        {
            "id": r["id"],
            "documentId": r["document_id"],
            "patientId": r["patient_id"],
            "factType": r["fact_type"],
            "rawValue": r["raw_value"],
            "normalizedValue": r["normalized_value"],
            "code": r["code"],
            "confidenceScore": r["confidence_score"],
            "isNegated": bool(r["is_negated"]),
            "temporality": r["temporality"],
            "pageNumber": r["page_number"],
            "verificationStatus": r["verification_status"]
        } for r in facts_rows
    ]

    versions = [
        {
            "id": r["id"],
            "versionNumber": r["version_number"],
            "fileName": r["file_name"],
            "changeSummary": r["change_summary"],
            "uploadedAt": r["uploaded_at"]
        } for r in versions_rows
    ]

    return ApiResponse(data={
        "id": doc["id"],
        "patientId": doc["patient_id"],
        "fileName": doc["file_name"],
        "fileType": doc["file_type"],
        "documentCategory": doc["document_category"],
        "fileSizeBytes": doc["file_size_bytes"],
        "mimeType": doc["mime_type"],
        "storagePath": doc["storage_path"],
        "pageCount": doc["page_count"],
        "ocrApplied": bool(doc["ocr_applied"]),
        "processingStatus": doc["processing_status"],
        "errorMessage": doc["error_message"],
        "version": doc["version"],
        "uploadedAt": doc["uploaded_at"],
        "pages": pages,
        "facts": facts,
        "versions": versions
    })

# 3. Retry Document Processing / OCR Fallback API
@router.post("/{document_id}/retry", response_model=ApiResponse[dict])
async def retry_document_processing(
    document_id: str,
    request: Optional[DocumentRetryRequest] = None,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM patient_documents WHERE id = ?;", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    force_ocr = request.forceOcr if request else True

    # Read genuine document file bytes from disk or DB pages
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    saved_file_path = os.path.join(uploads_dir, f"{doc['id']}_{doc['file_name']}")

    if os.path.exists(saved_file_path):
        with open(saved_file_path, "rb") as f_in:
            file_bytes = f_in.read()
    else:
        cursor.execute("SELECT page_text FROM document_pages WHERE document_id = ? ORDER BY page_number ASC;", (document_id,))
        page_rows = cursor.fetchall()
        existing_text = "\n".join([r["page_text"] for r in page_rows])
        file_bytes = existing_text.encode("utf-8")

    # Re-trigger genuine page extraction and real OCR
    pages = extract_pages_with_pymupdf(file_bytes, doc["file_name"], force_ocr=force_ocr)

    cursor.execute("DELETE FROM document_pages WHERE document_id = ?;", (document_id,))
    cursor.execute("DELETE FROM extracted_facts WHERE document_id = ?;", (document_id,))
    
    all_facts = []
    for p in pages:
        cursor.execute("""
            INSERT INTO document_pages (id, document_id, page_number, page_text, char_count, source_spans_json, ocr_applied)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            str(uuid.uuid4()), document_id, p["page_number"], p["page_text"], p["char_count"],
            json.dumps(p["source_spans"]), p["ocr_applied"]
        ))
        
        p_facts = await extract_clinical_facts_from_text(p["page_text"], page_number=p["page_number"])
        all_facts.extend(p_facts)

    for f in all_facts:
        cursor.execute("""
            INSERT INTO extracted_facts (
                id, document_id, patient_id, fact_type, raw_value, normalized_value,
                code, confidence_score, is_negated, temporality, page_number, verification_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            f["id"], document_id, doc["patient_id"], f["factType"], f["rawValue"], f["normalizedValue"],
            f["code"], f["confidenceScore"], f["isNegated"], f["temporality"],
            f["pageNumber"], f["verificationStatus"]
        ))

    cursor.execute("""
        UPDATE patient_documents
        SET ocr_applied = 1, processing_status = 'completed', error_message = NULL
        WHERE id = ?;
    """, (document_id,))

    conn.commit()
    conn.close()

    log_audit_event(
        action="DATA_CHANGE",
        entity_type="document",
        entity_id=document_id,
        user_id=current_user.user_id,
        payload={"event": "DOCUMENT_RETRY_PROCESSED", "forceOcr": force_ocr}
    )

    return ApiResponse(data={"documentId": document_id, "status": "completed", "ocrApplied": True})

# 4. Approve Facts API
@router.post("/{document_id}/approve", response_model=ApiResponse[dict])
async def approve_extracted_facts(
    document_id: str,
    request: FactApproveRequest,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT patient_id FROM patient_documents WHERE id = ?;", (document_id,))
    doc = cursor.fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    patient_id = doc["patient_id"]
    approved_count = 0
    today_str = datetime.now().strftime("%Y-%m-%d")

    for f_id in request.approvedFactIds:
        cursor.execute("SELECT * FROM extracted_facts WHERE id = ?;", (f_id,))
        fact = cursor.fetchone()
        if fact:
            cursor.execute("UPDATE extracted_facts SET verification_status = 'verified' WHERE id = ?;", (f_id,))

            f_type = fact["fact_type"].lower()
            if f_type == "condition":
                cursor.execute("""
                    INSERT INTO patient_conditions (id, patient_id, raw_value, normalized_value, concept_code, verification_status, source)
                    VALUES (?, ?, ?, ?, ?, 'verified', 'nlp_extraction');
                """, (str(uuid.uuid4()), patient_id, fact["raw_value"], fact["normalized_value"], fact["code"]))
            elif f_type == "lab":
                cursor.execute("""
                    INSERT INTO patient_labs (id, patient_id, raw_value, normalized_value, loinc_code, lab_date, verification_status, source)
                    VALUES (?, ?, ?, ?, ?, ?, 'verified', 'nlp_extraction');
                """, (str(uuid.uuid4()), patient_id, fact["raw_value"], fact["normalized_value"], fact["code"], today_str))
            elif f_type == "biomarker":
                cursor.execute("""
                    INSERT INTO patient_biomarkers (id, patient_id, raw_value, normalized_value, biomarker_name, status_value, test_date, verification_status, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'verified', 'nlp_extraction');
                """, (str(uuid.uuid4()), patient_id, fact["raw_value"], fact["normalized_value"], fact["normalized_value"].split()[0], "POSITIVE", today_str))
            
            approved_count += 1

    conn.commit()
    conn.close()

    log_audit_event(
        action="DATA_CHANGE",
        entity_type="document",
        entity_id=document_id,
        user_id=current_user.user_id,
        payload={"event": "FACTS_APPROVED", "approvedCount": approved_count}
    )

    return ApiResponse(data={"documentId": document_id, "approvedCount": approved_count, "status": "facts_committed"})

# 5. List Documents for a Patient API
@router.get("/patient/{patient_id}", response_model=ApiResponse[List[dict]])
async def list_patient_documents(
    patient_id: str,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER, UserRole.VIEWER
    ]))
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM patients WHERE id = ? OR mrn_synthetic = ?;", (patient_id, patient_id))
    patient = cursor.fetchone()
    if not patient:
        conn.close()
        return ApiResponse(data=[])

    cursor.execute("SELECT * FROM patient_documents WHERE patient_id = ? ORDER BY uploaded_at DESC;", (patient["id"],))
    rows = cursor.fetchall()
    conn.close()

    docs = [
        {
            "id": r["id"],
            "patientId": r["patient_id"],
            "fileName": r["file_name"],
            "fileType": r["file_type"],
            "documentCategory": r["document_category"],
            "fileSizeBytes": r["file_size_bytes"],
            "pageCount": r["page_count"],
            "ocrApplied": bool(r["ocr_applied"]),
            "processingStatus": r["processing_status"],
            "version": r["version"],
            "uploadedAt": r["uploaded_at"]
        } for r in rows
    ]

    return ApiResponse(data=docs)
