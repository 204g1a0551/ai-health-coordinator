import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../services/chat.service';
import { TimelineService } from '../../services/timeline.service';
import { ExpenseSummary, TimelineEvent } from '../../models/timeline.model';

@Component({
  selector: 'app-medical-timeline',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './medical-timeline.component.html',
  styleUrl: './medical-timeline.component.css',
})
export class MedicalTimelineComponent implements OnInit {
  private readonly timelineService = inject(TimelineService);
  readonly chatService = inject(ChatService);
  readonly events = signal<TimelineEvent[]>([]);
  readonly expenses = signal<ExpenseSummary | null>(null);
  readonly question = signal('');
  readonly answer = signal('');

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.timelineService.getTimeline(this.chatService.sessionId).subscribe((data) => this.events.set(data.events));
    this.timelineService.getExpenses(this.chatService.sessionId).subscribe((data) => this.expenses.set(data));
  }

  ask(): void {
    const question = this.question().trim();
    if (!question) return;
    this.timelineService.ask(this.chatService.sessionId, question).subscribe((data) => this.answer.set(data.summary));
  }

  icon(type: string): string {
    return ({ CONSULTATION: '🏥', PRESCRIPTION: '💊', LAB_REPORT: '🧪', PHARMACY_BILL: '🧾', FOLLOW_UP: '📋', INSURANCE: '🛡️' } as Record<string, string>)[type] || '📄';
  }
}
