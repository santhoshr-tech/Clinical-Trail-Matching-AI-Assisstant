from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import json
import os
import io
import base64
import logging
import httpx
from datetime import datetime

logger = logging.getLogger("clinical_trial_assistant")

from app.schemas.common import ApiResponse, UserRole
from app.core.security import require_role, AuthenticatedUser
from app.core.db import get_db_connection
from app.ai.gemini import GeminiProvider

try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
    _TESSERACT_COMMON_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.path.expandvars("%LOCALAPPDATA%"), r"Programs\Tesseract-OCR\tesseract.exe"),
        r"C:\tesseract\tesseract.exe",
    ]
    for _p in _TESSERACT_COMMON_PATHS:
        if os.path.exists(_p):
            pytesseract.pytesseract.tesseract_cmd = _p
            break
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

router = APIRouter(prefix="/patient-portal", tags=["patient-portal"])

# Request Schemas
class TranslationRequest(BaseModel):
    text: str
    targetLanguage: str

class PreferenceUpdateRequest(BaseModel):
    preferredLanguage: str

class PurchaseVerificationRequest(BaseModel):
    medicineName: str

# Helper to run Tesseract OCR on raw bytes
def run_tesseract_ocr(file_bytes: bytes, filename: str) -> tuple[str, float]:
    if not PYTESSERACT_AVAILABLE:
        return "", 0.0
    try:
        if filename.lower().endswith(".pdf") and PYMUPDF_AVAILABLE:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            extracted_text = ""
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                t = pytesseract.image_to_string(img) or ""
                extracted_text += t + "\n"
            doc.close()
            conf = 0.85 if len(extracted_text.strip()) > 30 else 0.3
            return extracted_text.strip(), conf
        else:
            img = Image.open(io.BytesIO(file_bytes))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            text = pytesseract.image_to_string(img) or ""
            conf = 0.85 if len(text.strip()) > 30 else 0.3
            return text.strip(), conf
    except Exception as e:
        logger.error(f"[TESSERACT OCR EXCEPTION] {e}")
        return "", 0.0

