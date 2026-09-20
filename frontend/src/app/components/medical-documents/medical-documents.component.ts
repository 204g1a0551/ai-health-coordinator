import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { DocumentService } from '../../services/document.service';
import { PharmacyService } from '../../services/pharmacy.service';
import {
  DocumentUploadResponse,
  DocumentListItem,
  DocumentType,
} from '../../models/document.model';
import {
  MedicineInfo,
  PharmacyStore,
  MedicineSearchResponse,
} from '../../models/pharmacy.model';

@Component({
  selector: 'app-medical-documents',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './medical-documents.component.html',
  styleUrl: './medical-documents.component.css',
})
export class MedicalDocumentsComponent implements OnInit {
  protected readonly docService = inject(DocumentService);
  protected readonly pharmacyService = inject(PharmacyService);

  readonly isDragOver = signal<boolean>(false);
  readonly selectedFile = signal<File | null>(null);
  readonly validationError = signal<string | null>(null);
  readonly showRawText = signal<boolean>(false);
  readonly questionInput = signal<string>('');

  // Pharmacy & Medicine Search state
  readonly selectedPharmacyLocality = signal<string>('Koramangala');
  readonly customLocalityInput = signal<string>('');
  readonly isLocating = signal<boolean>(false);
  readonly locationNotice = signal<string | null>(null);

  // Prompt questions as specified in requirements
  readonly suggestedQuestions = [
    'What medicines are mentioned in this prescription?',
    'What is the prescribed dosage?',
    'What is the consultation date?',
    'What does my insurance policy say about outpatient medicines?',
    'Does my company policy mention pharmacy reimbursement?',
  ];

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

  onAskQuestion(customQuestion?: string): void {
    const q = (customQuestion || this.questionInput()).trim();
    if (!q) return;

    this.questionInput.set(q);
    const activeDocId = this.docService.activeDocument()?.id;
    this.docService.askQuestion(q, activeDocId).subscribe();
  }

  onSelectPrompt(prompt: string): void {
    this.questionInput.set(prompt);
    this.onAskQuestion(prompt);
  }

  onClearAnswer(): void {
    this.docService.clearAnswer();
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

  onSearchPharmacies(customLoc?: string): void {
    const activeDocId = this.docService.activeDocument()?.id;
    const locality = customLoc || this.customLocalityInput().trim() || this.selectedPharmacyLocality();
    this.selectedPharmacyLocality.set(locality);
    this.locationNotice.set(null);
    this.pharmacyService.searchForDocument(activeDocId, locality).subscribe();
  }

  onSelectPharmacyLocality(loc: string): void {
    this.selectedPharmacyLocality.set(loc);
    this.customLocalityInput.set('');
    this.onSearchPharmacies(loc);
  }

  async onUseCurrentLocation(): Promise<void> {
    this.isLocating.set(true);
    this.locationNotice.set('Detecting current GPS coordinates...');
    try {
      const coords = await this.pharmacyService.requestGeolocation();
      this.isLocating.set(false);
      this.locationNotice.set(`GPS locked (${coords.lat.toFixed(3)}, ${coords.lng.toFixed(3)}). Distance calculated.`);
      const activeDocId = this.docService.activeDocument()?.id;
      this.pharmacyService.searchForDocument(activeDocId, 'Current Location', coords.lat, coords.lng).subscribe();
    } catch (err: any) {
      this.isLocating.set(false);
      this.locationNotice.set(`Location access: ${err.message || 'Denied'}. Defaulting to ${this.selectedPharmacyLocality()}.`);
    }
  }

  onClearPharmacyResults(): void {
    this.pharmacyService.clearResults();
  }

  pharmacyDistanceLabel(km: number): string {
    if (km < 1) {
      return `${Math.round(km * 1000)} m away`;
    }
    return `${km.toFixed(1)} km away`;
  }

  pharmacyDistanceClass(km: number): string {
    if (km <= 1.5) return 'dist-close';
    if (km <= 5.0) return 'dist-mid';
    return 'dist-far';
  }

  pharmacyStars(rating: number): string[] {
    const full = Math.round(rating);
    return Array.from({ length: 5 }, (_, i) => (i < full ? '★' : '☆'));
  }
}

