import { Component, ElementRef, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css',
})
export class ChatComponent {
  protected readonly chatService = inject(ChatService);
  protected readonly messages = this.chatService.messages;
  protected readonly isSending = this.chatService.isSending;
  protected readonly sessionId = this.chatService.sessionId;

  @ViewChild('messagesScroll') private messagesScroll?: ElementRef<HTMLDivElement>;

  userInput = '';

  sendMessage(): void {
    const text = this.userInput.trim();
    if (!text || this.isSending()) return;

    this.userInput = '';
    this.scrollToBottom();

    this.chatService.sendMessage(text).subscribe({
      next: () => {
        this.scrollToBottom();
      },
      error: () => {
        this.scrollToBottom();
      },
    });
  }

  sendPreset(prompt: string): void {
    if (this.isSending()) return;
    this.chatService.sendMessage(prompt).subscribe({
      next: () => this.scrollToBottom(),
      error: () => this.scrollToBottom(),
    });
  }

  searchNearMe(): void {
    if (this.isSending()) return;
    this.chatService.requestLocation()
      .then((coords) => {
        this.chatService.sendMessage('Doctors near me', coords).subscribe({
          next: () => this.scrollToBottom(),
          error: () => this.scrollToBottom(),
        });
      })
      .catch(() => {
        // Fallback to sending prompt without coords, prompting user politely
        this.chatService.sendMessage('Doctors near me').subscribe({
          next: () => this.scrollToBottom(),
          error: () => this.scrollToBottom(),
        });
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
