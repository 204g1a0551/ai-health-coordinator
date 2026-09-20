import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { DocumentService } from '../../services/document.service';
import {
  DocumentUploadResponse,
  DocumentListItem,
  DocumentType,
} from '../../models/document.model';

@Component({
  selector: 'app-medical-documents',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './medical-documents.component.html',
  styleUrl: './medical-documents.component.css',
})
export class MedicalDocumentsComponent implements OnInit {
  protected readonly docService = inject(DocumentService);

  readonly isDragOver = signal<boolean>(false);
  readonly selectedFile = signal<File | null>(null);
  readonly validationError = signal<string | null>(null);
  readonly showRawText = signal<boolean>(false);

  // Supported document categories
  readonly supportedCategories = [
    { type: 'Prescription PDF', icon: '💊', desc: 'Medication names, dosage, instructions' },
    { type: 'Doctor Consultation PDF', icon: '🩺', desc: 'Clinical notes, vitals, provider info' },
    { type: 'Medical Report PDF', icon: '🧪', desc: 'Pathology, lab values, diagnosis' },
    { type: 'Medicine Bill PDF', icon: '🧾', desc: 'Pharmacy invoices, item totals, GST' },
    { type: 'Insurance Policy PDF', icon: '🛡️', desc: 'Sum insured, cashless, co-pay clauses' },
    { type: 'Reimbursement Policy PDF', icon: '🏢', desc: 'Corporate claim limits & deadlines' },
  ];

  ngOnInit(): void {
    this.docService.refreshDocuments();
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFileInput(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFileInput(input.files[0]);
    }
  }

  private handleFileInput(file: File): void {
    this.validationError.set(null);

    // 1. Validate file type (must be PDF)
    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      this.validationError.set('Only PDF documents are supported. Please upload a .pdf file.');
      return;
    }

    // 2. Validate file size (max 15MB)
    const maxSize = 15 * 1024 * 1024;
    if (file.size > maxSize) {
      this.validationError.set('File size exceeds the 15MB limit. Please upload a smaller PDF.');
      return;
    }

    if (file.size < 64) {
      this.validationError.set('The selected file appears to be empty or corrupted.');
      return;
    }

    this.selectedFile.set(file);
    this.uploadFile(file);
  }

  uploadFile(file: File): void {
    this.docService.uploadDocument(file).subscribe({
      next: () => {
        this.selectedFile.set(null);
      },
      error: (err) => {
        console.error('Document upload error:', err);
      },
    });
  }

  selectDocument(item: DocumentListItem): void {
    this.docService.getDocumentDetails(item.id).subscribe();
  }

  deleteActiveDocument(id: string): void {
    if (confirm('Are you sure you want to delete this medical document?')) {
      this.docService.deleteDocument(id).subscribe();
    }
  }

  toggleRawText(): void {
    this.showRawText.update((v) => !v);
  }

  formatFileSize(bytes: number): string {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  getDocumentTypeBadgeClass(type: string): string {
    switch (type) {
      case 'PRESCRIPTION':
        return 'badge-prescription';
      case 'DOCTOR_CONSULTATION':
        return 'badge-consultation';
      case 'MEDICAL_REPORT':
        return 'badge-report';
      case 'MEDICINE_BILL':
        return 'badge-bill';
      case 'INSURANCE_POLICY':
        return 'badge-insurance';
      case 'REIMBURSEMENT_POLICY':
        return 'badge-reimbursement';
      default:
        return 'badge-other';
    }
  }

  formatDocumentTypeName(type: string): string {
    if (!type) return 'Document';
    return type
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
  }
}
