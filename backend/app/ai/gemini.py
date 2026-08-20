import os
import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from app.ai.base import AIProvider, ExtractionResult
from app.core.config import settings

logger = logging.getLogger("clinical_trial_assistant")

class GeminiProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-1.5-flash"
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"

    async def _call_gemini_api(self, prompt: str, json_mode: bool = False, timeout: float = 8.0) -> str:
        """Call Gemini REST API directly using httpx with detailed error logging and model fallback."""
        key = self.api_key or ""

        if not key or "placeholder" in key.lower() or "your-" in key.lower():
            logger.warning("[GEMINI WARNING] GEMINI_API_KEY missing or placeholder — using intelligent local NLP fallback.")
            raise ValueError("GEMINI_API_KEY is missing or invalid.")

        models_to_try = [
            self.model_name,
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-3.7-flash"
        ]
        unique_models = list(dict.fromkeys([m for m in models_to_try if m]))

        last_error = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for model in unique_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                gen_config = {"temperature": 0.1}
                if json_mode:
                    gen_config["responseMimeType"] = "application/json"

                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": gen_config
                }

                logger.info(f"[GEMINI API] Attempting call to model: '{model}' (timeout={timeout}s)")
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        content_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        logger.info(f"[GEMINI API SUCCESS] Received response from '{model}'")
                        return content_text
                    else:
                        last_error = f"Model '{model}' returned HTTP {response.status_code}: {response.text}"
                        logger.warning(f"[GEMINI API WARN] {last_error}")
                except Exception as e:
                    last_error = f"Request to model '{model}' failed: {type(e).__name__} - {e}"
                    logger.warning(f"[GEMINI API EXCEPTION] {last_error}")

        raise ValueError(f"Gemini API call failed for all candidate models. Last error: {last_error}")

    async def _call_gemini_vision_api(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        """Call Gemini Vision API directly using httpx with inlineData base64 image bytes."""
        import base64
        key = self.api_key or ""
        if not key or "placeholder" in key.lower() or "your-" in key.lower():
            logger.warning("[GEMINI VISION WARN] GEMINI_API_KEY missing or placeholder.")
            raise ValueError("GEMINI_API_KEY is missing or invalid.")

        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        models_to_try = [
            self.model_name,
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-2.5-flash",
            "gemini-flash-latest"
        ]
        unique_models = list(dict.fromkeys([m for m in models_to_try if m]))

        last_error = None
        async with httpx.AsyncClient(timeout=10.0) as client:
            for model in unique_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "inlineData": {
                                        "mimeType": mime_type,
                                        "data": b64_data
                                    }
                                },
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1
                    }
                }

                logger.info(f"[GEMINI VISION] Attempting image OCR call with model: '{model}'")
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        content_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        return content_text
                    else:
                        last_error = f"Model '{model}' returned HTTP {response.status_code}: {response.text}"
                except Exception as e:
                    last_error = f"Vision request to model '{model}' failed: {type(e).__name__} - {e}"

        raise ValueError(f"Gemini Vision API call failed for all models. Last error: {last_error}")

    async def transcribe_handwritten_prescription_image(self, image_bytes: bytes, mime_type: str) -> str:
        """Decipher handwritten doctor prescriptions using specialized clinical handwriting AI prompt & medical shorthand knowledge."""
        prompt = """You are a Senior Clinical Pharmacist and Medical AI OCR Expert specializing in reading complex doctor handwriting, handwritten prescriptions, medical shorthand, and clinical notes across global and regional standards.

EXAMINE THE UPLOADED PRESCRIPTION / REPORT AND TRANSCRIBE ALL HANDWRITTEN & PRINTED TEXT ACCURATELY.

======================================================================
CLINICAL HANDWRITING & SHORTHAND REFERENCE KNOWLEDGE:
======================================================================
1. CLINICAL HEADERS & VITALS:
   - Rx / ℞ = Prescription / Treatment
   - C/o = Complains of / Chief Complaint (e.g. C/o cold, fever, cough, chest pain, body pain)
   - K/c/o = Known case of (e.g. K/c/o Allergic Asthma, Diabetes/DM, Hypertension/HTN, CKD)
   - O/e = On examination (Vitals: BP 120/70, HR 116/min, Temp 102.2F, SpO2 98%, RS B/L AEE, CVS N, Abd Soft)
   - Adv / Advice = Instructions / General advice

2. MEDICATION FORM PREFIXES:
   - T. / Tab. / Tab / 1) / 2) = Tablet
   - C. / Cap. / Cap = Capsule
   - S. / Syp. / Syr. / S. = Syrup / Oral Suspension
   - I. / Inj. / Inj = Injection
   - Oint. / L/A = Ointment / Local Application
   - Inhaler / Puffs = Inhaler / Nebulizer

3. DOSAGE FREQUENCY PATTERNS & TIMING:
   - 1-0-1 = Twice daily (Morning & Night) [BD / BID]
   - 1-1-1 = Three times daily (Morning, Afternoon & Night) [TDS / TID]
   - 1-0-0 = Once daily (Morning) [OD]
   - 0-0-1 = Bedtime only [HS]
   - 1x1, 1x2, 1x3 = 1 tablet once, twice, or thrice daily
   - Q6H / Q4H = Every 6 hours / Every 4 hours
   - SOS = As needed / Emergency relief (e.g. for fever or severe pain)
   - BBF / AC = Before Breakfast / Before Food
   - AF / PC = After Food / After Meals
   - (6), (8), (10), 60 days, 120 days = Total quantity or duration

4. BRAND & GENERIC MEDICAL KNOWLEDGE:
   - Antibiotics & Anti-infectives: Opox-CV, Amoxicillin, Augmentin, Moxikind-CV, Monocet, Azithromycin, Ciprofloxacin, Cefixime
   - Analgesics & Antipyretics: Dolo 650, Calpol, Paracetamol, Meftal-P, Combiflam, Altilose-SP, Breezy, Skipon-D, Febrin, Plazo
   - Gastrointestinal & Antacids: Pan 40, Pantoprazole, Omez, Rantac, Liv-52, Zincovit
   - Respiratory & Asthma: Xaltide Inhaler, Levolin, Ventolin Expectorant, Delcon, Floaid, L-C-Z Mont
   - Cardiovascular & Diabetes: Cetanil, Glizid, Valera, Voglikem-M, Telmisartan, Amlodipine, Metformin

======================================================================
OUTPUT INSTRUCTIONS:
======================================================================
1. Use clinical context to decipher cursive handwriting accurately. DO NOT lazily mark readable cursive handwriting as "[illegible]".
2. Only mark "[illegible — please confirm with your doctor]" if a section of the document is physically torn, obscured by a dark smudge, or completely unreadable.
3. Organize the transcription clearly under these headers:
   - 👨‍⚕️ Doctor & Clinic Details
   - 👤 Patient Information & Vitals
   - 🩺 Clinical Findings & Complaints (C/o & K/c/o)
   - 💊 Prescribed Medications (Rx)
   - 📝 Doctor Advice & Instructions

Return ONLY the clean transcribed text without meta explanation.
"""
        return await self._call_gemini_vision_api(image_bytes, mime_type, prompt)

    async def clean_and_transcribe_prescription(self, raw_text: str) -> str:
        """Pass raw OCR text through Gemini API to produce clean, legible prescription transcription."""
        prompt = f"""You are a medical prescription transcription assistant.
Clean up the following raw OCR text extracted from a doctor's prescription or handwritten notes.

CRITICAL INSTRUCTIONS:
1. Produce a clean, human-readable, formatted version of exactly what the doctor wrote.
2. DO NOT summarize, extrapolate, or invent details not present in the text.
3. If any words, dosages, or numbers are illegible or ambiguous, write "[illegible — please confirm with your doctor]" for that exact word/phrase.
4. Keep original medicine names, dosages, instructions, diagnosis, patient details, and doctor notes clear.

Raw OCR Text:
\"\"\"
{raw_text}
\"\"\"
"""
        return await self._call_gemini_api(prompt)

    async def translate_text(self, text: str, target_language: str) -> str:
        """Translate text into target language using Gemini API."""
        logger.info(f"[GEMINI TRANSLATE] Received translation request. Target language: '{target_language}'. Text length: {len(text) if text else 0}")
        if not text or target_language.lower() == "english":
            logger.info("[GEMINI TRANSLATE] Language is English or text empty. Returning original text without calling API.")
            return text

        prompt = f"""You are a professional medical translator.
Translate the following medical prescription transcription text FULLY and COMPLETELY into {target_language}.

RULES:
1. Translate EVERY line and section heading into {target_language}.
2. Keep medicine names (brand/generic) in English — only translate instructions, labels, and dosage frequency words.
3. Keep [illegible — please confirm with your doctor] markers, translate the surrounding words.
4. Preserve the structured section layout (Doctor details, Patient info, Medications, Advice) using translated headings.
5. Return ONLY the translated text — no meta commentary, no explanations.

Text to translate:
\"\"\"
{text}
\"\"\"
"""
        logger.info(f"[GEMINI TRANSLATE API CALL] Calling Gemini API for target language: '{target_language}'...")
        try:
            translated = await self._call_gemini_api(prompt, timeout=25.0)
            logger.info(f"[GEMINI TRANSLATE RAW RESPONSE] (First 150 chars): {translated[:150] if translated else 'EMPTY'}")
            return translated
        except Exception as e:
            logger.error(f"[GEMINI TRANSLATE ERROR] Translation call failed: {e}")
            raise e

    async def extract_prescription_details(self, text: str) -> Dict[str, Any]:
        """Extract structured JSON list of medicines and diagnosed conditions from prescription text."""
        prompt = f"""You are a clinical NLP extractor.
Analyze the following prescription text and extract all prescribed medicines and diagnosed conditions/diseases.
Return ONLY valid JSON matching this schema:
{{
  "medicines": [
    {{
      "name": "<medicine brand/generic name>",
      "dosage": "<e.g., 500mg>",
      "frequency": "<e.g., twice daily after meals>",
      "indication": "<purpose if stated>"
    }}
  ],
  "conditions": [
    "<diagnosed condition/disease 1>",
    "<diagnosed condition/disease 2>"
  ]
}}

Prescription Text:
\"\"\"
{text}
\"\"\"
"""
        raw_resp = await self._call_gemini_api(prompt, json_mode=True)
        clean = raw_resp.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        try:
            return json.loads(clean.strip())
        except Exception:
            return {"medicines": [], "conditions": []}

    async def extract_patient_facts(self, text: str) -> ExtractionResult:
        """Extract clinical facts from real OCR-extracted text using Gemini API."""
        prompt = f"""You are an expert clinical NLP extraction assistant.
Extract all clinical facts and entities from the following medical document text (including diagnoses, radiology findings, lab results, medications, biomarkers, procedures, and clinical observations).
Return ONLY valid JSON matching this schema:
{{
  "facts": [
    {{
      "factType": "condition",
      "rawValue": "<exact raw text snippet>",
      "normalizedValue": "<canonical label>",
      "code": "<LOINC / RxNorm / SNOMED code if available>",
      "confidenceScore": 0.95,
      "isNegated": false,
      "temporality": "current"
    }}
  ],
  "confidence": 0.95
}}

Medical Document Text:
\"\"\"
{text}
\"\"\"
"""
        raw_response = await self._call_gemini_api(prompt, json_mode=True)
        clean_resp = raw_response.strip()
        if clean_resp.startswith("```json"):
            clean_resp = clean_resp[7:]
        if clean_resp.startswith("```"):
            clean_resp = clean_resp[3:]
        if clean_resp.endswith("```"):
            clean_resp = clean_resp[:-3]
        clean_resp = clean_resp.strip()
        
        try:
            parsed = json.loads(clean_resp)
        except Exception as err:
            logger.error(f"[GEMINI JSON PARSE ERROR] Failed to parse JSON: {err}. Raw: {clean_resp}")
            print(f"[GEMINI JSON PARSE ERROR] {err}")
            parsed = {"facts": [], "confidence": 0.5}

        facts_list = parsed.get("facts", []) if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
        return ExtractionResult(
            facts=facts_list,
            confidence=parsed.get("confidence", 0.9) if isinstance(parsed, dict) else 0.9,
            provider="gemini"
        )

    async def extract_trial_criteria(self, protocol_text: str) -> Dict[str, Any]:
        """Extract structured inclusion/exclusion trial criteria using Gemini API."""
        prompt = f"""You are a clinical trial protocol analyzer.
Extract inclusion and exclusion criteria from the protocol text.
Return ONLY valid JSON:
{{
  "inclusion": ["<criterion 1>", "<criterion 2>"],
  "exclusion": ["<criterion 1>", "<criterion 2>"]
}}

Protocol Text:
\"\"\"
{protocol_text}
\"\"\"
"""
        raw_response = await self._call_gemini_api(prompt)
        return json.loads(raw_response)

    async def normalize_medical_terms(self, raw_terms: List[str]) -> List[Dict[str, Any]]:
        """Normalize medical terms using Gemini API."""
        prompt = f"""Normalize these medical terms to standard coding systems (LOINC, RxNorm, SNOMED CT).
Return ONLY valid JSON array:
[
  {{
    "raw_text": "<term>",
    "normalized_label": "<canonical name>",
    "coding_system": "LOINC",
    "code": "<code>"
  }}
]

Terms: {json.dumps(raw_terms)}
"""
        raw_response = await self._call_gemini_api(prompt)
        return json.loads(raw_response)

    async def detect_negation(self, text_spans: List[str]) -> List[Dict[str, Any]]:
        """Detect negation in clinical text spans using Gemini API."""
        prompt = f"""Analyze clinical text spans for negation (whether the condition/finding is absent or denied).
Return ONLY valid JSON array:
[
  {{
    "span": "<text span>",
    "is_negated": false
  }}
]

Spans: {json.dumps(text_spans)}
"""
        raw_response = await self._call_gemini_api(prompt)
        return json.loads(raw_response)
