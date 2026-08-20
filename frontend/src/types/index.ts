// User Roles
export type UserRole =
  | 'admin'
  | 'research_coordinator'
  | 'investigator'
  | 'reviewer'
  | 'viewer'
  | 'patient';

export interface UserProfile {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
}

export interface PatientPrescription {
  id: string;
  patientId: string;
  fileName: string;
  fileType: string;
  fileSizeBytes: number;
  imageUrl?: string;
  transcribedText: string;
  originalExtractedText: string;
  ocrMethod: string;
  ocrConfidence: number;
  hasIllegibleText: boolean;
  uploadedAt: string;
}

export interface PatientMedicine {
  id: string;
  name: string;
  rxcui?: string;
  dosage?: string;
  frequency?: string;
  indication?: string;
  prescriptionRequired: boolean;
  prescribedInUploadedDoc: boolean;
  sourceCitation: string;
  generalDescription: string;
}

export interface PatientConditionInfo {
  conditionName: string;
  summary: string;
  sourceCitation: string;
}

export interface FoodGuidanceItem {
  category: 'foods_to_eat' | 'foods_to_avoid' | 'drug_food_interaction';
  title: string;
  details: string;
  sourceCitation: string;
}

// Final Criterion Decision States
export type CriterionDecisionState = 'PASS' | 'FAIL' | 'UNKNOWN' | 'CONFLICT';

// Final Screening States
export type ScreeningState =
  | 'eligible_for_review'
  | 'potentially_eligible'
  | 'not_eligible'
  | 'manual_review_required'
  | 'expired_match';

// Provider Status State
export type ProviderStatusState = 'configured' | 'missing' | 'invalid';

export interface ProviderHealthStatus {
  aiProvider: string;
  status: ProviderStatusState;
  geminiStatus: ProviderStatusState;
  ollamaStatus: ProviderStatusState;
  clinicalTrialsApiStatus: ProviderStatusState;
}

// API Response Structure
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string | null;
  timestamp: string;
}

// Synthetic Patient Base Type
export interface PatientHeader {
  id: string;
  mrnSynthetic: string;
  age: number;
  gender: string;
  ethnicity: string;
  status: string;
  createdAt: string;
}
