import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-document-summary',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './document-summary.component.html',
  styleUrl: './document-summary.component.css',
})
export class DocumentSummaryComponent {
  @Input() data: any;
  @Output() actionClicked = new EventEmitter<string>();

  get fileName(): string {
    return this.data?.file_name || 'prescription.pdf';
  }

  get docType(): string {
    return (this.data?.document_type || 'PRESCRIPTION').replace('_', ' ');
  }

  get doctor(): string {
    return this.data?.doctor_hospital?.doctor_name || 'Dr. Ravi Kumar';
  }

  get hospital(): string {
    return this.data?.doctor_hospital?.hospital_name || 'Manipal Hospital';
  }

  get consultationDate(): string {
    return this.data?.dates?.consultation_date || '2026-09-18';
  }

  get summary(): string {
    return (
      this.data?.summary ||
      'Prescription issued for acute respiratory symptoms. Contains prescribed medications and dosage directions.'
    );
  }

  get medicinesCount(): number {
    return this.data?.medicines_count ?? 2;
  }

  get sourcePage(): number {
    return this.data?.source_page || 1;
  }

  onSelectAction(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
