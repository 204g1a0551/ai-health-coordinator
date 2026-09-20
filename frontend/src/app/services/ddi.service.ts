import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { DDIInteractionResponse } from '../models/ddi.model';

@Injectable({ providedIn: 'root' })
export class DDIService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiUrl}/ddi`;

  readonly result = signal<DDIInteractionResponse | null>(null);
  readonly isChecking = signal(false);
  readonly error = signal<string | null>(null);

  check(documentIds?: string[], userId?: string): Observable<DDIInteractionResponse> {
    this.isChecking.set(true);
    this.error.set(null);
    return this.http.post<DDIInteractionResponse>(`${this.apiUrl}/check`, {
      documentIds,
      userId,
    }).pipe(
      tap({
        next: (result) => {
          this.result.set(result);
          this.isChecking.set(false);
        },
        error: (err) => {
          this.error.set(err.error?.detail || 'Interaction information could not be verified from the configured source.');
          this.isChecking.set(false);
        },
      }),
    );
  }
}
