import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ExpenseSummary, TimelineEvent, TimelineQueryResponse } from '../models/timeline.model';

@Injectable({ providedIn: 'root' })
export class TimelineService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiUrl}/timeline`;

  getTimeline(sessionId: string): Observable<{ events: TimelineEvent[] }> {
    return this.http.get<{ events: TimelineEvent[] }>(this.apiUrl, { params: { session_id: sessionId } });
  }

  getExpenses(sessionId: string, period?: string): Observable<ExpenseSummary> {
    let params = new HttpParams().set('session_id', sessionId);
    if (period) params = params.set('period', period);
    return this.http.get<ExpenseSummary>(`${this.apiUrl}/expenses`, { params });
  }

  getHistory(sessionId: string): Observable<{ documents: TimelineEvent[] }> {
    return this.http.get<{ documents: TimelineEvent[] }>(`${this.apiUrl}/history`, { params: { session_id: sessionId } });
  }

  ask(sessionId: string, question: string): Observable<TimelineQueryResponse> {
    return this.http.post<TimelineQueryResponse>(`${this.apiUrl}/query`, { session_id: sessionId, question });
  }
}
