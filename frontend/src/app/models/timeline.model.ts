export type TimelineEventType =
  | 'CONSULTATION' | 'PRESCRIPTION' | 'LAB_REPORT'
  | 'PHARMACY_BILL' | 'FOLLOW_UP' | 'INSURANCE';

export interface TimelineEvent {
  event_id: string;
  session_id: string;
  event_type: TimelineEventType;
  date?: string;
  doctor?: string;
  hospital?: string;
  medicines: string[];
  bill_amount?: number;
  consultation_amount?: number;
  diagnostic_amount?: number;
  doc_id: string;
  doc_type: string;
  summary: string;
  created_at: string;
}

export interface MedicalExpense {
  expense_id: string;
  session_id: string;
  category: string;
  amount: number;
  date?: string;
  provider?: string;
  doc_id: string;
}

export interface ExpenseSummary {
  monthly_breakdown: Record<string, Record<string, number>>;
  category_totals: Record<string, number>;
  total: number;
  expenses: MedicalExpense[];
}

export interface TimelineQueryResponse {
  events: TimelineEvent[];
  summary: string;
  evidence: Array<{ doc_id: string; doc_type: string; date?: string }>;
}
