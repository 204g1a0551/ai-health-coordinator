import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  DocumentUploadResponse,
  DocumentListItem,
  DocumentQuestionRequest,
  DocumentAnswerResponse,
} from '../models/document.model';

@Injectable({
  providedIn: 'root',
})
export class DocumentService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiUrl}/documents`;

  // Reactive state for document list
  readonly documents = signal<DocumentListItem[]>([]);
  readonly activeDocument = signal<DocumentUploadResponse | null>(null);
  readonly isUploading = signal<boolean>(false);
  readonly uploadError = signal<string | null>(null);

  // Reactive state for Document RAG Q&A
  readonly isAnswering = signal<boolean>(false);
  readonly currentAnswer = signal<DocumentAnswerResponse | null>(null);
  readonly qaError = signal<string | null>(null);

  /**
   * Uploads medical PDF to backend document processing pipeline.
   */
  uploadDocument(file: File, userId?: string): Observable<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    if (userId) {
      formData.append('user_id', userId);
    }

    this.isUploading.set(true);
    this.uploadError.set(null);

    return this.http.post<DocumentUploadResponse>(`${this.apiUrl}/upload`, formData).pipe(
      tap({
        next: (res) => {
          this.isUploading.set(false);
          this.activeDocument.set(res);
          this.refreshDocuments();
        },
        error: (err) => {
          this.isUploading.set(false);
          const msg = err.error?.detail || err.message || 'Failed to upload document.';
          this.uploadError.set(msg);
        },
      })
    );
  }

  /**
   * Fetches list of all stored documents.
   */
  listDocuments(userId?: string): Observable<DocumentListItem[]> {
    const url = userId ? `${this.apiUrl}?user_id=${encodeURIComponent(userId)}` : this.apiUrl;
    return this.http.get<DocumentListItem[]>(url).pipe(
      tap((docs) => this.documents.set(docs))
    );
  }

  refreshDocuments(): void {
    this.listDocuments().subscribe({
      error: () => {},
    });
  }

  /**
   * Fetches full extracted details for a document.
   */
  getDocumentDetails(id: string): Observable<DocumentUploadResponse> {
    return this.http.get<DocumentUploadResponse>(`${this.apiUrl}/${id}`).pipe(
      tap((res) => this.activeDocument.set(res))
    );
  }

  /**
   * Deletes a document by ID.
   */
  deleteDocument(id: string): Observable<{ message: string; id: string }> {
    return this.http.delete<{ message: string; id: string }>(`${this.apiUrl}/${id}`).pipe(
      tap(() => {
        if (this.activeDocument()?.id === id) {
          this.activeDocument.set(null);
        }
        this.refreshDocuments();
      })
    );
  }

  /**
   * Returns direct download URL for original PDF.
   */
  getDownloadUrl(id: string): string {
    return `${this.apiUrl}/${id}/download`;
  }

  /**
   * Submits a question to the Document Intelligence & RAG pipeline.
   */
  askQuestion(question: string, docId?: string): Observable<DocumentAnswerResponse> {
    this.isAnswering.set(true);
    this.qaError.set(null);

    const payload: DocumentQuestionRequest = {
      question: question.trim(),
      doc_id: docId,
    };

    return this.http.post<DocumentAnswerResponse>(`${this.apiUrl}/qa`, payload).pipe(
      tap({
        next: (res) => {
          this.isAnswering.set(false);
          this.currentAnswer.set(res);
        },
        error: (err) => {
          this.isAnswering.set(false);
          const msg = err.error?.detail || err.message || 'Failed to get answer from document.';
          this.qaError.set(msg);
        },
      })
    );
  }

  clearAnswer(): void {
    this.currentAnswer.set(null);
    this.qaError.set(null);
  }
}
