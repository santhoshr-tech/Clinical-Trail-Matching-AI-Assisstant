-- =============================================================================
-- AI Clinical Trial Matching & Research Assistant Database Schema
-- Prototype Scope: Synthetic & De-identified Data Only
-- Phase 3 Schema Update: Comprehensive Patient Clinical Profile, Facts, Recency, & Versions
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User Roles Enum
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('admin', 'research_coordinator', 'investigator', 'reviewer', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'research_coordinator',
    organization VARCHAR(255) DEFAULT 'Synthetic Clinical Research Institute',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    version INT NOT NULL DEFAULT 1,
    source VARCHAR(100) NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Patients Table (Enhanced with Phase 3 attributes)
CREATE TABLE IF NOT EXISTS public.patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mrn_synthetic VARCHAR(100) NOT NULL UNIQUE,
    age INT NOT NULL,
    gender VARCHAR(50) NOT NULL,
    location VARCHAR(255) DEFAULT 'Synthetic Oncology Clinic - Site 01',
    ethnicity VARCHAR(100) DEFAULT 'De-identified Synthetic',
    primary_diagnosis VARCHAR(255) NOT NULL DEFAULT 'Non-Small Cell Lung Cancer',
    disease_stage VARCHAR(100) DEFAULT 'Stage IV',
    comorbidities TEXT DEFAULT 'Hypertension',
    allergies TEXT DEFAULT 'Penicillin',
    patient_status VARCHAR(50) NOT NULL DEFAULT 'active',
    synthetic_data_flag BOOLEAN NOT NULL DEFAULT TRUE,
    version INT NOT NULL DEFAULT 1,
    source VARCHAR(100) NOT NULL DEFAULT 'synthetic_generator',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Patient Conditions Table (Preserves raw vs normalized value)
CREATE TABLE IF NOT EXISTS public.patient_conditions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    raw_value TEXT NOT NULL,
    normalized_value VARCHAR(255) NOT NULL,
    coding_system VARCHAR(100) DEFAULT 'SNOMED-CT',
    concept_code VARCHAR(100),
    stage VARCHAR(100),
    onset_date DATE,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'unverified', -- unverified, verified, flagged
    version INT NOT NULL DEFAULT 1,
    source VARCHAR(100) NOT NULL DEFAULT 'nlp_extraction',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Patient Medications Table
CREATE TABLE IF NOT EXISTS public.patient_medications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    raw_value TEXT NOT NULL,
    normalized_value VARCHAR(255) NOT NULL,
    rxnorm_code VARCHAR(100),
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    start_date DATE,
    end_date DATE,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'unverified',
    version INT NOT NULL DEFAULT 1,
    source VARCHAR(100) NOT NULL DEFAULT 'nlp_extraction',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Patient Labs Table (Recency & Stale indicators)
CREATE TABLE IF NOT EXISTS public.patient_labs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    raw_value TEXT NOT NULL, -- e.g. "ANC 2.8 k/uL on 2026-08-01"
    normalized_value VARCHAR(255) NOT NULL, -- e.g. "Absolute Neutrophil Count: 2.8 10*3/uL"
    loinc_code VARCHAR(100),
    numeric_value NUMERIC,
    unit VARCHAR(50),
    reference_range VARCHAR(100),
    lab_date DATE NOT NULL,
    is_stale BOOLEAN NOT NULL DEFAULT FALSE,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'unverified',
    version INT NOT NULL DEFAULT 1,
    source VARCHAR(100) NOT NULL DEFAULT 'lab_import',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Patient Biomarkers Table
CREATE TABLE IF NOT EXISTS public.patient_biomarkers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    raw_value TEXT NOT NULL, -- e.g. "PD-L1 IHC 22C3 TPS 60% positive"
    normalized_value VARCHAR(255) NOT NULL, -- e.g. "PD-L1 Expression: POSITIVE (60%)"
    biomarker_name VARCHAR(255) NOT NULL,
    status_value VARCHAR(100) NOT NULL, -- POSITIVE, NEGATIVE, MUTATED, WILD_TYPE
    test_date DATE,
    is_stale BOOLEAN NOT NULL DEFAULT FALSE,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'unverified',
    version INT NOT NULL DEFAULT 1,
    source VARCHAR(100) NOT NULL DEFAULT 'genomic_panel',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Clinical Timeline Table
CREATE TABLE IF NOT EXISTS public.patient_timeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL, -- DIAGNOSIS, LAB_RESULT, MEDICATION_STARTED, BIOMARKER_TEST, SCREENING_RUN
    event_date DATE NOT NULL,
    summary TEXT NOT NULL,
    raw_snippet TEXT,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'verified',
    version INT NOT NULL DEFAULT 1,
    source VARCHAR(100) NOT NULL DEFAULT 'timeline_engine',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Patient Version History Log
CREATE TABLE IF NOT EXISTS public.patient_version_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES public.patients(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    changed_by UUID REFERENCES public.profiles(id),
    snapshot_json JSONB NOT NULL,
    change_reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit Logs Table (Immutable)
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(255),
    payload_json JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Protect audit_logs against modifications (Immutable Rule)
CREATE OR REPLACE FUNCTION block_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable. UPDATE and DELETE operations are prohibited.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS prevent_audit_log_tampering ON public.audit_logs;
CREATE TRIGGER prevent_audit_log_tampering
BEFORE UPDATE OR DELETE ON public.audit_logs
FOR EACH ROW EXECUTE FUNCTION block_audit_log_modification();