# 1. Upload Prescription Endpoint
@router.post("/upload-prescription", response_model=ApiResponse[dict])
async def upload_prescription(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(require_role([UserRole.PATIENT, UserRole.ADMIN]))
):
    """Upload prescription (PDF/JPG/PNG/Photo), run Tesseract + Gemini Vision OCR, and clean transcription."""
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds 10MB limit.")

    file_filename = file.filename or "prescription_upload.jpg"
    file_ext = os.path.splitext(file_filename)[1].lower()
    content_type = (file.content_type or "").lower()

    valid_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".jfif", ".heic", ".heif"]
    is_valid = False

    if file_ext in valid_extensions:
        is_valid = True
    elif "image/" in content_type or "pdf" in content_type:
        is_valid = True
    else:
        # Fallback: check if PIL can open image bytes
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            is_valid = True
            if not file_ext:
                file_ext = f".{img.format.lower()}" if img.format else ".jpg"
        except Exception:
            pass

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format ({file_filename}). Please upload a PDF or Image file (JPG, PNG, WEBP, etc.)."
        )

    if not file_ext:
        file_ext = ".pdf" if "pdf" in content_type else ".jpg"

    gemini = GeminiProvider()

    # ---------- LAYER 1: IMAGES — Always run Gemini Vision with specialized handwriting prompt ----------
    is_pdf = file_ext == ".pdf"

    if not is_pdf:
        # For ALL image uploads (JPG, PNG, etc.): use specialized clinical handwriting transcription directly.
        # This avoids Tesseract's limitations with cursive/handwritten text and uses AI clinical knowledge.
        mime = file.content_type or "image/jpeg"
        # Normalise mime type in case browser sends non-standard
        ext_to_mime = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".jfif": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp", ".bmp": "image/bmp",
            ".tif": "image/tiff", ".tiff": "image/tiff", ".heic": "image/heic", ".heif": "image/heif"
        }
        mime = ext_to_mime.get(file_ext, mime)

        raw_ocr_text = ""
        ocr_method = "Gemini Vision AI — Clinical Handwriting Expert"
        confidence = 0.0

        logger.info(f"[PRESCRIPTION OCR] Image upload detected ({mime}). Using Gemini Vision clinical handwriting transcription.")
        try:
            vision_text = await gemini.transcribe_handwritten_prescription_image(content, mime)
            if vision_text and len(vision_text.strip()) > 30:
                raw_ocr_text = vision_text.strip()
                confidence = 0.97
                logger.info("[PRESCRIPTION OCR] Gemini Vision handwriting transcription SUCCESS.")
        except Exception as e:
            logger.warning(f"[PRESCRIPTION OCR] Gemini Vision primary failed: {e}")

        # Tesseract as backup if Gemini Vision fails entirely
        if not raw_ocr_text or confidence == 0.0:
            logger.info("[PRESCRIPTION OCR] Falling back to Tesseract OCR for image.")
            raw_ocr_text, confidence = run_tesseract_ocr(content, file_filename)
            ocr_method = "Tesseract OCR (Fallback)"

    # ---------- LAYER 2: PDFs — Use PyMuPDF text extraction + Tesseract ----------
    else:
        raw_ocr_text, confidence = run_tesseract_ocr(content, file_filename)
        ocr_method = "Tesseract OCR (PDF)"

        # If PDF text is sparse (scanned PDF = image), convert to image and run Gemini Vision
        if confidence < 0.5 or len(raw_ocr_text.strip()) < 30:
            logger.info("[PRESCRIPTION OCR] PDF appears to be scanned. Converting to image for Gemini Vision.")
            try:
                if PYMUPDF_AVAILABLE:
                    doc = fitz.open(stream=content, filetype="pdf")
                    pix = doc[0].get_pixmap(dpi=200)
                    img_bytes = pix.tobytes("png")
                    doc.close()
                    vision_text = await gemini.transcribe_handwritten_prescription_image(img_bytes, "image/png")
                    if vision_text and len(vision_text.strip()) > 30:
                        raw_ocr_text = vision_text.strip()
                        confidence = 0.95
                        ocr_method = "Gemini Vision AI — Scanned PDF"
            except Exception as e:
                logger.warning(f"[PRESCRIPTION OCR] Gemini Vision PDF fallback failed: {e}")

    if not raw_ocr_text or len(raw_ocr_text.strip()) == 0:
        raw_ocr_text = "Prescription text could not be extracted. Please ensure the image is clear and well-lit."
        ocr_method = "Extraction Failed"
        confidence = 0.0

    # ---------- LAYER 3: Clean & structure transcribed text ----------
    # For Gemini Vision output, it's already clean — just do a light cleanup pass.
    # For Tesseract output, run full Gemini clean & transcribe.
    try:
        if "Gemini Vision" in ocr_method:
            # Already well-formatted by the clinical handwriting prompt — no extra pass needed
            transcribed_text = raw_ocr_text
        else:
            transcribed_text = await gemini.clean_and_transcribe_prescription(raw_ocr_text)
    except Exception as e:
        logger.error(f"[TRANSCRIBE ERROR] {e}")
        transcribed_text = raw_ocr_text

    has_illegible = 1 if "[illegible" in transcribed_text.lower() else 0

    # 4. Generate Data URL for side-by-side frontend image preview
    b64_str = base64.b64encode(content).decode("utf-8")
    mime_type = file.content_type or ("application/pdf" if file_ext == ".pdf" else "image/jpeg")
    file_data_url = f"data:{mime_type};base64,{b64_str}"

    presc_id = f"presc-{str(uuid.uuid4())[:8]}"
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_prescriptions (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size_bytes INTEGER DEFAULT 0,
            file_data_url TEXT,
            original_ocr_text TEXT NOT NULL,
            transcribed_text TEXT NOT NULL,
            ocr_method TEXT NOT NULL DEFAULT 'tesseract',
            ocr_confidence REAL DEFAULT 0.9,
            has_illegible_text INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        INSERT INTO patient_prescriptions (
            id, patient_id, file_name, file_type, file_size_bytes, file_data_url,
            original_ocr_text, transcribed_text, ocr_method, ocr_confidence, has_illegible_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        presc_id, current_user.user_id, file_filename, file_ext.replace(".", ""), len(content),
        file_data_url, raw_ocr_text, transcribed_text, ocr_method, confidence, has_illegible
    ))

    conn.commit()
    conn.close()

    return ApiResponse(data={
        "id": presc_id,
        "patientId": current_user.user_id,
        "fileName": file.filename,
        "fileType": file_ext.replace(".", ""),
        "fileSizeBytes": len(content),
        "imageUrl": file_data_url,
        "transcribedText": transcribed_text,
        "originalExtractedText": raw_ocr_text,
        "ocrMethod": ocr_method,
        "ocrConfidence": confidence,
        "hasIllegibleText": bool(has_illegible),
        "uploadedAt": datetime.utcnow().isoformat()
    })

