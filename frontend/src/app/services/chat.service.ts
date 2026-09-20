import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, tap, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { ChatMessage, ChatRequest, ChatResponse } from '../models/chat.model';

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private readonly http = inject(HttpClient);
  private readonly chatApiUrl = `${environment.apiUrl}/chat`;

  // Persistent conversation/session ID for current session
  readonly sessionId = this.getOrCreateSessionId();

  // Reactive message history for current session
  readonly messages = signal<ChatMessage[]>([
    {
      id: 'init-msg-1',
      sender: 'assistant',
      text: 'Hello! I am your AI Health Checkup & Appointment Coordinator. How can I help you today?',
      timestamp: this.getCurrentTimeString(),
    },
  ]);

  readonly isSending = signal<boolean>(false);
  readonly errorMessage = signal<string | null>(null);

  /**
   * Sends user message to FastAPI backend and appends assistant response to history
   */
  sendMessage(userText: string): Observable<ChatResponse> {
    const trimmed = userText.trim();
    if (!trimmed) {
      return throwError(() => new Error('Message cannot be empty'));
    }

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      sender: 'user',
      text: trimmed,
      timestamp: this.getCurrentTimeString(),
    };

    // Append user message immediately
    this.messages.update((msgs) => [...msgs, userMessage]);
    this.isSending.set(true);
    this.errorMessage.set(null);

    const payload: ChatRequest = {
      message: trimmed,
      sessionId: this.sessionId,
    };

    return this.http.post<ChatResponse>(this.chatApiUrl, payload).pipe(
      tap((res) => {
        const assistantMessage: ChatMessage = {
          id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
          sender: 'assistant',
          text: res.message || 'I understand. I can help organize your symptoms and appointment request.',
          timestamp: this.getCurrentTimeString(),
        };

        this.messages.update((msgs) => [...msgs, assistantMessage]);
        this.isSending.set(false);
      }),
      catchError((error: HttpErrorResponse) => {
        this.isSending.set(false);
        const errorText = error.status === 0
          ? 'Unable to connect to the healthcare backend. Please ensure FastAPI server is running on port 8000.'
          : (error.error?.detail || 'An unexpected error occurred while communicating with the server.');

        this.errorMessage.set(errorText);

        const errorNotice: ChatMessage = {
          id: `err-${Date.now()}`,
          sender: 'assistant',
          text: errorText,
          timestamp: this.getCurrentTimeString(),
          isError: true,
        };

        this.messages.update((msgs) => [...msgs, errorNotice]);
        return throwError(() => error);
      })
    );
  }

  private getOrCreateSessionId(): string {
    const storageKey = 'health_coord_session_id';
    try {
      const existing = sessionStorage.getItem(storageKey);
      if (existing) return existing;
      const newId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      sessionStorage.setItem(storageKey, newId);
      return newId;
    } catch {
      return `sess_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    }
  }

  private getCurrentTimeString(): string {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
}
