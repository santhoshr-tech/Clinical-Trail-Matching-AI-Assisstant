import os
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date

logger = logging.getLogger("clinical_trial_assistant")

LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "local_prototype.db")

def calculate_stale_flag(lab_date_str: str) -> bool:
    """Calculate if lab/biomarker is stale (> 90 days old)."""
    try:
        fact_date = datetime.strptime(lab_date_str, "%Y-%m-%d").date()
        days_old = (date.today() - fact_date).days
        return days_old > 90
    except Exception:
        return False

def init_db():
    conn = sqlite3.connect(LOCAL_DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    
    # Profiles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'research_coordinator',
        organization TEXT DEFAULT 'Synthetic Clinical Research Institute',
        status TEXT NOT NULL DEFAULT 'active',
        version INTEGER NOT NULL DEFAULT 1,
        source TEXT NOT NULL DEFAULT 'system',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Audit Logs (Immutable)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        payload_json TEXT,
        ip_address TEXT,
        user_agent TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Patients (Enhanced Phase 3 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        mrn_synthetic TEXT NOT NULL UNIQUE,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        location TEXT DEFAULT 'Synthetic Oncology Clinic - Site 01',
        ethnicity TEXT DEFAULT 'De-identified Synthetic',
        primary_diagnosis TEXT NOT NULL DEFAULT 'Non-Small Cell Lung Cancer',
        disease_stage TEXT DEFAULT 'Stage IV',
        comorbidities TEXT DEFAULT 'Hypertension',
        allergies TEXT DEFAULT 'Penicillin',
        patient_status TEXT NOT NULL DEFAULT 'active',
        synthetic_data_flag INTEGER NOT NULL DEFAULT 1,
        version INTEGER NOT NULL DEFAULT 1,
        source TEXT NOT NULL DEFAULT 'synthetic_generator',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Patient Conditions (Raw vs Normalized)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_conditions (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        raw_value TEXT NOT NULL,
        normalized_value TEXT NOT NULL,
        coding_system TEXT DEFAULT 'SNOMED-CT',
        concept_code TEXT,
        stage TEXT,
        onset_date TEXT,
        verification_status TEXT DEFAULT 'unverified',
        version INTEGER DEFAULT 1,
        source TEXT DEFAULT 'nlp_extraction',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Patient Medications
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_medications (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        raw_value TEXT NOT NULL,
        normalized_value TEXT NOT NULL,
        rxnorm_code TEXT,
        dosage TEXT,
        frequency TEXT,
        start_date TEXT,
        end_date TEXT,
        verification_status TEXT DEFAULT 'unverified',
        version INTEGER DEFAULT 1,
        source TEXT DEFAULT 'nlp_extraction',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Patient Labs (Raw vs Normalized + Recency / Stale indicators)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_labs (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        raw_value TEXT NOT NULL,
        normalized_value TEXT NOT NULL,
        loinc_code TEXT,
        numeric_value REAL,
        unit TEXT,
        reference_range TEXT,
        lab_date TEXT NOT NULL,
        is_stale INTEGER DEFAULT 0,
        verification_status TEXT DEFAULT 'unverified',
        version INTEGER DEFAULT 1,
        source TEXT DEFAULT 'lab_import',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Patient Biomarkers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_biomarkers (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        raw_value TEXT NOT NULL,
        normalized_value TEXT NOT NULL,
        biomarker_name TEXT NOT NULL,
        status_value TEXT NOT NULL,
        test_date TEXT,
        is_stale INTEGER DEFAULT 0,
        verification_status TEXT DEFAULT 'unverified',
        version INTEGER DEFAULT 1,
        source TEXT DEFAULT 'genomic_panel',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Patient Timeline
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_timeline (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_date TEXT NOT NULL,
        summary TEXT NOT NULL,
        raw_snippet TEXT,
        verification_status TEXT DEFAULT 'verified',
        version INTEGER DEFAULT 1,
        source TEXT DEFAULT 'timeline_engine',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Trials Table (Phase 4 Schema + Phase 7 Additions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trials (
        id TEXT PRIMARY KEY,
        nct_id TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        official_title TEXT,
        phase TEXT DEFAULT 'Phase 3',
        recruitment_status TEXT DEFAULT 'RECRUITING',
        conditions TEXT,
        interventions TEXT,
        sponsor TEXT DEFAULT 'Synthetic Medical Research Institute',
        brief_summary TEXT,
        eligibility_criteria_text TEXT,
        min_age INTEGER DEFAULT 18,
        max_age INTEGER DEFAULT 85,
        gender TEXT DEFAULT 'ALL',
        locations TEXT,
        biomarkers TEXT,
        source_url TEXT,
        key_metric_name TEXT,
        improvement_direction TEXT DEFAULT 'decrease',
        improvement_threshold_weeks INTEGER DEFAULT 2,
        version INTEGER DEFAULT 1,
        last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Safe column additions for pre-existing trials table
    for col in ["key_metric_name TEXT", "improvement_direction TEXT DEFAULT 'decrease'", "improvement_threshold_weeks INTEGER DEFAULT 2"]:
        try:
            cursor.execute(f"ALTER TABLE trials ADD COLUMN {col};")
        except Exception:
            pass

    # Phase 7: Trial Enrollments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trial_enrollments (
        enrollment_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        trial_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        enrolled_date TEXT NOT NULL,
        baseline_report_id TEXT,
        baseline_metric_value REAL,
        current_metric_value REAL,
        next_expected_report_date TEXT NOT NULL,
        missed_week INTEGER DEFAULT 0,
        missed_since_date TEXT,
        discontinued_reason TEXT,
        last_alert_sent_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
        FOREIGN KEY(trial_id) REFERENCES trials(id) ON DELETE CASCADE
    );
    """)

    # Phase 7: Trial Progress Reports Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trial_progress_reports (
        id TEXT PRIMARY KEY,
        enrollment_id TEXT NOT NULL,
        report_id TEXT,
        week_number INTEGER NOT NULL,
        upload_date TEXT NOT NULL,
        key_metric_name TEXT NOT NULL,
        key_metric_value REAL NOT NULL,
        comparison_to_previous REAL,
        comparison_to_baseline REAL,
        is_improving INTEGER NOT NULL DEFAULT 1,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(enrollment_id) REFERENCES trial_enrollments(enrollment_id) ON DELETE CASCADE
    );
    """)


    # Phase 8: Trial Sites Table (with latitude, longitude, geocoded_at)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trial_sites (
        id TEXT PRIMARY KEY,
        trial_id TEXT NOT NULL,
        site_name TEXT NOT NULL,
        facility_name TEXT,
        city TEXT NOT NULL,
        state TEXT,
        country TEXT NOT NULL DEFAULT 'India',
        zip_code TEXT,
        status TEXT DEFAULT 'RECRUITING',
        latitude REAL,
        longitude REAL,
        geocoded_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(trial_id) REFERENCES trials(id) ON DELETE CASCADE
    );
    """)

    # Phase 8: Safe column migration for trial_sites if table existed prior
    for col_def in [
        ("latitude", "REAL"),
        ("longitude", "REAL"),
        ("geocoded_at", "TIMESTAMP")
    ]:
        try:
            cursor.execute(f"ALTER TABLE trial_sites ADD COLUMN {col_def[0]} {col_def[1]};")
        except Exception:
            pass

    # Phase 8: Chatbot Conversations & Messages Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chatbot_conversations (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        role TEXT NOT NULL DEFAULT 'researcher',
        title TEXT DEFAULT 'Clinical Trial Assistant Session',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chatbot_messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        sender TEXT NOT NULL,
        message_text TEXT NOT NULL,
        retrieved_trial_ids TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(conversation_id) REFERENCES chatbot_conversations(id) ON DELETE CASCADE
    );
    """)

    # Seed trial_sites if empty
    cursor.execute("SELECT COUNT(*) FROM trial_sites;")
    if cursor.fetchone()[0] == 0:
        seed_sites = [
            ("site-001", "t-nct04500000", "Chennai Medical Research Center & Oncology Institute", "Apollo Cancer Centre", "Chennai", "Tamil Nadu", "India", "600006", "RECRUITING", 13.0827, 80.2707),
            ("site-002", "t-nct04500000", "KIOT Clinical Trials Unit", "Knowledge Hospital & Cancer Wing", "Salem", "Tamil Nadu", "India", "637504", "RECRUITING", 11.6643, 78.1460),
            ("site-003", "t-nct04500000", "Coimbatore Regional Medical Center", "Kovai Medical Center", "Coimbatore", "Tamil Nadu", "India", "641014", "RECRUITING", 11.0168, 76.9558),
            ("site-004", "t-nct04500000", "Tata Memorial Hospital & Clinical Research Wing", "Tata Memorial Centre", "Mumbai", "Maharashtra", "India", "400012", "RECRUITING", 19.0028, 72.8427),
            ("site-005", "t-nct04500000", "All India Institute of Medical Sciences (AIIMS)", "AIIMS Clinical Trial Center", "New Delhi", "Delhi", "India", "110029", "RECRUITING", 28.5672, 77.2100),
            ("site-006", "t-nct04500000", "Dana-Farber Cancer Institute", "Thoracic Oncology Research Unit", "Boston", "MA", "United States", "02215", "RECRUITING", 42.3375, -71.1070),
            ("site-007", "t-nct04500000", "Memorial Sloan Kettering Cancer Center", "MSK Precision Medicine Site", "New York", "NY", "United States", "10065", "RECRUITING", 40.7641, -73.9567),
        ]
        cursor.executemany("""
        INSERT INTO trial_sites (id, trial_id, site_name, facility_name, city, state, country, zip_code, status, latitude, longitude, geocoded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, seed_sites)

    # Trial Versions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trial_versions (
        id TEXT PRIMARY KEY,
        trial_id TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        snapshot_json TEXT NOT NULL,
        change_summary TEXT DEFAULT 'Protocol metadata update synced from ClinicalTrials.gov',
        synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(trial_id) REFERENCES trials(id) ON DELETE CASCADE
    );
    """)

    # Trial Criteria Table (Phase 8 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trial_criteria (
        id TEXT PRIMARY KEY,
        trial_id TEXT NOT NULL,
        criterion_type TEXT NOT NULL,
        category TEXT NOT NULL,
        operator TEXT NOT NULL,
        value_primary TEXT,
        value_secondary TEXT,
        unit TEXT,
        temporal_window TEXT,
        is_negated INTEGER DEFAULT 0,
        logic_group TEXT DEFAULT 'AND',
        raw_text TEXT NOT NULL,
        page_number INTEGER DEFAULT 1,
        start_char INTEGER DEFAULT 0,
        end_char INTEGER DEFAULT 0,
        classification_confidence REAL DEFAULT 0.95,
        approval_status TEXT DEFAULT 'pending',
        version INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(trial_id) REFERENCES trials(id) ON DELETE CASCADE
    );
    """)

    # Trial Criteria Versions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trial_criteria_versions (
        id TEXT PRIMARY KEY,
        criterion_id TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        snapshot_json TEXT NOT NULL,
        edited_by TEXT,
        change_summary TEXT DEFAULT 'Criteria updated',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(criterion_id) REFERENCES trial_criteria(id) ON DELETE CASCADE
    );
    """)

    # Patient Trial Match Results Table (Phase 9 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_trial_matches (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        trial_id TEXT NOT NULL,
        overall_status TEXT NOT NULL,
        match_score REAL NOT NULL,
        total_criteria INTEGER NOT NULL,
        passed_count INTEGER NOT NULL,
        failed_count INTEGER NOT NULL,
        unknown_count INTEGER NOT NULL,
        conflict_count INTEGER NOT NULL,
        engine_version TEXT NOT NULL DEFAULT 'v1.0.0-deterministic',
        evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
        FOREIGN KEY(trial_id) REFERENCES trials(id) ON DELETE CASCADE
    );
    """)

    # Patient Criterion Evaluations Table (Phase 9 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_criterion_evaluations (
        id TEXT PRIMARY KEY,
        match_id TEXT NOT NULL,
        criterion_id TEXT NOT NULL,
        criterion_version INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL,
        patient_value TEXT,
        expected_value TEXT,
        rule_used TEXT NOT NULL,
        source_evidence TEXT,
        evidence_reliability TEXT NOT NULL,
        data_date TEXT,
        decision_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(match_id) REFERENCES patient_trial_matches(id) ON DELETE CASCADE,
        FOREIGN KEY(criterion_id) REFERENCES trial_criteria(id) ON DELETE CASCADE
    );
    """)

    # Decision Trace Logs Table (Phase 10 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decision_trace_logs (
        id TEXT PRIMARY KEY,
        match_id TEXT NOT NULL,
        criterion_id TEXT NOT NULL,
        criterion_version INTEGER NOT NULL DEFAULT 1,
        trial_id TEXT NOT NULL,
        trial_version INTEGER NOT NULL DEFAULT 1,
        patient_id TEXT NOT NULL,
        patient_snapshot_id TEXT NOT NULL,
        status TEXT NOT NULL,
        patient_value TEXT,
        expected_value TEXT,
        rule_used TEXT NOT NULL,
        facts_used_json TEXT NOT NULL,
        evidence_items_json TEXT NOT NULL,
        reliability_score REAL NOT NULL,
        reliability_breakdown_json TEXT NOT NULL,
        ai_provider TEXT NOT NULL DEFAULT 'mock',
        ai_model TEXT NOT NULL DEFAULT 'mock-v1',
        prompt_version TEXT NOT NULL DEFAULT 'v1.0',
        matching_engine_version TEXT NOT NULL DEFAULT 'v1.0.0-deterministic',
        human_review_json TEXT,
        override_reason TEXT,
        decision_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completeness_score REAL NOT NULL DEFAULT 1.0,
        FOREIGN KEY(match_id) REFERENCES patient_trial_matches(id) ON DELETE CASCADE,
        FOREIGN KEY(criterion_id) REFERENCES trial_criteria(id) ON DELETE CASCADE
    );
    """)

    # Extracted Clinical Facts Table (Phase 7 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extracted_clinical_facts (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        document_id TEXT,
        category TEXT NOT NULL,
        raw_text TEXT NOT NULL,
        canonical_label TEXT NOT NULL,
        mapping_method TEXT NOT NULL DEFAULT 'snomed_loinc_rxnorm_hybrid',
        mapping_confidence REAL NOT NULL DEFAULT 0.92,
        is_negated INTEGER NOT NULL DEFAULT 0,
        temporal_expression TEXT,
        data_date TEXT,
        is_stale INTEGER NOT NULL DEFAULT 0,
        numeric_value REAL,
        raw_unit TEXT,
        normalized_unit TEXT,
        source_page INTEGER NOT NULL DEFAULT 1,
        start_char INTEGER NOT NULL DEFAULT 0,
        end_char INTEGER NOT NULL DEFAULT 0,
        ai_provider TEXT NOT NULL DEFAULT 'mock',
        ai_model TEXT NOT NULL DEFAULT 'mock-v1',
        prompt_version TEXT NOT NULL DEFAULT 'v1.0',
        review_status TEXT NOT NULL DEFAULT 'pending',
        has_conflict INTEGER NOT NULL DEFAULT 0,
        conflict_details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Fact Conflicts Table (Phase 7 & Phase 11 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fact_conflicts (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        category TEXT NOT NULL,
        existing_fact_id TEXT,
        new_fact_id TEXT,
        conflict_description TEXT NOT NULL,
        source_a_json TEXT,
        source_b_json TEXT,
        resolution_status TEXT NOT NULL DEFAULT 'unresolved',
        resolution_reason TEXT,
        resolved_by TEXT,
        resolved_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Migrations for fact_conflicts columns if table pre-existed
    for col in ["source_a_json TEXT", "source_b_json TEXT", "resolution_reason TEXT", "resolved_by TEXT", "resolved_at TIMESTAMP"]:
        try:
            cursor.execute(f"ALTER TABLE fact_conflicts ADD COLUMN {col};")
        except Exception:
            pass

    # Conflict Resolutions Audit Table (Phase 11 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conflict_resolutions_audit (
        id TEXT PRIMARY KEY,
        conflict_id TEXT NOT NULL,
        patient_id TEXT NOT NULL,
        category TEXT NOT NULL,
        resolution_choice TEXT NOT NULL,
        resolution_reason TEXT NOT NULL,
        resolved_value TEXT NOT NULL,
        resolved_by TEXT NOT NULL,
        resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        rescreening_triggered INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(conflict_id) REFERENCES fact_conflicts(id) ON DELETE CASCADE
    );
    """)

    # Temporal Validations Table (Phase 12 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS temporal_validations (
        id TEXT PRIMARY KEY,
        patient_id TEXT,
        rule_type TEXT NOT NULL,
        event_date TEXT,
        reference_date TEXT,
        days_difference INTEGER,
        date_quality TEXT NOT NULL,
        is_stale INTEGER NOT NULL DEFAULT 0,
        temporal_explanation TEXT NOT NULL,
        requires_human_review INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Patient Eligibility Timeline Table (Phase 12 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_eligibility_timeline (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        trial_id TEXT NOT NULL,
        criterion_id TEXT NOT NULL,
        old_status TEXT NOT NULL,
        new_status TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        trigger_reason TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # What-If Scenarios Table (Phase 13 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS what_if_scenarios (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        trial_id TEXT NOT NULL,
        scenario_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        modifications_json TEXT NOT NULL,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # What-If Audit Logs Table (Phase 13 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS what_if_audit_logs (
        id TEXT PRIMARY KEY,
        scenario_id TEXT NOT NULL,
        patient_id TEXT NOT NULL,
        trial_id TEXT NOT NULL,
        original_overall_status TEXT NOT NULL,
        simulated_overall_status TEXT NOT NULL,
        original_score REAL NOT NULL,
        simulated_score REAL NOT NULL,
        deltas_json TEXT NOT NULL,
        executed_by TEXT NOT NULL,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(scenario_id) REFERENCES what_if_scenarios(id) ON DELETE CASCADE
    );
    """)

    # Re-Screening Jobs Table (Phase 14 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS re_screening_jobs (
        id TEXT PRIMARY KEY,
        trigger_type TEXT NOT NULL,
        trigger_source_id TEXT NOT NULL,
        patient_id TEXT,
        trial_id TEXT,
        idempotency_key TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        retry_count INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    );
    """)

    # Screening History Table (Phase 14 Schema - Immutable Historical Runs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS screening_history (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        trial_id TEXT NOT NULL,
        overall_status TEXT NOT NULL,
        match_score REAL NOT NULL,
        results_json TEXT NOT NULL,
        trigger_job_id TEXT,
        evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Coordinator Notifications Table (Phase 14 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coordinator_notifications (
        id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        patient_id TEXT NOT NULL,
        trial_id TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(job_id) REFERENCES re_screening_jobs(id) ON DELETE CASCADE
    );
    """)

    # Researcher Feedback Table (Phase 15 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS researcher_feedback (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        trial_id TEXT NOT NULL,
        criterion_id TEXT NOT NULL,
        ai_decision TEXT NOT NULL,
        human_decision TEXT NOT NULL,
        agreement_status TEXT NOT NULL,
        error_type TEXT NOT NULL,
        disagreement_category TEXT,
        override_reason TEXT,
        reviewer_id TEXT NOT NULL,
        model_version TEXT NOT NULL,
        prompt_version TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Feedback Audit Logs Table (Phase 15 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback_audit_logs (
        id TEXT PRIMARY KEY,
        feedback_id TEXT NOT NULL,
        reviewer_id TEXT NOT NULL,
        action TEXT NOT NULL,
        rationale TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(feedback_id) REFERENCES researcher_feedback(id) ON DELETE CASCADE
    );
    """)

    # Gold Standard Test Cases Table (Phase 16 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gold_standard_test_cases (
        id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        input_data_json TEXT NOT NULL,
        expected_label TEXT NOT NULL,
        dataset_version TEXT NOT NULL DEFAULT 'v1.0-synthetic-gold-standard',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Evaluation Runs Table (Phase 16 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evaluation_runs (
        id TEXT PRIMARY KEY,
        dataset_version TEXT NOT NULL,
        total_test_cases INTEGER NOT NULL,
        overall_f1 REAL NOT NULL,
        results_json TEXT NOT NULL,
        executed_by TEXT NOT NULL DEFAULT 'auto_eval_runner',
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Patient Documents Table (Enhanced Phase 5 Schema)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_documents (
        id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_type TEXT DEFAULT 'pdf',
        document_category TEXT NOT NULL DEFAULT 'patient_report',
        file_size_bytes INTEGER DEFAULT 0,
        mime_type TEXT DEFAULT 'application/pdf',
        file_path TEXT,
        storage_path TEXT,
        page_count INTEGER DEFAULT 1,
        ocr_applied INTEGER DEFAULT 0,
        processing_status TEXT DEFAULT 'completed',
        error_message TEXT,
        version INTEGER DEFAULT 1,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # Document Pages Table (Page-Level Evidence & Spans)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_pages (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        page_text TEXT NOT NULL,
        char_count INTEGER DEFAULT 0,
        source_spans_json TEXT,
        ocr_applied INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(document_id) REFERENCES patient_documents(id) ON DELETE CASCADE
    );
    """)

    # Document Version History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document_versions (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        version_number INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        change_summary TEXT DEFAULT 'Document version uploaded',
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(document_id) REFERENCES patient_documents(id) ON DELETE CASCADE
    );
    """)

    # Extracted Facts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extracted_facts (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        patient_id TEXT NOT NULL,
        fact_type TEXT NOT NULL,
        raw_value TEXT NOT NULL,
        normalized_value TEXT NOT NULL,
        code TEXT,
        confidence_score REAL DEFAULT 0.95,
        is_negated INTEGER DEFAULT 0,
        temporality TEXT DEFAULT 'current',
        page_number INTEGER DEFAULT 1,
        verification_status TEXT DEFAULT 'unverified',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(document_id) REFERENCES patient_documents(id) ON DELETE CASCADE,
        FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE
    );
    """)

    # User Preferences Table (Language, Portal settings)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_preferences (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL UNIQUE,
        preferred_language TEXT NOT NULL DEFAULT 'English',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Patient Prescriptions Table
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

    # Seed Default Profiles if empty or add patient profile
    cursor.execute("SELECT COUNT(*) FROM profiles;")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
        INSERT INTO profiles (id, email, full_name, role, organization, source) VALUES (?, ?, ?, ?, ?, ?);
        """, [
            ('00000000-0000-0000-0000-000000000001', 'admin@clinicaltrial.ai', 'System Admin User', 'admin', 'Synthetic Clinical Research Institute', 'seed_data'),
            ('00000000-0000-0000-0000-000000000002', 'coordinator@clinicaltrial.ai', 'Dr. Sarah Connor (CRC)', 'research_coordinator', 'Synthetic Oncology Center', 'seed_data'),
            ('00000000-0000-0000-0000-000000000003', 'investigator@clinicaltrial.ai', 'Dr. Marcus Vance (PI)', 'investigator', 'Synthetic Oncology Center', 'seed_data'),
            ('00000000-0000-0000-0000-000000000004', 'reviewer@clinicaltrial.ai', 'Dr. Elena Rostova', 'reviewer', 'Quality Governance Board', 'seed_data'),
            ('00000000-0000-0000-0000-000000000005', 'viewer@clinicaltrial.ai', 'Observer Demo', 'viewer', 'Synthetic Analytics Unit', 'seed_data'),
            ('00000000-0000-0000-0000-000000000006', 'patient@clinicaltrial.ai', 'Jane Doe (Patient)', 'patient', 'Synthetic Oncology Clinic - Site 01', 'seed_data')
        ])
    else:
        cursor.execute("""
        INSERT OR IGNORE INTO profiles (id, email, full_name, role, organization, source)
        VALUES ('00000000-0000-0000-0000-000000000006', 'patient@clinicaltrial.ai', 'Jane Doe (Patient)', 'patient', 'Synthetic Oncology Clinic - Site 01', 'seed_data');
        """)

    seed_synthetic_scenarios(cursor)
    seed_synthetic_trials(cursor)

    conn.commit()
    conn.close()