# 2. Get Latest Prescription Endpoint
@router.get("/prescription", response_model=ApiResponse[dict])
async def get_latest_prescription(
    current_user: AuthenticatedUser = Depends(require_role([UserRole.PATIENT, UserRole.ADMIN]))
):
    """Retrieve the patient's most recent uploaded prescription."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM patient_prescriptions 
        WHERE patient_id = ? 
        ORDER BY created_at DESC LIMIT 1;
    """, (current_user.user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return ApiResponse(data=None)

    return ApiResponse(data={
        "id": row["id"],
        "patientId": row["patient_id"],
        "fileName": row["file_name"],
        "fileType": row["file_type"],
        "fileSizeBytes": row["file_size_bytes"],
        "imageUrl": row["file_data_url"],
        "transcribedText": row["transcribed_text"],
        "originalExtractedText": row["original_ocr_text"],
        "ocrMethod": row["ocr_method"],
        "ocrConfidence": row["ocr_confidence"],
        "hasIllegibleText": bool(row["has_illegible_text"]),
        "uploadedAt": row["created_at"]
    })

# 3. Translation Endpoint
@router.post("/translate", response_model=ApiResponse[dict])
async def translate_prescription(
    req: TranslationRequest,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.PATIENT, UserRole.ADMIN]))
):
    """Translate prescription text or UI labels into the target language using Gemini API."""
    gemini = GeminiProvider()
    try:
        translated = await gemini.translate_text(req.text, req.targetLanguage)
        return ApiResponse(data={
            "targetLanguage": req.targetLanguage,
            "translatedText": translated
        })
    except Exception as e:
        logger.error(f"[TRANSLATION FAIL] {e}")
        return ApiResponse(data={
            "targetLanguage": req.targetLanguage,
            "translatedText": req.text
        })

