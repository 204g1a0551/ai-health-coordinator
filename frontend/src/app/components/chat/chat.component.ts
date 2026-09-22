import { Component, ElementRef, ViewChild, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ChatService } from '../../services/chat.service';
import { VoiceService } from '../../services/voice.service';
import { FollowUpService } from '../../services/follow-up.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css',
})
export class ChatComponent implements OnInit {
  protected readonly chatService = inject(ChatService);
  protected readonly voiceService = inject(VoiceService);
  protected readonly followUpService = inject(FollowUpService);
  private readonly sanitizer = inject(DomSanitizer);

  protected readonly messages = this.chatService.messages;
  protected readonly isSending = this.chatService.isSending;
  protected readonly sessionId = this.chatService.sessionId;

  protected readonly isRecording = this.voiceService.isRecording;
  protected readonly isSpeaking = this.voiceService.isSpeaking;
  protected readonly selectedLanguage = this.voiceService.selectedLanguage;
  protected readonly supportedLanguages = this.voiceService.supportedLanguages;
  protected readonly activeFollowUp = this.followUpService.activeNotification;

  @ViewChild('messagesScroll') private messagesScroll?: ElementRef<HTMLDivElement>;

  userInput = '';

  ngOnInit(): void {
    // Load existing follow-up tasks on init
    this.followUpService.loadTasks().subscribe();
  }

  toggleVoice(): void {
    if (this.isRecording()) {
      this.voiceService.stopListening();
    } else {
      this.voiceService.startListening(
        (transcript) => {
          this.userInput = transcript;
          this.sendMessage();
        },
        (err) => {
          console.warn('Voice recognition error:', err);
        }
      );
    }
  }

  speakMessage(text: string): void {
    this.voiceService.speakText(text, this.selectedLanguage());
  }

  selectLanguage(langCode: string): void {
    this.voiceService.selectedLanguage.set(langCode);
  }

  simulateFollowUp(): void {
    // Check if there are tasks to trigger, or schedule a fresh demo task
    const tasks = this.followUpService.tasks();
    if (tasks.length > 0) {
      this.followUpService.triggerDay2Simulation(tasks[0].task_id).subscribe();
    } else {
      // Create and trigger instant demo task
      this.followUpService.loadTasks().subscribe((tList) => {
        if (tList.length > 0) {
          this.followUpService.triggerDay2Simulation(tList[0].task_id).subscribe();
        }
      });
    }
  }

  respondFollowUp(status: string): void {
    const active = this.activeFollowUp();
    if (!active) return;
    const text = status === 'RECOVERED' ? 'Feeling much better, fever is gone!' : (status === 'SAME' ? 'Symptoms persisting, still having mild fever.' : 'Feeling worse, need doctor assistance.');
    this.followUpService.submitResponse(active.task_id, text, status).subscribe({
      next: () => {
        this.chatService.sendMessage(`[Follow-Up Response]: ${text}`).subscribe();
      }
    });
  }

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

  formatMessage(text: string): SafeHtml {
    if (!text) return '';
    // 1. HTML-escape raw text to prevent XSS
    let formatted = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');

    // 2. Bold: **text** or __text__ -> <strong>text</strong>
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/__(.+?)__/g, '<strong>$1</strong>');

    // 3. Italic: *text* -> <em>text</em>
    formatted = formatted.replace(/(^|[^\*])\*([^\*\n]+?)\*([^\*]|$)/g, '$1<em>$2</em>$3');

    // 4. Remove any remaining stray asterisks like ****, ***, or unclosed **
    formatted = formatted.replace(/\*{2,}/g, '');
    formatted = formatted.replace(/(^|\s)\*(\s|$)/g, '$1•$2');

    // 5. Convert newlines to <br/>
    formatted = formatted.replace(/\n/g, '<br/>');

    return this.sanitizer.bypassSecurityTrustHtml(formatted);
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
