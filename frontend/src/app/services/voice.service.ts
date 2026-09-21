import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface VoiceProcessResponse {
  success: boolean;
  session_id: string;
  original_transcript: string;
  detected_language: string;
  language_name: string;
  normalized_english_query: string;
  response_text_english: string;
  response_text_vernacular: string;
  audio_base64?: string;
  audio_mime_type?: string;
  triage_status?: string;
  normal_workflow_allowed: boolean;
  actions: any[];
}

@Injectable({
  providedIn: 'root',
})
export class VoiceService {
  private readonly http = inject(HttpClient);
  private readonly voiceApiUrl = `${environment.apiUrl}/voice`;

  readonly isRecording = signal<boolean>(false);
  readonly isSpeaking = signal<boolean>(false);
  readonly selectedLanguage = signal<string>('auto'); // 'auto', 'te', 'hi', 'en'
  readonly supportedLanguages = [
    { code: 'auto', label: '🌐 Auto-Detect', locale: 'en-IN' },
    { code: 'te', label: '🇮🇳 తెలుగు (Telugu)', locale: 'te-IN' },
    { code: 'hi', label: '🇮🇳 हिन्दी (Hindi)', locale: 'hi-IN' },
    { code: 'en', label: '🇬🇧 English', locale: 'en-IN' },
  ];

  private recognition: any = null;
  private currentAudioElement: HTMLAudioElement | null = null;

  constructor() {
    this.initSpeechRecognition();
  }

  private initSpeechRecognition(): void {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.maxAlternatives = 1;
    }
  }

  /**
   * Starts listening to user voice via Web Speech API
   */
  startListening(
    onResult: (transcript: string) => void,
    onError: (err: any) => void
  ): boolean {
    if (!this.recognition) {
      onError('Speech recognition is not supported in this browser.');
      return false;
    }

    const langCode = this.selectedLanguage();
    const langObj = this.supportedLanguages.find((l) => l.code === langCode);
    this.recognition.lang = langObj && langObj.locale ? langObj.locale : 'te-IN';

    this.recognition.onresult = (event: any) => {
      this.isRecording.set(false);
      if (event.results && event.results[0] && event.results[0][0]) {
        const transcript = event.results[0][0].transcript;
        onResult(transcript);
      }
    };

    this.recognition.onerror = (err: any) => {
      this.isRecording.set(false);
      onError(err);
    };

    this.recognition.onend = () => {
      this.isRecording.set(false);
    };

    try {
      this.recognition.start();
      this.isRecording.set(true);
      return true;
    } catch (e) {
      this.isRecording.set(false);
      onError(e);
      return false;
    }
  }

  /**
   * Stops voice recording
   */
  stopListening(): void {
    if (this.recognition && this.isRecording()) {
      this.recognition.stop();
      this.isRecording.set(false);
    }
  }

  /**
   * Processes voice message through FastAPI backend
   */
  processVoice(payload: {
    text?: string;
    audio_base64?: string;
    session_id: string;
    preferred_language?: string;
  }): Observable<VoiceProcessResponse> {
    return this.http.post<VoiceProcessResponse>(`${this.voiceApiUrl}/process`, {
      text: payload.text,
      audio_base64: payload.audio_base64,
      session_id: payload.session_id,
      preferred_language: payload.preferred_language || this.selectedLanguage(),
      synthesize_voice_response: true,
    });
  }

  /**
   * Speaks out response text either via server-synthesized audio or Web Speech synthesis
   */
  speakText(text: string, language: string = 'te', audioBase64?: string): void {
    this.stopSpeaking();

    // If backend provided synthesized audio base64, play it
    if (audioBase64) {
      try {
        const audioBlob = this.base64ToBlob(audioBase64, 'audio/wav');
        const audioUrl = URL.createObjectURL(audioBlob);
        this.currentAudioElement = new Audio(audioUrl);
        this.isSpeaking.set(true);

        this.currentAudioElement.onended = () => {
          this.isSpeaking.set(false);
          URL.revokeObjectURL(audioUrl);
        };
        this.currentAudioElement.onerror = () => {
          this.isSpeaking.set(false);
          this.speakViaBrowser(text, language);
        };

        this.currentAudioElement.play().catch(() => {
          this.speakViaBrowser(text, language);
        });
        return;
      } catch (e) {
        // Fallback to browser synthesis
      }
    }

    this.speakViaBrowser(text, language);
  }

  private speakViaBrowser(text: string, language: string): void {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const langLocaleMap: Record<string, string> = {
      te: 'te-IN',
      hi: 'hi-IN',
      en: 'en-IN',
      kn: 'kn-IN',
      ta: 'ta-IN',
    };
    utterance.lang = langLocaleMap[language] || 'en-IN';
    utterance.rate = 0.95;

    utterance.onstart = () => this.isSpeaking.set(true);
    utterance.onend = () => this.isSpeaking.set(false);
    utterance.onerror = () => this.isSpeaking.set(false);

    window.speechSynthesis.speak(utterance);
  }

  stopSpeaking(): void {
    if (this.currentAudioElement) {
      this.currentAudioElement.pause();
      this.currentAudioElement = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.isSpeaking.set(false);
  }

  private base64ToBlob(base64: string, type: string): Blob {
    const binStr = atob(base64);
    const len = binStr.length;
    const arr = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      arr[i] = binStr.charCodeAt(i);
    }
    return new Blob([arr], { type });
  }
}
