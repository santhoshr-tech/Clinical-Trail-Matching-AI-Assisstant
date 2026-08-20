# Data Safety, Compliance & Security Architecture

## 1. Safety Scope & Regulatory Disclaimers

> **MANDATORY SYSTEM DISCLAIMERS:**  
> 1. **Research Prototype & Decision-Support Tool Only**: This system does **not** provide final medical advice, replace an investigator, or automatically enroll a patient.  
> 2. **Human-in-the-Loop Requirement**: Final eligibility determinations **must** be reviewed and signed off by an authorized clinical research coordinator (CRC) or principal investigator (PI).  
> 3. **Non-Regulatory Claim**: This system is an educational and research prototype. It does **not** claim compliance with HIPAA, GDPR, 21 CFR Part 11, or formal regulatory approval by FDA/EMA/CDSCO.

---

## 2. Data Protection Guidelines

1. **Synthetic & De-Identified Data Only**: All patient profiles, clinical documents, labs, and timeline events generated or ingested must be 100% synthetic or de-identified.
2. **Prohibition of Real PHI**: Real patient records, government IDs (e.g. Aadhaar, SSN), personal phone numbers, physical addresses, or hospital MRNs are strictly forbidden.
3. **No External PHI Leakage**: Real Protected Health Information (PHI) must never be transmitted to external LLM APIs (Gemini/Ollama), browser agents, console logs, or third-party tracking services.
4. **UI Security Badges**:
   - Persistent banner on top of every page displaying: **"Synthetic / De-identified Research Prototype"**.
   - Footer & Modal disclaimer: **"AI-assisted pre-screening requires qualified human review."**

---

## 3. Secret Management & API Security

1. **Zero Hardcoded Secrets**: No API keys, database credentials, or secret tokens may be committed to source code or version control.
2. **Environment Configuration**: Secrets are loaded exclusively via environment variables (`.env`).
3. **Template-Only Commits**: Only `.env.example` containing non-sensitive default placeholders is checked into Git repository.
4. **Chat Privacy**: Users must never be requested to paste live API keys in chat or prompts.
5. **Backend Secret Scope**: Frontend applications must never expose or store service-role keys or AI provider API keys. All LLM calls route strictly through backend API proxies.
6. **Graceful Fallback / Mock Mode**: When no valid API key is present in environment, the system gracefully defaults to `AI_PROVIDER=mock`, returning deterministic mock outputs without throwing uncaught authentication errors.
7. **Startup Health Verification**: At backend startup, provider checks inspect keys and output sanitized status messages (`configured`, `missing`, or `invalid`) without printing key strings.

---

## 4. Authorization & Audit Trail

### 4.1 Role-Based Access Control (RBAC)
- **admin**: Full system management, provider configuration, audit log inspection.
- **research_coordinator**: Synthetic patient management, document upload, criteria extraction verification, matching execution.
- **investigator**: Final review sign-off, decision override, trial protocol management.
- **reviewer**: Read-only verification and feedback submission.
- **viewer**: Read-only summary dashboard access.

### 4.2 Immutable Audit Trail
Every system action (screening execution, human override, document ingestion, protocol edit) creates an immutable record in `audit_logs`:
- Action name & timestamp
- User UUID & assigned role
- Target entity ID & payload snapshot
- IP address & client identifier
- Audit records are append-only and cannot be updated or deleted.
