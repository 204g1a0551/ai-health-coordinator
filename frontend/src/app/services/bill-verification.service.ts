import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { BillVerificationData, VerificationQuestionResponse, VerificationEvidenceData } from '../models/bill-verification.model';

@Injectable({ providedIn: 'root' })
export class BillVerificationService {
  private readonly apiBase = 'http://localhost:8000/api/bill-verification';

  constructor(private http: HttpClient) {}

  verifyDocuments(prescriptionDocId: string, billDocId: string, sessionId?: string): Observable<{success: boolean; data: BillVerificationData}> {
    const form = new FormData();
    form.append('prescription_doc_id', prescriptionDocId);
    form.append('bill_doc_id', billDocId);
    if (sessionId) form.append('session_id', sessionId);
    return this.http.post<{success: boolean; data: BillVerificationData}>(`${this.apiBase}/verify`, form);
  }

  getLatestVerification(sessionId?: string): Observable<{success: boolean; data: BillVerificationData}> {
    const params = sessionId ? `?session_id=${sessionId}` : '';
    return this.http.get<{success: boolean; data: BillVerificationData}>(`${this.apiBase}/latest${params}`);
  }

  queryVerification(question: string, sessionId?: string): Observable<{success: boolean; data: VerificationQuestionResponse}> {
    return this.http.post<{success: boolean; data: VerificationQuestionResponse}>(`${this.apiBase}/query`, { question, session_id: sessionId });
  }

  getEvidence(sessionId?: string): Observable<{success: boolean; data: VerificationEvidenceData}> {
    const params = sessionId ? `?session_id=${sessionId}` : '';
    return this.http.get<{success: boolean; data: VerificationEvidenceData}>(`${this.apiBase}/evidence${params}`);
  }
}
