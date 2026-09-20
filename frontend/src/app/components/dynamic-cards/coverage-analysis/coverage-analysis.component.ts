import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-coverage-analysis',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './coverage-analysis.component.html',
  styleUrl: './coverage-analysis.component.css',
})
export class CoverageAnalysisComponent {
  @Input() data: any;
  @Output() actionClicked = new EventEmitter<string>();

  get coverage(): string {
    return this.data?.coverage_assessment || 'Potentially eligible';
  }

  get reason(): string {
    return (
      this.data?.reason ||
      'The uploaded corporate reimbursement policy states that eligible outpatient pharmacy expenses may be reimbursed up to ₹15,000 per financial year for prescribed medications.'
    );
  }

  get conditions(): string[] {
    return (
      this.data?.conditions || [
        'Valid doctor’s prescription linked to the invoice',
        'Original itemized tax invoice with GSTIN and pharmacy drug license',
        'Claim submitted within 30 days of purchase',
      ]
    );
  }

  get source(): string {
    return this.data?.source || 'Company Policy — Page 1';
  }

  get disclaimer(): string {
    return (
      this.data?.disclaimer ||
      'Preliminary assessment based on uploaded documents. Final claim approval belongs exclusively to your insurer or employer policy administrator.'
    );
  }

  isEligible(): boolean {
    const c = this.coverage.toLowerCase();
    return c.includes('potenti') || c.includes('eligib') || c.includes('cover');
  }

  onSelectAction(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
