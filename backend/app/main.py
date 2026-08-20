from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.schemas.common import ApiResponse, ProviderHealthStatus, ProviderStatusState
from app.core.db import init_db

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("clinical_trial_assistant")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Modular-monolith decision-support application for AI-assisted clinical trial pre-screening."
)

@app.on_event("startup")
def startup_event():
    logger.info("Initializing database schemas on app startup...")
    init_db()

# Enable CORS for frontend Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global API exception handler for structured error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": "Internal server error occurred",
            "detail": str(exc),
            "timestamp": settings.VERSION
        }
    )

# Task 7: Health Check Endpoint
@app.get("/health", response_model=ApiResponse[dict])
async def health_check():
    return ApiResponse(data={
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "aiProvider": settings.AI_PROVIDER
    })

# Task 8: Config Status Endpoint (Reports ONLY configured / missing / invalid)
@app.get("/api/config/status", response_model=ApiResponse[ProviderHealthStatus])
async def config_status():
    # Evaluate Gemini Key Status
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.strip() == "":
        gemini_status = ProviderStatusState.MISSING
    elif "placeholder" in settings.GEMINI_API_KEY.lower() or "your-" in settings.GEMINI_API_KEY.lower():
        gemini_status = ProviderStatusState.INVALID
    else:
        gemini_status = ProviderStatusState.CONFIGURED

    # Evaluate Ollama Base URL
    if not settings.OLLAMA_BASE_URL:
        ollama_status = ProviderStatusState.MISSING
    else:
        ollama_status = ProviderStatusState.CONFIGURED

    # ClinicalTrials API Status
    ct_status = ProviderStatusState.CONFIGURED if settings.CLINICALTRIALS_API_BASE_URL else ProviderStatusState.MISSING

    # Active Provider Status
    if settings.AI_PROVIDER == "gemini":
        active_status = gemini_status
    elif settings.AI_PROVIDER == "ollama":
        active_status = ollama_status
    else:
        active_status = ProviderStatusState.CONFIGURED  # Mock provider is always ready/configured

    return ApiResponse(
        data=ProviderHealthStatus(
            aiProvider=settings.AI_PROVIDER,
            status=active_status,
            geminiStatus=gemini_status,
            ollamaStatus=ollama_status,
            clinicalTrialsApiStatus=ct_status
        )
    )

# Import and mount all 22 module routers under /api/v1
from app.modules.auth.router import router as auth_router
from app.modules.patients.router import router as patients_router
from app.modules.documents.router import router as documents_router
from app.modules.extraction.router import router as extraction_router
from app.modules.normalization.router import router as normalization_router
from app.modules.terminology.router import router as terminology_router
from app.modules.trials.router import router as trials_router
from app.modules.protocols.router import router as protocols_router
from app.modules.criteria.router import router as criteria_router
from app.modules.temporal.router import router as temporal_router
from app.modules.conflicts.router import router as conflicts_router
from app.modules.matching.router import router as matching_router
from app.modules.evidence.router import router as evidence_router
from app.modules.review.router import router as review_router
from app.modules.what_if.router import router as what_if_router
from app.modules.rescreening.router import router as rescreening_router
from app.modules.impact_analysis.router import router as impact_router
from app.modules.feedback.router import router as feedback_router
from app.modules.evaluation.router import router as evaluation_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.notifications.router import router as notifications_router
from app.modules.audit.router import router as audit_router
from app.modules.security.router import router as security_router
from app.modules.patient_portal.router import router as patient_portal_router
from app.modules.enrollment.router import router as enrollment_router
from app.modules.location.router import router as location_router
from app.modules.chatbot.router import router as chatbot_router
from app.modules.enrollment.service import check_and_alert_missed_weeks

@app.on_event("startup")
def startup_event():
    logger.info("Initializing database schemas on app startup...")
    init_db()
    try:
        logger.info("Running daily scheduled missed-week check...")
        check_and_alert_missed_weeks()
    except Exception as e:
        logger.warning(f"Startup missed-week check failed: {e}")

api_v1_prefix = settings.API_V1_STR

app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(patients_router, prefix=api_v1_prefix)
app.include_router(documents_router, prefix=api_v1_prefix)
app.include_router(extraction_router, prefix=api_v1_prefix)
app.include_router(normalization_router, prefix=api_v1_prefix)
app.include_router(terminology_router, prefix=api_v1_prefix)
app.include_router(trials_router, prefix=api_v1_prefix)
app.include_router(protocols_router, prefix=api_v1_prefix)
app.include_router(criteria_router, prefix=api_v1_prefix)
app.include_router(temporal_router, prefix=api_v1_prefix)
app.include_router(conflicts_router, prefix=api_v1_prefix)
app.include_router(matching_router, prefix=api_v1_prefix)
app.include_router(evidence_router, prefix=api_v1_prefix)
app.include_router(review_router, prefix=api_v1_prefix)
app.include_router(what_if_router, prefix=api_v1_prefix)
app.include_router(rescreening_router, prefix=api_v1_prefix)
app.include_router(impact_router, prefix=api_v1_prefix)
app.include_router(feedback_router, prefix=api_v1_prefix)
app.include_router(evaluation_router, prefix=api_v1_prefix)
app.include_router(dashboard_router, prefix=api_v1_prefix)
app.include_router(notifications_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)
app.include_router(security_router, prefix=api_v1_prefix)
app.include_router(patient_portal_router, prefix=api_v1_prefix)
app.include_router(enrollment_router, prefix=api_v1_prefix)
app.include_router(location_router, prefix=api_v1_prefix)
app.include_router(chatbot_router, prefix=api_v1_prefix)


