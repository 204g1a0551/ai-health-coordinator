import { Component, input } from '@angular/core';

@Component({
  selector: 'app-document-history-card',
  standalone: true,
  template: `<div class="history-card"><h3>📚 Document History</h3><p>{{ data()?.documents?.length || 0 }} uploaded documents</p></div>`,
  styles: [`.history-card { padding: 1rem; border-radius: 12px; background: #f0fdf4; }`],
})
export class DocumentHistoryCardComponent {
  readonly data = input<any>(null);
}
