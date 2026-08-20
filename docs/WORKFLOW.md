# System Workflow & Core Pipeline

## 1. End-to-End Clinical Trial Matching Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Coordinator as Research Coordinator / Investigator
    participant UI as Frontend Interface
    participant API as FastAPI Backend
    participant DocEngine as Document Parsing & OCR Engine
    participant NLPEngine as Clinical NLP & AI Provider
    participant RuleEngine as Deterministic Match Engine
    participant DB as PostgreSQL Database

    %% Patient Ingestion Workflow
    rect rgb(245, 247, 250)
    note right of Coordinator: Phase 1: Patient & Document Ingestion
    Coordinator->>UI: Upload synthetic clinical PDF / record
    UI->>API: POST /api/documents/upload
    API->>DocEngine: Parse PDF (PyMuPDF / Tesseract OCR)
    DocEngine-->>API: Document Pages & Spans
    API->>NLPEngine: Extract Facts, Normalization & Negation & Temporal
    NLPEngine-->>API: Structured Clinical Facts + Spans
    API->>DB: Save Patient, Documents, Pages, Facts, Timelines
    API-->>UI: Return extracted facts with page grounding
    Coordinator->>UI: Review & approve extracted facts
    UI->>API: POST /api/extraction/verify
    API->>DB: Update verification status
    end

    %% Trial Ingestion Workflow
    rect rgb(240, 248, 255)
    note right of Coordinator: Phase 2: Trial Protocol Import & Extraction
    Coordinator->>UI: Search & select ClinicalTrials.gov NCT ID
    UI->>API: POST /api/trials/import/{nct_id}
    API->>DB: Ingest Trial Protocol & Criteria
    API->>NLPEngine: Extract Criteria & Logic Nodes
    NLPEngine-->>API: Structured Inclusion/Exclusion Criteria Rules
    API->>DB: Save Trial Criteria Versions & Logic Nodes
    end

    %% Screening & Matching Pipeline
    rect rgb(255, 248, 240)
    note right of Coordinator: Phase 3: Patient-Trial Screening Execution
    Coordinator->>UI: Initiate Patient-Trial Matching
    UI->>API: POST /api/matching/screen
    API->>RuleEngine: Fetch Patient Facts & Trial Criteria Version
    RuleEngine->>RuleEngine: Evaluate Negation, Temporal, Lab Ranges & Conflicts
    RuleEngine-->>API: Returns State per Criterion (PASS, FAIL, UNKNOWN, CONFLICT)
    API->>DB: Save Screening Run, Results, Evidence Spans, Audit Trail
    API-->>UI: Return Structured Screening Card
    end

    %% Coordinator Review & Decision
    rect rgb(245, 255, 245)
    note right of Coordinator: Phase 4: Human Review & Feedback
    Coordinator->>UI: Review criterion evidence & verify grounding
    Coordinator->>UI: Override decision or confirm status
    UI->>API: POST /api/review/submit
    API->>DB: Save Human Review, Override Reason, Disagreement Analytics
    end
```

---

## 2. Detailed Pipeline Stages

### Stage 1: Document Processing & Fact Extraction
1. **Document Upload**: PDF parsed into page-level text blocks (`document_pages`).
2. **Fact Extraction**: Rule-based regex + AI Provider extract conditions, labs, medications, biomarkers, and procedures.
3. **Evidence Linkage**: Every fact registers character offsets (`start_char`, `end_char`) and page index for visual highlighting.

### Stage 2: Normalization, Negation & Temporal Processing
1. **Terminology Mapping**: Maps raw terms to standardized labels (SNOMED, RxNorm, LOINC, ICD-10) with mapping method & confidence. Preserves raw text.
2. **Negation Detection**: Identifies scope of negation triggers (e.g., "denies shortness of breath", "negative for EGFR mutation").
3. **Temporal Reasoning**: Computes reference date deltas (e.g., "within last 6 months", "prior to enrollment").

### Stage 3: Deterministic Rule Engine Matching
For each trial criterion:
1. **Fact Retrieval**: Query normalized facts active during criterion temporal window.
2. **Conflict Check**: If contradictory evidence exists (e.g., two different biomarker statuses in the same window), state becomes `CONFLICT`.
3. **Missing Data Check**: If required test/lab is absent, state becomes `UNKNOWN`.
4. **Rule Evaluation**:
   - Inclusion matched & met $\rightarrow$ `PASS`
   - Inclusion matched & violated $\rightarrow$ `FAIL`
   - Exclusion matched & present $\rightarrow$ `FAIL`
   - Exclusion matched & absent $\rightarrow$ `PASS`

### Stage 4: Continuous Re-screening & Criteria Impact
- When patient lab/condition or trial criterion version changes:
  1. Background job detects affected patient-trial pairs (`re_screening_jobs`).
  2. Re-runs screening pipeline.
  3. Generates diff comparing `old_decision` vs `new_decision`.
  4. Alerts assigned coordinator if status changed.
