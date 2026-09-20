import { Component, ElementRef, ViewChild, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat.service';
import { ChatMessage } from '../../models/chat.model';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css',
})
export class ChatComponent {
  private readonly chatService = inject(ChatService);

  @ViewChild('messagesScroll') private messagesScroll?: ElementRef<HTMLDivElement>;

  userInput = '';
  isSending = signal(false);

  messages = signal<ChatMessage[]>([
    {
      sender: 'assistant',
      text: 'Hello! I am your AI Health Checkup & Appointment Coordinator. You can describe any symptoms you are experiencing or ask about doctor availability.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  sendMessage(): void {
    const text = this.userInput.trim();
    if (!text || this.isSending()) return;

    const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Add user message
    this.messages.update((msgs) => [
      ...msgs,
      { sender: 'user', text, timestamp: currentTime },
    ]);

    this.userInput = '';
    this.isSending.set(true);
    this.scrollToBottom();

    // Send to FastAPI backend
    this.chatService.sendMessage(text).subscribe({
      next: (res) => {
        const replyTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        this.messages.update((msgs) => [
          ...msgs,
          {
            sender: 'assistant',
            text: res.reply || 'Hello, how can I help you?',
            timestamp: replyTime,
          },
        ]);
        this.isSending.set(false);
        this.scrollToBottom();
      },
      error: () => {
        this.messages.update((msgs) => [
          ...msgs,
          {
            sender: 'assistant',
            text: 'An error occurred while contacting the health coordinator service.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
        this.isSending.set(false);
        this.scrollToBottom();
      },
    });
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      if (this.messagesScroll) {
        this.messagesScroll.nativeElement.scrollTop =
          this.messagesScroll.nativeElement.scrollHeight;
      }
    }, 50);
  }
}
