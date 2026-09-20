import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-lab-evidence',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './lab-evidence.component.html',
  styleUrl: './lab-evidence.component.css',
})
export class LabEvidenceComponent {
  @Input() data: any;
  @Output() actionClicked = new EventEmitter<string>();

  get documentName(): string {
    return this.data?.document_name || 'cbc_lab_report.pdf';
  }

  get pageNumber(): number {
    return this.data?.page_number || 3;
  }

  get extractedText(): string {
    return (
      this.data?.extracted_text ||
      'THYROID PANEL & ELECTROLYTES\nTSH (Thyroid Stimulating Hormone): 5.42 uIU/mL (Ref: 0.35 - 4.94 uIU/mL) [HIGH]\nFree Thyroxine (FT4): 1.15 ng/dL (Ref: 0.70 - 1.48 ng/dL) [NORMAL]\nSerum Sodium: 139 mEq/L (Ref: 136 - 145 mEq/L) [NORMAL]\nSerum Potassium: 4.2 mEq/L (Ref: 3.5 - 5.1 mEq/L) [NORMAL]'
    );
  }

  get explanation(): string {
    return (
      this.data?.explanation ||
      'Page 3 of the laboratory report reports the Thyroid Profile and Serum Electrolytes. TSH is observed at 5.42 uIU/mL, which is above the stated reference interval of 0.35 - 4.94 uIU/mL. All electrolytes are within stated intervals.'
    );
  }

  get relevantTests(): any[] {
    return this.data?.relevant_tests || [];
  }

  get disclaimer(): string {
    return (
      this.data?.disclaimer ||
      'Important: Values outside the stated reference ranges are reported strictly as extracted ' +
      'from the laboratory document. This information is for clinical tracking only and does NOT constitute ' +
      'a medical diagnosis or clinical conclusion. Please consult a licensed physician.'
    );
  }

  onSelectAction(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
