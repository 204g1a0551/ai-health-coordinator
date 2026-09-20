import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, tap, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { ChatMessage, ChatRequest, ChatResponse } from '../models/chat.model';
import { UIStateService } from './ui-state.service';

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private readonly http = inject(HttpClient);
  private readonly uiStateService = inject(UIStateService);
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
   * Request browser location permission safely
   */
  requestLocation(): Promise<{ lat: number; lng: number }> {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by your browser'));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          resolve({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
          });
        },
        (err) => reject(err),
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
      );
    });
  }

  /**
   * Sends user message to FastAPI backend and appends assistant response to history
   */
  sendMessage(userText: string, coordinates?: { lat: number; lng: number }): Observable<ChatResponse> {
    const trimmed = userText.trim();
    if (!trimmed) {
      return throwError(() => new Error('Message cannot be empty'));
    }
    if (this.uiStateService.state().emergencyBlocked) {
      return throwError(() => new Error('Normal workflow is blocked during an emergency alert'));
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
      coordinates,
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

        // Dispatch the primary UI action determined by the backend ui_agent
        if (res.action) {
          this.uiStateService.dispatchAction(res.action, res.data ?? null);
        }

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
