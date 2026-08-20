# REST API Specification

## Base URL
`/api/v1`

All responses return standard JSON wrappers:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2026-08-14T12:00:00Z"
}
```

---

## 1. Authentication & System Health (`/auth`, `/health`)
- `POST /api/v1/auth/login`: Authenticate user session.
- `GET /api/v1/auth/me`: Get active user profile and role privileges.
- `GET /api/v1/health/providers`: System provider health check (`configured`, `missing`, `invalid` status for AI providers & APIs).

## 2. Patients & Documents (`/patients`, `/documents`)
- `GET /api/v1/patients`: List synthetic patient profiles with filtering & pagination.
- `POST /api/v1/patients`: Create synthetic patient record.
- `GET /api/v1/patients/{patient_id}`: Get patient header, timeline, conditions, labs, biomarkers, and medications.
- `POST /api/v1/documents/upload`: Upload synthetic medical PDF document.
- `GET /api/v1/documents/{document_id}/pages`: Retrieve parsed pages & text blocks.
- `POST /api/v1/extraction/run`: Run fact extraction, normalization, negation, and temporal analysis on uploaded document.
- `POST /api/v1/extraction/verify`: Verify and confirm extracted clinical facts.

## 3. Clinical Trials (`/trials`)
- `GET /api/v1/trials/search`: Query external ClinicalTrials.gov API via proxy.
- `POST /api/v1/trials/import`: Ingest trial protocol by NCT ID into backend.
- `GET /api/v1/trials`: List cached local trials.
- `GET /api/v1/trials/{trial_id}`: Retrieve protocol details, version history, and criteria tree.
- `POST /api/v1/trials/{trial_id}/criteria/extract`: Extract & parse criteria logic nodes.

## 4. Matching & Screening (`/matching`)
- `POST /api/v1/matching/screen`: Execute patient-trial matching run. Returns 4-state criterion decision tree.
- `GET /api/v1/matching/runs/{run_id}`: Retrieve detailed screening card with grounded evidence spans.
- `POST /api/v1/matching/what-if`: Execute hypothetical scenario evaluation without saving patient state.
- `GET /api/v1/matching/patient/{patient_id}/timeline`: Retrieve longitudinal eligibility timeline.

## 5. Re-Screening & Impact Analysis (`/rescreening`, `/impact`)
- `GET /api/v1/rescreening/queue`: List pending re-screening jobs.
- `POST /api/v1/rescreening/run`: Trigger queued re-screening jobs.
- `GET /api/v1/impact/trial/{trial_version_id}`: View protocol modification impact report.

## 6. Review, Analytics & Feedback (`/review`, `/analytics`, `/feedback`)
- `POST /api/v1/review/submit`: Submit CRC/Investigator determination & override reason.
- `GET /api/v1/analytics/disagreements`: AI vs Human disagreement report & dispute metrics.
- `POST /api/v1/feedback`: Submit researcher feedback on NLP extractions or decisions.
- `GET /api/v1/audit/logs`: View immutable audit trail logs.

## 7. Evaluation Module (`/evaluation`)
- `GET /api/v1/evaluation/datasets`: List gold-standard benchmark datasets.
- `POST /api/v1/evaluation/run`: Execute benchmark evaluation against active `AIProvider`.
- `GET /api/v1/evaluation/results`: Retrieve performance metrics (Accuracy, Precision, Recall, F1, Negation Acc, Grounding Score).
