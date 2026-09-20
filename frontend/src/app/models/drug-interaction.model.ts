export type InteractionSeverity =
  | 'HIGH'
  | 'MAJOR'
  | 'MODERATE'
  | 'MINOR'
  | 'UNVERIFIED';

export interface NormalizedMedication {
  raw_name: string;
  normalized_name: string;
  brand_name: string | null;
  rxnorm_id: string | null;
  dosage: string | null;
  frequency: string | null;
  source_document_id: string | null;
  source_document_name: string | null;
  source_department: string | null;
}

export interface DrugInteractionPair {
  medicine_a: NormalizedMedication;
  medicine_b: NormalizedMedication;
  severity: InteractionSeverity;
  description: string;
  clinical_effect: string;
  source: string;
  warning: string;
  recommendation: string;
  is_verified: boolean;
}

export interface DuplicateMedication {
  normalized_name: string;
  occurrence_count: number;
  prescriptions: Array<{
    document_id: string;
    file_name: string;
    department: string;
    raw_name: string;
  }>;
}

export interface DDIAnalysisResult {
  session_id: string;
  total_medications: number;
  medications: NormalizedMedication[];
  duplicate_medications: DuplicateMedication[];
  interactions_found: number;
  interactions: DrugInteractionPair[];
  unverified_pairs: DrugInteractionPair[];
  sources_checked: string[];
  analyzed_documents: Array<{ id: string; file_name: string; document_type: string }>;
  analyzed_at: string;
  disclaimer: string;
}

export interface DDIQuestionResponse {
  question: string;
  answer: string;
  interactions: DrugInteractionPair[];
  medications: NormalizedMedication[];
  disclaimer: string;
}