def seed_synthetic_trials(cursor):
    """Seed synthetic fallback trials for Phase 4."""
    synthetic_trials = [
        (
            't-nct04500000', 'NCT04500000',
            'Phase 3 Study of Pembrolizumab Plus Chemotherapy in Advanced NSCLC',
            'A Randomized, Double-Blind Phase 3 Trial Evaluating Anti-PD-1 Therapy in First-Line Non-Small Cell Lung Cancer',
            'Phase 3', 'RECRUITING',
            'Non-Small Cell Lung Cancer, NSCLC, Lung Adenocarcinoma',
            'Pembrolizumab, Carboplatin, Pemetrexed',
            'Global Oncology Research Group',
            'Evaluating efficacy of first-line pembrolizumab combination therapy in stage IV NSCLC patients.',
            'Inclusion Criteria:\n1. Age >= 18 years.\n2. Histologically confirmed Stage IV NSCLC.\n3. ANC >= 1.5 x 10^9/L.\n4. PD-L1 TPS >= 50%.\n\nExclusion Criteria:\n1. Active EGFR mutation or ALK translocation.\n2. Prior anti-PD-1/PD-L1 therapy.\n3. Active CNS metastases.',
            18, 80, 'ALL', 'Site 01 - Oncology Wing, Site 02 - General Clinic',
            'PD-L1 Expression, EGFR Mutation, ALK Rearrangement',
            'https://clinicaltrials.gov/study/NCT04500000', 1
        ),
        (
            't-nct04611111', 'NCT04611111',
            'Targeted Osimertinib Evaluation Trial in EGFR-Mutated Stage IV NSCLC',
            'Double-Blind Study of Third-Generation EGFR Tyrosine Kinase Inhibitor in Advanced Lung Cancer',
            'Phase 2', 'RECRUITING',
            'Non-Small Cell Lung Cancer, EGFR-Mutated NSCLC',
            'Osimertinib, Chemotherapy',
            'Precision Therapeutics Consortium',
            'Assessing targeted EGFR inhibitor efficacy in patients with exon 19 deletion or L858R mutation.',
            'Inclusion Criteria:\n1. Age >= 18 years.\n2. Confirmed EGFR Exon 19 deletion or L858R mutation.\n3. Stage IV NSCLC.\n\nExclusion Criteria:\n1. EGFR wild-type.\n2. Severe cardiac dysfunction.',
            18, 85, 'ALL', 'Site 01 - Oncology Wing',
            'EGFR Mutation',
            'https://clinicaltrials.gov/study/NCT04611111', 1
        ),
        (
            't-nct04722222', 'NCT04722222',
            'Immunotherapy Safety and Efficacy Study in Refractory Solid Tumors',
            'Phase 1/2 Dose-Escalation Study of Novel Checkpoint Inhibitor in Advanced Malignancies',
            'Phase 1', 'ACTIVE_NOT_RECRUITING',
            'Solid Tumors, Melanoma, NSCLC',
            'Novel Anti-CTLA-4 Antibody',
            'Synthetic BioPharma',
            'Phase 1/2 safety assessment in patients with advanced solid organ malignancies.',
            'Inclusion Criteria:\n1. Age >= 18 years.\n2. Advanced solid tumor refractory to standard therapy.\n\nExclusion Criteria:\n1. Autoimmune disease.',
            18, 75, 'ALL', 'Site 03 - Regional Center',
            'CTLA-4, Tumor Mutational Burden',
            'https://clinicaltrials.gov/study/NCT04722222', 1
        )
    ]

    for trial in synthetic_trials:
        cursor.execute("SELECT COUNT(*) FROM trials WHERE id = ?;", (trial[0],))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO trials (
                id, nct_id, title, official_title, phase, recruitment_status,
                conditions, interventions, sponsor, brief_summary, eligibility_criteria_text,
                min_age, max_age, gender, locations, biomarkers, source_url, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, trial)

            # Insert initial version history
            snapshot_json = f'{{"nct_id": "{trial[1]}", "title": "{trial[2]}", "phase": "{trial[4]}", "status": "{trial[5]}"}}'
            cursor.execute("""
            INSERT INTO trial_versions (id, trial_id, version_number, snapshot_json, change_summary)
            VALUES (?, ?, 1, ?, 'Initial synthetic protocol import');
            """, (f"v1-{trial[0]}", trial[0], snapshot_json))

