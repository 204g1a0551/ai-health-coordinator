import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { DDIAnalysisResult, DDIQuestionResponse, DrugInteractionPair } from '../models/drug-interaction.model';

@Injectable({ providedIn: 'root' })
export class DrugInteractionService {
  private readonly apiBase = 'http://localhost:8000/api/ddi';

  constructor(private http: HttpClient) {}

  getLatestAnalysis(sessionId?: string): Observable<DDIAnalysisResult> {
    const params = sessionId ? `?session_id=${sessionId}` : '';
    return this.http.get<DDIAnalysisResult>(`${this.apiBase}/latest${params}`);
  }

  analyzeDocuments(documentIds?: string[], sessionId?: string): Observable<DDIAnalysisResult> {
    return this.http.post<DDIAnalysisResult>(`${this.apiBase}/analyze`, {
      document_ids: documentIds,
      session_id: sessionId || 'default',
    });
  }

  checkPair(medicineA: string, medicineB: string): Observable<DrugInteractionPair> {
    return this.http.post<DrugInteractionPair>(`${this.apiBase}/check-pair`, {
      medicine_a: medicineA,
      medicine_b: medicineB,
    });
  }

  queryInteractions(question: string, sessionId?: string): Observable<DDIQuestionResponse> {
    return this.http.post<DDIQuestionResponse>(`${this.apiBase}/query`, {
      question,
      session_id: sessionId || 'default',
    });
  }
}
