# System Architecture: AI Clinical Trial Matching & Research Assistant

## 1. System Overview
The **AI Clinical Trial Matching & Research Assistant** is a modular-monolith decision support application designed for clinical research coordinators (CRCs) and principal investigators (PIs). It automates pre-screening matching of synthetic patient records and clinical documents against ClinicalTrials.gov protocol criteria, grounding every decision in explicit source evidence with a 100% traceable audit trail.

> **CRITICAL SAFETY DISCLAIMER & SCOPE:**  
> This system is a **synthetic/de-identified research prototype and decision-support tool**. It does **not** provide medical advice, replace a qualified investigator, or automatically enroll patients. Final eligibility determinations require independent review by authorized clinical research coordinators and investigators.

---

## 2. High-Level Architecture Diagram

```mermaid
graph TD
    subgraph Frontend [React + Vite + TypeScript + Tailwind CSS]
        UI[UI Components & Dashboard Pages]
        State[State Management & TanStack Query]
        Router[React Router SPA]
    end

    subgraph Backend [FastAPI Modular Monolith]
        API Gateway[FastAPI API Router]
        
        subgraph Core Modules
            AuthMod[auth / security]
            PatientMod[patients & timeline]
            DocMod[documents & OCR / parsing]
            NLPMod[extraction & normalization & negation & temporal]
            TrialMod[trials & ClinicalTrials.gov API proxy]
            MatchMod[matching engine & rules]
            EvidenceMod[evidence & conflict resolver]
            SimMod[what_if simulator]
            RescreenMod[rescreening & impact analysis]
            ReviewMod[review & feedback & audit]
            EvalMod[evaluation module]
        end

        subgraph AI Abstraction Layer
            AIInterface[AIProvider Interface]
            MockProvider[MockProvider (Default)]
            GeminiProvider[GeminiProvider]
            OllamaProvider[OllamaProvider]
        end
    end

    subgraph Data & External Services
        DB[(Supabase PostgreSQL / SQLite local fallback)]
        ExtAPI[ClinicalTrials.gov REST API v2]
    end

    UI --> API Gateway
    API Gateway --> Core Modules
    NLPMod --> AIInterface
    MatchMod --> AIInterface
    AIInterface --> MockProvider
    AIInterface --> GeminiProvider
    AIInterface --> OllamaProvider
    TrialMod --> ExtAPI
    CoreModules --> DB
```

---

## 3. Core Component Definitions

### 3.1 Frontend Architecture (React + Vite + TS)
- **Role-Based Navigation**: Dynamic UI adjusting layout and permissions for Roles (`admin`, `research_coordinator`, `investigator`, `reviewer`, `viewer`).
- **Clinical Workbench**: Rich interfaces for multi-page PDF verification, side-by-side evidence grounding, visual conflict resolution, what-if scenario testing, and timeline viewing.
- **Evaluation & Disagreement Dashboards**: Recharts visualizations comparing AI decisions against human ground truth, calibration curves, and evaluation metrics across 10 NLP/Matching targets.

### 3.2 Backend Modular Monolith (FastAPI)
- **Modular Boundaries**: Each feature domain (`patients`, `trials`, `matching`, etc.) maintains its own schemas, domain logic, and API endpoints inside `backend/app/modules/`.
- **Deterministic Rule Engine**: Final criteria state (`PASS`, `FAIL`, `UNKNOWN`, `CONFLICT`) is determined strictly by deterministic Python rule evaluation. AI explanations provide contextual commentary but **never** override deterministic decision tree outcomes.
- **External Integration Proxy**: ClinicalTrials.gov API calls are strictly handled server-side to enforce caching, rate limiting, and standard normalization.

### 3.3 AI Service Abstraction Layer
- `AIProvider` abstract base class defining key clinical NLP functions (`extract_patient_facts`, `extract_trial_criteria`, `normalize_medical_terms`, `detect_negation`, `extract_temporal_assertions`, `explain_criterion_decision`, `identify_evidence`, `summarize_document`).
- Standardized return formats strictly enforced using **Pydantic models**.
- Default `AIProvider=mock` ensures the application runs out-of-the-box without requiring API keys.

---

## 4. Key Architectural Patterns
1. **Rule Engine Primacy**: AI assists in extraction and structured formatting; deterministic logic governs final matching state.
2. **Versioned Clinical Truth**: Patient records and trial criteria are versioned immutably. Previous screening runs remain frozen for auditability.
3. **Traceable Grounding**: Every extracted fact links directly to `source_document_id`, `source_page`, and `source_span`.
4. **Asynchronous Re-screening**: Data changes (patient updates or protocol amendments) automatically enqueue non-blocking re-screening background tasks.
