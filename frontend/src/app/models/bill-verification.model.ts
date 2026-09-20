export type DiscrepancyType =
  | 'MATCH'
  | 'MISSING_FROM_BILL'
  | 'NOT_IN_PRESCRIPTION'
  | 'QUANTITY_MISMATCH'
  | 'DOSAGE_MISMATCH';

export interface MedicineComparisonItem {
  medicine_name: string;
  prescription_quantity: string | null;
  prescription_dosage: string | null;
  prescription_duration: string | null;
  billed_quantity: string | null;
  billed_price: string | null;
  discrepancy_type: DiscrepancyType;
  discrepancy_detail: string | null;
}

export interface BillFinancialSummary {
  subtotal: string | null;
  tax_amount: string | null;
  total_amount: string | null;
  payment_mode: string | null;
  invoice_number: string | null;
  bill_date: string | null;
  pharmacy_name: string | null;
}

export interface BillVerificationData {
  session_id: string;
  prescription_doc_id: string | null;
  bill_doc_id: string | null;
  comparison_items: MedicineComparisonItem[];
  financial_summary: BillFinancialSummary | null;
  prescription_source_page: number;
  bill_source_page: number;
  total_prescribed: number;
  total_billed: number;
  discrepancies_found: number;
  verified_at: string;
}

export interface VerificationQuestionResponse {
  question: string;
  answer: string;
  evidence_items: VerificationEvidenceItem[];
}

export interface VerificationEvidenceItem {
  medicine_name: string;
  discrepancy_type: DiscrepancyType;
  prescription_detail: string | null;
  bill_detail: string | null;
  discrepancy_detail: string | null;
  prescription_page: number;
  bill_page: number;
}

export interface VerificationEvidenceData {
  session_id: string;
  evidence_items: VerificationEvidenceItem[];
  prescription_doc_id: string | null;
  bill_doc_id: string | null;
  extracted_at: string;
}
