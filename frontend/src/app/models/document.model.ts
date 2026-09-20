export type DocumentType =
  | 'PRESCRIPTION'
  | 'DOCTOR_CONSULTATION'
  | 'MEDICAL_REPORT'
  | 'MEDICINE_BILL'
  | 'INSURANCE_POLICY'
  | 'REIMBURSEMENT_POLICY'
  | 'OTHER';

export interface ExtractedMedicine {
  name: string;
  dosage?: string;
  frequency?: string;
  duration?: string;
  instructions?: string;
}

export interface DoctorHospitalInfo {
  doctor_name?: string;
  hospital_name?: string;
  department?: string;
  qualifications?: string;
  registration_no?: string;
  contact?: string;
}

export interface DocumentDates {
  document_date?: string;
  consultation_date?: string;
  valid_until?: string;
  admission_date?: string;
  discharge_date?: string;
}

export interface PolicyClause {
  title: string;
  description: string;
  category?: string;
}

export interface PolicyReimbursementInfo {
  coverage_amount?: string;
  claim_limit?: string;
  eligible_expenses: string[];
  ineligible_expenses: string[];
  clauses: PolicyClause[];
  co_pay_percentage?: string;
  claim_submission_deadline?: string;
}

export interface ExtractedDocumentData {
  document_type: DocumentType;
  confidence_score: number;
  patient_name?: string;
  medicines: ExtractedMedicine[];
  doctor_hospital?: DoctorHospitalInfo;
  dates?: DocumentDates;
  policy_reimbursement?: PolicyReimbursementInfo;
  diagnosis_findings: string[];
  total_amount?: string;
  clinical_notes_summary?: string;
  raw_text_snippet?: string;
  disclaimer: string;
}

export interface ProcessingStage {
  stage: string;
  message: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  timestamp: string;
}

export interface DocumentUploadResponse {
  id: string;
  file_name: string;
  file_size: number;
  processing_status: string;
  stages: ProcessingStage[];
  extracted_data?: ExtractedDocumentData;
  created_at: string;
  error_message?: string;
}

export interface DocumentListItem {
  id: string;
  file_name: string;
  file_size: number;
  document_type: DocumentType;
  doctor_or_hospital?: string;
  document_date?: string;
  medicines_count: number;
  processing_status: string;
  created_at: string;
}
