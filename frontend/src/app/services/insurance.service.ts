import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of } from 'rxjs';
import {
  PolicyListItem,
  ExtractedPolicyRules,
  CoverageComparisonResponse,
  PolicyAnswerResponse,
  PolicyUploadCategory,
} from '../models/insurance.model';

@Injectable({
  providedIn: 'root',
})
export class InsuranceService {
  private http = inject(HttpClient);
  private readonly baseUrl = 'http://127.0.0.1:8000/api/insurance';

  readonly policies = signal<PolicyListItem[]>([]);
  readonly activePolicy = signal<PolicyListItem | null>(null);
  readonly activePolicyRules = signal<ExtractedPolicyRules | null>(null);
  readonly coverageComparison = signal<CoverageComparisonResponse | null>(null);
  readonly policyAnswer = signal<PolicyAnswerResponse | null>(null);

  readonly isLoading = signal<boolean>(false);
  readonly isUploading = signal<boolean>(false);
  readonly isAnalyzing = signal<boolean>(false);
  readonly isQuerying = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  constructor() {
    this.loadPolicies();
  }

  loadPolicies(): void {
    this.isLoading.set(true);
    this.error.set(null);
    this.http.get<PolicyListItem[]>(`${this.baseUrl}/policies`).subscribe({
      next: (list) => {
        this.policies.set(list);
        this.isLoading.set(false);
        if (list.length > 0 && !this.activePolicy()) {
          this.selectPolicy(list[0]);
        }
      },
      error: (err) => {
        this.error.set('Failed to load insurance policies from server.');
        this.isLoading.set(false);
      },
    });
  }

  selectPolicy(policy: PolicyListItem): void {
    this.activePolicy.set(policy);
    this.loadPolicyRules(policy.id);
  }

  loadPolicyRules(policyId: string): void {
    this.isLoading.set(true);
    this.http.get<ExtractedPolicyRules>(`${this.baseUrl}/policies/${policyId}/rules`).subscribe({
      next: (rules) => {
        this.activePolicyRules.set(rules);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      },
    });
  }

  uploadPolicy(file: File, category: PolicyUploadCategory): Observable<any> {
    this.isUploading.set(true);
    this.error.set(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);

    return this.http.post<any>(`${this.baseUrl}/upload`, formData).pipe(
      tap((res) => {
        this.isUploading.set(false);
        this.loadPolicies();
      }),
      catchError((err) => {
        this.isUploading.set(false);
        this.error.set(err.error?.detail || 'Failed to upload and index policy document.');
        return of(null);
      })
    );
  }

  compareCoverage(policyId: string, medicalDocId?: string, userQuery?: string): Observable<CoverageComparisonResponse | null> {
    this.isAnalyzing.set(true);
    this.error.set(null);

    const payload = {
      policy_id: policyId,
      medical_document_id: medicalDocId || null,
      user_query: userQuery || null,
    };

    return this.http.post<CoverageComparisonResponse>(`${this.baseUrl}/compare`, payload).pipe(
      tap((res) => {
        this.coverageComparison.set(res);
        this.isAnalyzing.set(false);
      }),
      catchError((err) => {
        this.isAnalyzing.set(false);
        this.error.set(err.error?.detail || 'Coverage comparison could not be completed.');
        return of(null);
      })
    );
  }

  queryPolicy(question: string, policyId?: string): Observable<PolicyAnswerResponse | null> {
    this.isQuerying.set(true);
    this.error.set(null);

    const payload = {
      policy_id: policyId || this.activePolicy()?.id || null,
      question,
    };

    return this.http.post<PolicyAnswerResponse>(`${this.baseUrl}/query`, payload).pipe(
      tap((res) => {
        this.policyAnswer.set(res);
        this.isQuerying.set(false);
      }),
      catchError((err) => {
        this.isQuerying.set(false);
        this.error.set(err.error?.detail || 'Failed to query policy document.');
        return of(null);
      })
    );
  }
}
