import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-document-evidence',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './document-evidence.component.html',
  styleUrl: './document-evidence.component.css',
})
export class DocumentEvidenceComponent {
  @Input() data: any;
  @Output() actionClicked = new EventEmitter<string>();

  get documentName(): string {
    return this.data?.source_document || 'Company Health Insurance & Reimbursement Policy';
  }

  get pageNumber(): number {
    return this.data?.page_number || 1;
  }

  get extractedText(): string {
    return (
      this.data?.extracted_text ||
      'Section 4.1 Pharmacy Benefits: Eligible outpatient prescribed medications will be reimbursed up to the annual limit of ₹15,000 per employee family, provided original bills with GST numbers and valid prescriptions are submitted within 30 days of purchase.'
    );
  }

  get explanation(): string {
    return (
      this.data?.explanation ||
      'The policy reimburses prescription pharmacy expenses up to ₹15,000 annually when accompanied by an original GST invoice and physician prescription submitted within 30 days.'
    );
  }

  get userQuery(): string {
    return this.data?.query || 'What does page 7 say about pharmacy reimbursement?';
  }

  onSelectAction(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