def seed_synthetic_scenarios(cursor):
    """Seed the 5 Synthetic Scenarios for Phase 3 evaluation testing."""
    scenarios = [
        ('11111111-1111-1111-1111-111111111111', 'SYNTH-SCENARIO-A', 58, 'Female', 'Site 01 - Oncology Wing', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'None', 'Penicillin', 'active'),
        ('22222222-2222-2222-2222-222222222222', 'SYNTH-SCENARIO-B', 62, 'Male', 'Site 02 - General Clinic', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'Hypertension', 'None', 'active'),
        ('33333333-3333-3333-3333-333333333333', 'SYNTH-SCENARIO-C', 54, 'Female', 'Site 01 - Oncology Wing', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'Asthma', 'Sulfa', 'active'),
        ('44444444-4444-4444-4444-444444444444', 'SYNTH-SCENARIO-D', 71, 'Male', 'Site 03 - Regional Center', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'Type 2 Diabetes', 'Latex', 'active'),
        ('55555555-5555-5555-5555-555555555555', 'SYNTH-SCENARIO-E', 67, 'Female', 'Site 01 - Oncology Wing', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'None', 'None', 'active'),
    ]

    for pat in scenarios:
        cursor.execute("SELECT COUNT(*) FROM patients WHERE id = ?;", (pat[0],))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
            INSERT INTO patients (id, mrn_synthetic, age, gender, location, primary_diagnosis, disease_stage, comorbidities, allergies, patient_status, synthetic_data_flag, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'scenario_seed');
            """, pat)

    # Scenario A Facts (Fully Eligible)
    cursor.execute("SELECT COUNT(*) FROM patient_labs WHERE patient_id = '11111111-1111-1111-1111-111111111111';")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO patient_labs (id, patient_id, raw_value, normalized_value, loinc_code, numeric_value, unit, lab_date, is_stale, verification_status)
        VALUES ('b1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'ANC lab 2.8 10*3/uL', 'Absolute Neutrophil Count: 2.8 10*3/uL', '26499-4', 2.8, '10*3/uL', '2026-08-01', 0, 'verified');
        """)
        cursor.execute("""
        INSERT INTO patient_biomarkers (id, patient_id, raw_value, normalized_value, biomarker_name, status_value, test_date, is_stale, verification_status)
        VALUES ('c1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'EGFR Mutation Negative Wild-Type', 'EGFR Mutation: NEGATIVE (WILD_TYPE)', 'EGFR Mutation', 'NEGATIVE', '2026-07-20', 0, 'verified');
        """)
        cursor.execute("""
        INSERT INTO patient_biomarkers (id, patient_id, raw_value, normalized_value, biomarker_name, status_value, test_date, is_stale, verification_status)
        VALUES ('c1111111-1111-1111-1111-111111111112', '11111111-1111-1111-1111-111111111111', 'PD-L1 IHC TPS 60% Positive', 'PD-L1 Expression: POSITIVE (60%)', 'PD-L1 Expression', 'POSITIVE', '2026-07-20', 0, 'verified');
        """)
        cursor.execute("""
        INSERT INTO patient_timeline (id, patient_id, event_type, event_date, summary, raw_snippet, verification_status)
        VALUES ('t1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'DIAGNOSIS', '2026-06-15', 'Diagnosed with Stage IV NSCLC', 'Pathology report confirms adenocarcinoma stage IV', 'verified');
        """)

    # Scenario C Facts (Conflicting Biomarker)
    cursor.execute("SELECT COUNT(*) FROM patient_biomarkers WHERE patient_id = '33333333-3333-3333-3333-333333333333';")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO patient_biomarkers (id, patient_id, raw_value, normalized_value, biomarker_name, status_value, test_date, is_stale, verification_status)
        VALUES ('c3333333-3333-3333-3333-333333333331', '33333333-3333-3333-3333-333333333333', 'Biopsy 1: EGFR Exon 19 Deletion Positive', 'EGFR Mutation: POSITIVE (MUTATED)', 'EGFR Mutation', 'POSITIVE', '2026-06-10', 0, 'flagged');
        """)
        cursor.execute("""
        INSERT INTO patient_biomarkers (id, patient_id, raw_value, normalized_value, biomarker_name, status_value, test_date, is_stale, verification_status)
        VALUES ('c3333333-3333-3333-3333-333333333332', '33333333-3333-3333-3333-333333333333', 'Biopsy 2 (Liquid): EGFR Wild Type Negative', 'EGFR Mutation: NEGATIVE (WILD_TYPE)', 'EGFR Mutation', 'NEGATIVE', '2026-07-15', 0, 'flagged');
        """)

    # Scenario D Facts (Stale Lab)
    cursor.execute("SELECT COUNT(*) FROM patient_labs WHERE patient_id = '44444444-4444-4444-4444-444444444444';")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO patient_labs (id, patient_id, raw_value, normalized_value, loinc_code, numeric_value, unit, lab_date, is_stale, verification_status)
        VALUES ('b4444444-4444-4444-4444-444444444444', '44444444-4444-4444-4444-444444444444', 'ANC lab 2.1 (Old Lab Report 2025)', 'Absolute Neutrophil Count: 2.1 10*3/uL', '26499-4', 2.1, '10*3/uL', '2025-10-01', 1, 'unverified');
        """)

    # Scenario E Facts (Prior Treatment Exclusion)
    cursor.execute("SELECT COUNT(*) FROM patient_medications WHERE patient_id = '55555555-5555-5555-5555-555555555555';")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO patient_medications (id, patient_id, raw_value, normalized_value, rxnorm_code, dosage, start_date, verification_status)
        VALUES ('m5555555-5555-5555-5555-555555555555', '55555555-5555-5555-5555-555555555555', 'Pembrolizumab 200mg IV Infusion', 'Pembrolizumab 200mg', '1659152', '200mg', '2026-08-01', 'verified');
        """)

def get_db_connection():
    conn = sqlite3.connect(LOCAL_DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn
