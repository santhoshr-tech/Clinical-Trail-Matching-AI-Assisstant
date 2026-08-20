import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Clinical Trial Matching & Research Assistant"
    VERSION: str = "1.0.0-Phase1"
    API_V1_STR: str = "/api/v1"
    
    # Environment & AI Config
    AI_PROVIDER: str = "gemini"  # Real Gemini provider configured
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    CLINICALTRIALS_API_BASE_URL: str = "https://clinicaltrials.gov/api/v2"
    
    # Database
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # Limits & Logging
    MAX_UPLOAD_SIZE_MB: int = 20
    LOG_LEVEL: str = "INFO"

    # SMTP & Alert Email Credentials
    SMTP_HOST: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ALERT_RESEARCHER_EMAIL: str = "santhoshrpsn200@gmail.com"
    ALERT_PATIENT_EMAIL: str = "2k23cse145@kiot.ac.in"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
