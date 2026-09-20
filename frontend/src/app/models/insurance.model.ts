export type PolicyUploadCategory =
  | 'COMPANY_HEALTH_INSURANCE'
  | 'EMPLOYEE_REIMBURSEMENT'
  | 'INSURANCE_TERMS_CONDITIONS'
  | 'PHARMACY_REIMBURSEMENT';

export interface CoverageCategoryItem {
  category: string;
  status: string;
  details: string;
}

export interface PolicyExclusionItem {
  category: string;
  clause_reference?: string;
  description: string;
}

export interface ReimbursementLimit {
  scope: string;
  amount: string;
  notes?: string;
}

export interface PharmacyRule {
  rule: string;
  prescription_required: boolean;
  approved_network_only: boolean;
  details: string;
}

export interface OutpatientInpatientRule {
  setting: string;
  minimum_hospitalization_hours?: string;
  eligibility_summary: string;
}

export interface RequiredDocument {
  document_name: string;
  mandatory: boolean;
  purpose: string;
}

export interface ClaimSubmissionDeadline {
  timeframe: string;
  penalty_or_forfeiture?: string;
}

export interface ExtractedPolicyRules {
  policy_id: string;
  policy_name: string;
  policy_category: PolicyUploadCategory;
  coverage_categories: CoverageCategoryItem[];
  exclusions: PolicyExclusionItem[];
  reimbursement_limits: ReimbursementLimit[];
  pharmacy_medicine_rules: PharmacyRule[];
  outpatient_inpatient_rules: OutpatientInpatientRule[];
  required_documents: RequiredDocument[];
  claim_submission_deadlines: ClaimSubmissionDeadline[];
  summary: string;
  extracted_at: string;
}

export interface EvidenceItem {
  policy_name: string;
  page_number: number;
  clause_title?: string;
  quote: string;
}

export interface PolicyListItem {
  id: string;
  file_name: string;
  file_size: number;
  document_type: string;
  created_at: string;
}

export interface CoverageComparisonResponse {
  coverage_assessment: string;
  reason: string;
  evidence: EvidenceItem[];
  conditions: string[];
  confidence: string;
  applicable_limit?: string;
  required_documents: string[];
  deadline?: string;
  disclaimer: string;
}

export interface PolicyAnswerResponse {
  answer: string;
  evidence: EvidenceItem[];
  confidence: string;
  disclaimer: string;
}
