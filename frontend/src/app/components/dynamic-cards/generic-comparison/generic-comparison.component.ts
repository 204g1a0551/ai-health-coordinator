import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MedicineComparison, CostSaverAnalysisResult, EquivalenceLevel } from '../../../models/cost-saver.model';

@Component({
  selector: 'app-generic-comparison',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './generic-comparison.component.html',
  styleUrls: ['./generic-comparison.component.css'],
})
export class GenericComparisonComponent {
  @Input() data: any = {};
  @Output() actionClicked = new EventEmitter<string>();

  get analysis(): CostSaverAnalysisResult | null {
    return this.data?.analysis || this.data || null;
  }

  get comparisons(): MedicineComparison[] {
    return this.analysis?.comparisons || this.data?.comparisons || [];
  }

  get verifiedComparisons(): MedicineComparison[] {
    return this.comparisons.filter((c) => c.is_verified && c.generic_equivalent);
  }

  get unverifiedComparisons(): MedicineComparison[] {
    return this.comparisons.filter((c) => !c.is_verified || !c.generic_equivalent);
  }

  askAbout(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
