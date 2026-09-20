export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  text: string;
  timestamp: string;
  isError?: boolean;
}

export interface ChatRequest {
  message: string;
  sessionId: string;
  coordinates?: { lat: number; lng: number };
}

export interface ChatResponse {
  message: string;
  actions: any[];
  action?: string;
  data?: any;
  sessionId?: string;
}
