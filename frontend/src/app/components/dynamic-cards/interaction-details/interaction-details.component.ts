import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DrugInteractionPair, DDIAnalysisResult } from '../../../models/drug-interaction.model';

@Component({
  selector: 'app-interaction-details',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './interaction-details.component.html',
  styleUrls: ['./interaction-details.component.css'],
})
export class InteractionDetailsComponent {
  @Input() data: any = {};
  @Output() actionClicked = new EventEmitter<string>();

  get interactions(): DrugInteractionPair[] {
    return this.data?.interactions || this.data?.analysis?.interactions || [];
  }

  get unverifiedPairs(): DrugInteractionPair[] {
    return this.data?.unverified_pairs || this.data?.analysis?.unverified_pairs || [];
  }

  askAbout(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
