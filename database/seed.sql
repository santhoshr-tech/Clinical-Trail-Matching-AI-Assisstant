-- =============================================================================
-- Synthetic Seed Data for Phase 3 Scenarios
-- SAFETY SCOPE: 100% Synthetic and De-identified Data Only
-- 5 Synthetic Seed Scenarios (Fully Eligible, Missing Lab, Conflicting Biomarker, Stale Lab, Exclusion)
-- =============================================================================

-- Profiles
INSERT INTO public.profiles (id, email, full_name, role, organization, source) VALUES
('00000000-0000-0000-0000-000000000001', 'admin@clinicaltrial.ai', 'System Admin User', 'admin', 'Synthetic Clinical Research Institute', 'seed_data'),
('00000000-0000-0000-0000-000000000002', 'coordinator@clinicaltrial.ai', 'Dr. Sarah Connor (CRC)', 'research_coordinator', 'Synthetic Oncology Center', 'seed_data'),
('00000000-0000-0000-0000-000000000003', 'investigator@clinicaltrial.ai', 'Dr. Marcus Vance (PI)', 'investigator', 'Synthetic Oncology Center', 'seed_data')
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Scenario A: Fully Eligible Patient
-- -----------------------------------------------------------------------------
INSERT INTO public.patients (id, mrn_synthetic, age, gender, location, primary_diagnosis, disease_stage, comorbidities, allergies, patient_status, synthetic_data_flag, source) VALUES
('11111111-1111-1111-1111-111111111111', 'SYNTH-SCENARIO-A', 58, 'Female', 'Site 01 - Oncology Wing', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'None', 'Penicillin', 'active', TRUE, 'scenario_seed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.patient_conditions (id, patient_id, raw_value, normalized_value, coding_system, concept_code, stage, verification_status) VALUES
('a1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'Stage IV Non-Small Cell Lung Adenocarcinoma', 'Non-small cell lung cancer', 'SNOMED-CT', '254637007', 'Stage IV', 'verified')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.patient_labs (id, patient_id, raw_value, normalized_value, loinc_code, numeric_value, unit, lab_date, is_stale, verification_status) VALUES
('b1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'ANC lab 2.8 10*3/uL', 'Absolute Neutrophil Count: 2.8 10*3/uL', '26499-4', 2.8, '10*3/uL', '2026-08-01', FALSE, 'verified')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.patient_biomarkers (id, patient_id, raw_value, normalized_value, biomarker_name, status_value, test_date, is_stale, verification_status) VALUES
('c1111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'EGFR Mutation Negative Wild-Type', 'EGFR Mutation: NEGATIVE (WILD_TYPE)', 'EGFR Mutation', 'NEGATIVE', '2026-07-20', FALSE, 'verified'),
('c1111111-1111-1111-1111-111111111112', '11111111-1111-1111-1111-111111111111', 'PD-L1 IHC TPS 60% Positive', 'PD-L1 Expression: POSITIVE (60%)', 'PD-L1 Expression', 'POSITIVE', '2026-07-20', FALSE, 'verified')
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Scenario B: Missing Lab Patient
-- -----------------------------------------------------------------------------
INSERT INTO public.patients (id, mrn_synthetic, age, gender, location, primary_diagnosis, disease_stage, comorbidities, allergies, patient_status, synthetic_data_flag, source) VALUES
('22222222-2222-2222-2222-222222222222', 'SYNTH-SCENARIO-B', 62, 'Male', 'Site 02 - General Clinic', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'Hypertension', 'None', 'active', TRUE, 'scenario_seed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.patient_conditions (id, patient_id, raw_value, normalized_value, coding_system, concept_code, stage, verification_status) VALUES
('a2222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'Metastatic Lung Adenocarcinoma', 'Non-small cell lung cancer', 'SNOMED-CT', '254637007', 'Stage IV', 'verified')
ON CONFLICT (id) DO NOTHING;

-- (ANC Lab is missing for Scenario B)

-- -----------------------------------------------------------------------------
-- Scenario C: Conflicting Biomarker Patient
-- -----------------------------------------------------------------------------
INSERT INTO public.patients (id, mrn_synthetic, age, gender, location, primary_diagnosis, disease_stage, comorbidities, allergies, patient_status, synthetic_data_flag, source) VALUES
('33333333-3333-3333-3333-333333333333', 'SYNTH-SCENARIO-C', 54, 'Female', 'Site 01 - Oncology Wing', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'Asthma', 'Sulfa', 'active', TRUE, 'scenario_seed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.patient_biomarkers (id, patient_id, raw_value, normalized_value, biomarker_name, status_value, test_date, is_stale, verification_status) VALUES
('c3333333-3333-3333-3333-333333333331', '33333333-3333-3333-3333-333333333333', 'Biopsy 1: EGFR Exon 19 Deletion Positive', 'EGFR Mutation: POSITIVE (MUTATED)', 'EGFR Mutation', 'POSITIVE', '2026-06-10', FALSE, 'flagged'),
('c3333333-3333-3333-3333-333333333332', '33333333-3333-3333-3333-333333333333', 'Biopsy 2 (Liquid): EGFR Wild Type Negative', 'EGFR Mutation: NEGATIVE (WILD_TYPE)', 'EGFR Mutation', 'NEGATIVE', '2026-07-15', FALSE, 'flagged')
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Scenario D: Stale Lab Patient
-- -----------------------------------------------------------------------------
INSERT INTO public.patients (id, mrn_synthetic, age, gender, location, primary_diagnosis, disease_stage, comorbidities, allergies, patient_status, synthetic_data_flag, source) VALUES
('44444444-4444-4444-4444-444444444444', 'SYNTH-SCENARIO-D', 71, 'Male', 'Site 03 - Regional Center', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'Type 2 Diabetes', 'Latex', 'active', TRUE, 'scenario_seed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.patient_labs (id, patient_id, raw_value, normalized_value, loinc_code, numeric_value, unit, lab_date, is_stale, verification_status) VALUES
('b4444444-4444-4444-4444-444444444444', '44444444-4444-4444-4444-444444444444', 'ANC lab 2.1 (Old Lab Report 2025)', 'Absolute Neutrophil Count: 2.1 10*3/uL', '26499-4', 2.1, '10*3/uL', '2025-10-01', TRUE, 'unverified')
ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Scenario E: Prior Treatment Exclusion Patient
-- -----------------------------------------------------------------------------
INSERT INTO public.patients (id, mrn_synthetic, age, gender, location, primary_diagnosis, disease_stage, comorbidities, allergies, patient_status, synthetic_data_flag, source) VALUES
('55555555-5555-5555-5555-555555555555', 'SYNTH-SCENARIO-E', 67, 'Female', 'Site 01 - Oncology Wing', 'Stage IV Non-Small Cell Lung Cancer', 'Stage IV', 'None', 'None', 'active', TRUE, 'scenario_seed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.patient_medications (id, patient_id, raw_value, normalized_value, rxnorm_code, dosage, start_date, verification_status) VALUES
('m5555555-5555-5555-5555-555555555555', '55555555-5555-5555-5555-555555555555', 'Pembrolizumab 200mg IV Infusion', 'Pembrolizumab 200mg', '1659152', '200mg', '2026-08-01', 'verified')
ON CONFLICT (id) DO NOTHING;
