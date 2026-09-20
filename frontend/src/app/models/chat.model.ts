export interface ChatMessage {
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string | Date;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  reply: string;
  timestamp?: string;
}
