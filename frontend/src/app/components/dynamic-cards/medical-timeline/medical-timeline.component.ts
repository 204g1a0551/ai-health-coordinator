import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-medical-timeline-card',
  standalone: true,
  imports: [CommonModule],
  template: `<div class="timeline-card"><h3>📅 Medical Timeline</h3><p>{{ data()?.events?.length || 0 }} recorded events</p></div>`,
  styles: [`.timeline-card { padding: 1rem; border-radius: 12px; background: #eff6ff; }`],
})
export class MedicalTimelineCardComponent {
  readonly data = input<any>(null);
}
