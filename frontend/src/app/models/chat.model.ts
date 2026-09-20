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
}

export interface ChatResponse {
  message: string;
  actions: any[];
  sessionId?: string;
}
