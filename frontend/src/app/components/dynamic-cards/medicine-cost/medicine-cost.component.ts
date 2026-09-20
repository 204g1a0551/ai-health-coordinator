import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MedicineComparison, CostSaverAnalysisResult } from '../../../models/cost-saver.model';

@Component({
  selector: 'app-medicine-cost',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './medicine-cost.component.html',
  styleUrls: ['./medicine-cost.component.css'],
})
export class MedicineCostComponent {
  @Input() data: any = {};
  @Output() actionClicked = new EventEmitter<string>();

  get analysis(): CostSaverAnalysisResult | null {
    return this.data?.analysis || this.data || null;
  }

  get comparisons(): MedicineComparison[] {
    return this.analysis?.comparisons || this.data?.comparisons || [];
  }

  askAbout(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