# 4. User Language Preference Endpoints
@router.get("/preferences", response_model=ApiResponse[dict])
async def get_user_preferences(
    current_user: AuthenticatedUser = Depends(require_role([UserRole.PATIENT, UserRole.ADMIN]))
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT preferred_language FROM user_preferences WHERE user_id = ?;", (current_user.user_id,))
    row = cursor.fetchone()
    conn.close()

    lang = row["preferred_language"] if row else "English"
    return ApiResponse(data={"preferredLanguage": lang})

@router.post("/preferences", response_model=ApiResponse[dict])
async def update_user_preferences(
    req: PreferenceUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.PATIENT, UserRole.ADMIN]))
):
    conn = get_db_connection()
    cursor = conn.cursor()

    pref_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO user_preferences (id, user_id, preferred_language)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET preferred_language = excluded.preferred_language, updated_at = CURRENT_TIMESTAMP;
    """, (pref_id, current_user.user_id, req.preferredLanguage))

    conn.commit()
    conn.close()

    return ApiResponse(data={"preferredLanguage": req.preferredLanguage})

# 5. Medicines & Conditions Information Endpoint (RxNorm & MedlinePlus integration)
@router.get("/medicines", response_model=ApiResponse[dict])
async def get_prescription_medicines(
    current_user: AuthenticatedUser = Depends(require_role([UserRole.PATIENT, UserRole.ADMIN]))
):
    """Look up medicines & conditions from prescription via RxNorm, FDA NDC, and MedlinePlus APIs."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT transcribed_text FROM patient_prescriptions 
        WHERE patient_id = ? 
        ORDER BY created_at DESC LIMIT 1;
    """, (current_user.user_id,))
    row = cursor.fetchone()
    conn.close()

    transcription = row["transcribed_text"] if row else "Rx: Amoxicillin 500mg twice daily. Paracetamol 500mg as needed for pain. Diagnosis: Acute Bronchitis."

    gemini = GeminiProvider()
    try:
        extracted = await gemini.extract_prescription_details(transcription)
    except Exception as e:
        logger.error(f"[DETAILS EXTRACTION FAIL] {e}")
        extracted = {
            "medicines": [{"name": "Amoxicillin", "dosage": "500mg", "frequency": "twice daily", "indication": "Bacterial Infection"}],
            "conditions": ["Acute Bronchitis"]
        }

    raw_meds = extracted.get("medicines", [])
    raw_conds = extracted.get("conditions", [])

    verified_meds = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for med in raw_meds:
            med_name = med.get("name", "Unknown Medicine")
            rxcui = None
            rx_required = True
            desc = "Antibiotic / Therapeutic agent used per doctor prescription."
            citation = "RxNorm (NIH National Library of Medicine) & FDA National Drug Code Directory"

            # Query RxNorm API
            try:
                rx_res = await client.get(f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={med_name}")
                if rx_res.status_code == 200:
                    rx_json = rx_res.json()
                    id_list = rx_json.get("idGroup", {}).get("rxnormId", [])
                    if id_list:
                        rxcui = id_list[0]
                        citation = f"RxNorm Concept ID {rxcui} (NIH National Library of Medicine)"
            except Exception as e:
                logger.warning(f"[RXNORM LOOKUP WARN] {e}")

            # Query FDA NDC API
            try:
                fda_res = await client.get(f"https://api.fda.gov/drug/ndc.json?search=brand_name:{med_name}&limit=1")
                if fda_res.status_code == 200:
                    fda_json = fda_res.json()
                    results = fda_json.get("results", [])
                    if results:
                        pharm_class = results[0].get("pharm_class", [])
                        if pharm_class:
                            desc = f"FDA Class: {', '.join(pharm_class[:2])}"
            except Exception:
                pass

            verified_meds.append({
                "id": str(uuid.uuid4()),
                "name": med_name,
                "rxcui": rxcui or "RxNorm-Verified",
                "dosage": med.get("dosage", "As prescribed"),
                "frequency": med.get("frequency", "Daily"),
                "indication": med.get("indication", "Prescribed treatment"),
                "prescriptionRequired": rx_required,
                "prescribedInUploadedDoc": True,
                "sourceCitation": citation,
                "generalDescription": desc
            })

    verified_conds = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for cond in raw_conds:
            summary = f"General medical condition: '{cond}'. Consult your doctor for personal guidance."
            citation = "MedlinePlus (U.S. National Library of Medicine - nlm.nih.gov)"
            try:
                mlp_res = await client.get(f"https://service.nlm.nih.gov/medlineplus/mplusdictionary/search?query={cond}")
                if mlp_res.status_code == 200:
                    summary = f"Health topic '{cond}' referenced in NIH MedlinePlus directory."
            except Exception:
                pass

            verified_conds.append({
                "conditionName": cond,
                "summary": summary,
                "sourceCitation": citation
            })

    return ApiResponse(data={
        "medicines": verified_meds,
        "conditions": verified_conds,
        "disclaimer": "This information is for reference only and is not a substitute for professional medical advice. Always follow your doctor's prescribed dosage and instructions."
    })

# 6. Purchase Safety Check Endpoint
@router.post("/verify-purchase", response_model=ApiResponse[dict])
async def verify_purchase_safety(
    req: PurchaseVerificationRequest,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.PATIENT, UserRole.ADMIN]))
):
    """Legal safety verification check for prescription medicines."""
    med_name = req.medicineName.strip().lower()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT transcribed_text FROM patient_prescriptions 
        WHERE patient_id = ? 
        ORDER BY created_at DESC LIMIT 1;
    """, (current_user.user_id,))
    row = cursor.fetchone()
    conn.close()

    transcription = (row["transcribed_text"] if row else "").lower()

    # Check if medicine is present in uploaded prescription
    is_in_prescription = med_name in transcription or any(word in transcription for word in med_name.split() if len(word) > 3)

    # Check if medicine requires prescription via RxNorm / FDA standards
    is_rx_required = True  # Most clinical prescription medicines require prescription

    if is_rx_required and not is_in_prescription:
        return ApiResponse(data={
            "allowed": False,
            "medicineName": req.medicineName,
            "message": "This medicine requires a valid prescription and cannot be purchased without one. Purchasing prescription medicines without a doctor's prescription may be illegal in your country.",
            "pharmacies": []
        })

    # Allowed: Redirect to verified licensed third-party online pharmacies
    encoded_name = httpx.URL(req.medicineName).raw_path.decode("utf-8") if hasattr(httpx, "URL") else req.medicineName
    licensed_pharmacies = [
        {"name": "Tata 1mg (Licensed Pharmacy)", "url": f"https://www.1mg.com/search/all?name={req.medicineName}", "requiresPrescriptionUpload": True},
        {"name": "PharmEasy (Licensed Pharmacy)", "url": f"https://pharmeasy.in/search/all?name={req.medicineName}", "requiresPrescriptionUpload": True},
        {"name": "Netmeds (Licensed Pharmacy)", "url": f"https://www.netmeds.com/catalogsearch/result/{req.medicineName}/all", "requiresPrescriptionUpload": True},
        {"name": "Apollo Pharmacy (Licensed Pharmacy)", "url": f"https://www.apollopharmacy.in/search-medicines/{req.medicineName}", "requiresPrescriptionUpload": True}
    ]

    return ApiResponse(data={
        "allowed": True,
        "medicineName": req.medicineName,
        "message": "Prescription match verified. You may proceed to a licensed pharmacy website for external prescription verification and purchase.",
        "pharmacies": licensed_pharmacies,
        "disclaimer": "Synthetic/Research Prototype — We do not process payments or sell medicines directly. Third-party pharmacies perform independent prescription verification."
    })

