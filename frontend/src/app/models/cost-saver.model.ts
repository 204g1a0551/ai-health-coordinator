export type EquivalenceLevel =
  | 'THERAPEUTIC_EQUIVALENT'
  | 'PHARMACEUTICAL_EQUIVALENT'
  | 'PHARMACEUTICAL_ALTERNATIVE'
  | 'UNVERIFIED';

export interface MedicinePriceItem {
  medicine_name: string;
  active_ingredient: string;
  strength: string;
  dosage_form: string;
  pack_size: string;
  listed_price: number;
  price_per_unit: number;
  manufacturer?: string | null;
  is_generic: boolean;
  source: string;
  price_timestamp: string;
}

export interface MedicineComparison {
  prescribed_medicine: MedicinePriceItem;
  generic_equivalent?: MedicinePriceItem | null;
  equivalence_level: EquivalenceLevel;
  equivalence_notes: string;
  price_difference?: number | null;
  savings_percentage?: number | null;
  is_verified: boolean;
  verification_message?: string | null;
}

export interface CostSaverAnalysisResult {
  session_id: string;
  total_prescribed_cost: number;
  potential_generic_cost: number;
  total_potential_savings: number;
  savings_percentage: number;
  comparisons: MedicineComparison[];
  data_source: string;
  price_timestamp: string;
  disclaimer: string;
}

export interface CostSaverQuestionResponse {
  question: string;
  answer: string;
  comparisons: MedicineComparison[];
  total_potential_savings: number;
  disclaimer: string;
}
