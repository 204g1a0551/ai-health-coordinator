export interface LabTestResult {
  test_name: string;
  result: string;
  unit: string;
  reference_range: string;
  status: string;
  is_out_of_range: boolean;
  source_page: number;
  panel_name?: string;
}

export interface LabReportData {
  document_id: string;
  file_name: string;
  laboratory_name: string;
  report_date: string;
  patient_name?: string;
  page_count: number;
  tests: LabTestResult[];
  total_tests: number;
  out_of_range_count: number;
  summary: string;
  disclaimer: string;
}

export interface LabQuestionRequest {
  document_id?: string;
  question: string;
}

export interface LabQuestionResponse {
  question: string;
  answer: string;
  document_id?: string;
  document_name?: string;
  source_page?: number;
  referenced_tests: LabTestResult[];
  disclaimer: string;
}

export interface LabEvidenceResponse {
  document_name: string;
  page_number: number;
  extracted_text: string;
  explanation: string;
  query: string;
  relevant_tests: LabTestResult[];
  disclaimer: string;
}