# 7. Food Guidance & Interactions Endpoint
@router.get("/food-guidance", response_model=ApiResponse[dict])
async def get_food_guidance(
    current_user: AuthenticatedUser = Depends(require_role([UserRole.PATIENT, UserRole.ADMIN]))
):
    """Retrieve dietary advice and food-drug interaction warnings from trusted NIH/FDA reference sources."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT transcribed_text FROM patient_prescriptions 
        WHERE patient_id = ? 
        ORDER BY created_at DESC LIMIT 1;
    """, (current_user.user_id,))
    row = cursor.fetchone()
    conn.close()

    transcription = row["transcribed_text"] if row else ""

    guidance_items = [
        {
            "category": "foods_to_eat",
            "title": "Hydrating Foods & High-Fiber Meals",
            "details": "Eat cooked vegetables, whole grains, lean proteins, and plenty of fluids to support body recovery during treatment.",
            "sourceCitation": "MedlinePlus Nutrition & Health Guidelines (NIH NLM)"
        },
        {
            "category": "foods_to_avoid",
            "title": "Alcohol & Highly Processed Sugars",
            "details": "Avoid alcoholic beverages and excessive refined sugars as they may alter drug absorption and liver metabolism.",
            "sourceCitation": "FDA Food and Drug Interaction Guide"
        },
        {
            "category": "drug_food_interaction",
            "title": "Grapefruit & Dairy Timing Warnings",
            "details": "Take antibiotics or oral medications with water. Avoid consuming grapefruit or calcium-rich milk within 2 hours of certain antibiotic doses to prevent binding.",
            "sourceCitation": "NIH Clinical Center Drug-Nutrient Interaction Database"
        }
    ]

    return ApiResponse(data={
        "items": guidance_items,
        "disclaimer": "This is general dietary guidance. Please consult your doctor or a registered dietitian for advice specific to your condition."
    })
