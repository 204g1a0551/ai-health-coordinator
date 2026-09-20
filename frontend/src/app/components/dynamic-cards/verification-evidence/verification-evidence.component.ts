import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { VerificationEvidenceData, VerificationEvidenceItem } from '../../../models/bill-verification.model';

@Component({
  selector: 'app-verification-evidence',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './verification-evidence.component.html',
  styleUrls: ['./verification-evidence.component.css']
})
export class VerificationEvidenceComponent {
  @Input() data: any = {};
  @Output() actionClicked = new EventEmitter<string>();

  get evidenceData(): VerificationEvidenceData | null {
    return this.data?.evidence || this.data || null;
  }

  get evidenceItems(): VerificationEvidenceItem[] {
    return this.evidenceData?.evidence_items || [];
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
