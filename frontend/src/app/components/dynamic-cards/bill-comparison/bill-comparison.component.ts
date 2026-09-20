import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MedicineComparisonItem, BillVerificationData } from '../../../models/bill-verification.model';

@Component({
  selector: 'app-bill-comparison',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './bill-comparison.component.html',
  styleUrls: ['./bill-comparison.component.css']
})
export class BillComparisonComponent {
  @Input() data: any = {};
  @Output() actionClicked = new EventEmitter<string>();

  get verificationData(): BillVerificationData | null {
    return this.data?.verification || this.data || null;
  }

  get comparisonItems(): MedicineComparisonItem[] {
    return this.verificationData?.comparison_items || [];
  }

  getDiscrepancyClass(type: string): string {
    const map: Record<string, string> = {
      'MATCH': 'badge-match',
      'MISSING_FROM_BILL': 'badge-missing',
      'NOT_IN_PRESCRIPTION': 'badge-extra',
      'QUANTITY_MISMATCH': 'badge-qty',
      'DOSAGE_MISMATCH': 'badge-dosage'
    };
    return map[type] || 'badge-unknown';
  }

  getDiscrepancyLabel(type: string): string {
    const map: Record<string, string> = {
      'MATCH': '✓ Match',
      'MISSING_FROM_BILL': '⚠ Missing from Bill',
      'NOT_IN_PRESCRIPTION': '➕ Not Prescribed',
      'QUANTITY_MISMATCH': '⚖ Qty Mismatch',
      'DOSAGE_MISMATCH': '💊 Dosage Diff'
    };
    return map[type] || type;
  }

  askAbout(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
