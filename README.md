# AI Clinical Trial Matching & Research Assistant

> **SAFETY DISCLAIMER & SCOPE:**  
> This system is a **synthetic / de-identified research prototype and decision-support tool**. It does **not** provide final medical advice, replace a qualified investigator, or automatically enroll patients. Final eligibility determinations require independent review by authorized clinical research coordinators and investigators.

---

## 📌 Project Overview
The **AI Clinical Trial Matching & Research Assistant** is a modular-monolith web application built to streamline clinical trial pre-screening for research coordinators and principal investigators. It ingests synthetic patient records and unstructured medical documents, extracts and normalizes clinical facts, parses ClinicalTrials.gov protocols into structured logic trees, and evaluates patient eligibility using a deterministic rule engine backed by grounded AI extraction.

---

## ⚡ Key Features
1. **Synthetic Patient Management**: Manage synthetic patient demographics, conditions, medications, labs, biomarkers, and longitudinal timelines.
2. **Document Parsing & OCR**: PyMuPDF parsing with Tesseract OCR fallback and page-level character span grounding.
3. **Clinical NLP Pipeline**: Fact extraction, medical terminology normalization (RxNorm/SNOMED/LOINC), negation detection, and temporal expression validation.
4. **Trial Protocol Import**: Search and ingest official protocol criteria from ClinicalTrials.gov REST API v2.
5. **Deterministic 4-State Matching Engine**: Evaluates criteria into `PASS`, `FAIL`, `UNKNOWN`, or `CONFLICT` states.
6. **Overall Screening States**: Classifies patient eligibility into `eligible_for_review`, `potentially_eligible`, `not_eligible`, `manual_review_required`, or `expired_match`.
7. **Side-by-Side Evidence Grounding**: Trace every decision directly to source document spans and page numbers.
8. **What-If Eligibility Simulator**: Test hypothetical patient changes without altering canonical database records.
9. **Continuous Automated Re-screening**: Automatically re-evaluate matching status when patient data or trial criteria versions change.
10. **AI vs Human Analytics & Feedback**: Track coordinator overrides, dispute categories, and researcher feedback.
11. **Repeatable Evaluation Module**: Benchmark system extractions and matching decisions against a gold-standard annotated dataset.
12. **100% Decision Traceability**: Comprehensive append-only audit trail for regulatory and compliance tracking.

---

## 🛠️ Technology Stack
- **Frontend**: React, Vite, TypeScript, Tailwind CSS, React Router, Recharts, TanStack Query
- **Backend**: Python, FastAPI, Pydantic, SQLAlchemy, Pytest, Uvicorn
- **Database**: PostgreSQL (Supabase / SQLite local fallback)
- **AI Abstraction**: `AIProvider` interface supporting `MockProvider` (default), `GeminiProvider`, and `OllamaProvider`
- **Documents & NLP**: PyMuPDF, Tesseract OCR fallback, rule-based clinical regex, medical entity normalization

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- Node.js (v18+) & npm
- Python 3.10+
- Tesseract OCR (optional, for image PDF fallback)

### Backend Setup
```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
# Activate on Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables template
cp ../.env.example .env

# Run FastAPI development server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run Vite dev server
npm run dev
```

The application will be accessible at:
- **Frontend**: `http://localhost:5173`
- **Backend API Docs**: `http://localhost:8000/docs`

---

## 📑 Documentation Links
- [System Architecture](docs/ARCHITECTURE.md)
- [Workflow & Pipeline Diagram](docs/WORKFLOW.md)
- [Data Model & Database Schema](docs/DATA_MODEL.md)
- [REST API Specification](docs/API_SPEC.md)
- [Evaluation Plan & Metrics Framework](docs/EVALUATION_PLAN.md)
- [Data Safety & Security Plan](docs/SECURITY.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
