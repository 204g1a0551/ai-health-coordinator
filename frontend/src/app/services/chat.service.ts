import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, of } from 'rxjs';
import { ChatRequest, ChatResponse } from '../models/chat.model';

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/chat';

  sendMessage(message: string): Observable<ChatResponse> {
    const payload: ChatRequest = { message };
    return this.http.post<ChatResponse>(this.apiUrl, payload).pipe(
      catchError((error) => {
        console.error('Failed to communicate with FastAPI backend:', error);
        return of({
          reply: 'Unable to reach the healthcare assistant backend. Please ensure FastAPI server is running.',
        });
      })
    );
  }
}
