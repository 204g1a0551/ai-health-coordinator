import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CostSaverAnalysisResult, CostSaverQuestionResponse, MedicineComparison } from '../models/cost-saver.model';

@Injectable({ providedIn: 'root' })
export class CostSaverService {
  private readonly apiBase = 'http://localhost:8000/api/cost-saver';

  constructor(private http: HttpClient) {}

  getLatestAnalysis(sessionId?: string): Observable<CostSaverAnalysisResult> {
    const params = sessionId ? `?session_id=${sessionId}` : '';
    return this.http.get<CostSaverAnalysisResult>(`${this.apiBase}/latest${params}`);
  }

  analyzeDocuments(documentIds?: string[], sessionId?: string): Observable<CostSaverAnalysisResult> {
    return this.http.post<CostSaverAnalysisResult>(`${this.apiBase}/analyze`, {
      document_ids: documentIds,
      session_id: sessionId || 'default',
    });
  }

  checkMedicine(medicineName: string): Observable<MedicineComparison> {
    return this.http.post<MedicineComparison>(`${this.apiBase}/check-medicine`, {
      medicine_name: medicineName,
    });
  }

  queryCostSaver(question: string, sessionId?: string): Observable<CostSaverQuestionResponse> {
    return this.http.post<CostSaverQuestionResponse>(`${this.apiBase}/query`, {
      question,
      session_id: sessionId || 'default',
    });
  }
}
