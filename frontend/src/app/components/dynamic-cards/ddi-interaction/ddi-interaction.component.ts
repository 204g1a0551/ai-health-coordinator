import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DDIAnalysisResult, DrugInteractionPair, InteractionSeverity } from '../../../models/drug-interaction.model';

@Component({
  selector: 'app-ddi-interaction',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ddi-interaction.component.html',
  styleUrls: ['./ddi-interaction.component.css'],
})
export class DDIInteractionComponent {
  @Input() data: any = {};
  @Output() actionClicked = new EventEmitter<string>();

  get analysis(): DDIAnalysisResult | null {
    return this.data?.analysis || this.data || null;
  }

  get interactions(): DrugInteractionPair[] {
    return this.analysis?.interactions || [];
  }

  get unverifiedPairs(): DrugInteractionPair[] {
    return this.analysis?.unverified_pairs || [];
  }

  getSeverityBadgeClass(severity: InteractionSeverity | string): string {
    switch (severity) {
      case 'HIGH':
      case 'MAJOR':
        return 'badge-high';
      case 'MODERATE':
        return 'badge-mod';
      case 'MINOR':
        return 'badge-minor';
      default:
        return 'badge-unverified';
    }
  }

  askAbout(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
