import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';
import {
  LabReportData,
  LabQuestionRequest,
  LabQuestionResponse,
  LabEvidenceResponse,
} from '../models/lab-report.model';

@Injectable({
  providedIn: 'root',
})
export class LabReportsService {
  private http = inject(HttpClient);
  private readonly baseUrl = 'http://127.0.0.1:8000/api/lab-reports';

  readonly activeReport = signal<LabReportData | null>(null);
  readonly qaAnswer = signal<LabQuestionResponse | null>(null);
  readonly pageEvidence = signal<LabEvidenceResponse | null>(null);

  readonly isLoading = signal<boolean>(false);
  readonly isUploading = signal<boolean>(false);
  readonly isQuerying = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  constructor() {
    this.loadLatestReport();
  }

  loadLatestReport(): void {
    this.isLoading.set(true);
    this.error.set(null);
    this.http.get<LabReportData>(`${this.baseUrl}/latest`).subscribe({
      next: (data) => {
        this.activeReport.set(data);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.error.set('Failed to load laboratory report from server.');
        this.isLoading.set(false);
      },
    });
  }

  uploadLabReport(file: File, patientName?: string): Observable<LabReportData> {
    this.isUploading.set(true);
    this.error.set(null);

    const formData = new FormData();
    formData.append('file', file);
    if (patientName) {
      formData.append('patient_name', patientName);
    }

    return this.http.post<LabReportData>(`${this.baseUrl}/upload`, formData).pipe(
      tap({
        next: (report) => {
          this.activeReport.set(report);
          this.isUploading.set(false);
        },
        error: (err) => {
          this.error.set(err?.error?.detail || 'Failed to upload laboratory report.');
          this.isUploading.set(false);
        },
      })
    );
  }

  askQuestion(question: string, documentId?: string): void {
    const docId = documentId || this.activeReport()?.document_id;
    this.isQuerying.set(true);
    this.error.set(null);

    const req: LabQuestionRequest = {
      question,
      document_id: docId,
    };

    this.http.post<LabQuestionResponse>(`${this.baseUrl}/query`, req).subscribe({
      next: (res) => {
        this.qaAnswer.set(res);
        this.isQuerying.set(false);
      },
      error: (err) => {
        this.error.set('Failed to retrieve answer from laboratory report intelligence.');
        this.isQuerying.set(false);
      },
    });
  }

  loadEvidence(pageNumber: number, query: string = ''): void {
    const docId = this.activeReport()?.document_id || 'doc-ad301582d5c5';
    this.http
      .get<LabEvidenceResponse>(`${this.baseUrl}/${docId}/evidence?page=${pageNumber}&query=${encodeURIComponent(query)}`)
      .subscribe({
        next: (evidence) => {
          this.pageEvidence.set(evidence);
        },
        error: () => {
          // Non-critical
        },
      });
  }
}
