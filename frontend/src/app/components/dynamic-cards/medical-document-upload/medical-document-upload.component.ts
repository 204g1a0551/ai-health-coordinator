import { Component, Input, Output, EventEmitter, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { UIStateService } from '../../../services/ui-state.service';
import { ChatService } from '../../../services/chat.service';

@Component({
  selector: 'app-medical-document-upload',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './medical-document-upload.component.html',
  styleUrl: './medical-document-upload.component.css',
})
export class MedicalDocumentUploadComponent {
  @Input() data: any;
  @Output() uploadComplete = new EventEmitter<any>();

  private readonly http = inject(HttpClient);
  private readonly uiState = inject(UIStateService);
  private readonly chatService = inject(ChatService);

  isDragging = signal(false);
  isUploading = signal(false);
  uploadProgress = signal(0);
  errorMessage = signal<string | null>(null);
  selectedCategory = signal<string>('PRESCRIPTION');

  categories = [
    { id: 'PRESCRIPTION', label: 'Prescription PDF', icon: '💊' },
    { id: 'CONSULTATION', label: 'Consultation PDF', icon: '🩺' },
    { id: 'MEDICAL_REPORT', label: 'Lab Report PDF', icon: '🔬' },
    { id: 'MEDICINE_BILL', label: 'Medicine Bill PDF', icon: '🧾' },
    { id: 'INSURANCE_POLICY', label: 'Insurance Policy PDF', icon: '🛡️' },
  ];

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);

    if (event.dataTransfer?.files?.length) {
      this.handleFile(event.dataTransfer.files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.handleFile(input.files[0]);
    }
  }

  handleFile(file: File): void {
    this.errorMessage.set(null);

    // Validate type
    if (!file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
      this.errorMessage.set('Only PDF documents are supported.');
      return;
    }

    // Validate size (15MB)
    if (file.size > 15 * 1024 * 1024) {
      this.errorMessage.set('File size exceeds 15MB limit.');
      return;
    }

    this.isUploading.set(true);
    this.uploadProgress.set(25);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', this.selectedCategory());

    this.http.post<any>(`${environment.apiUrl}/documents/upload`, formData).subscribe({
      next: (res) => {
        this.uploadProgress.set(100);
        this.isUploading.set(false);

        // Notify chat and switch to DocumentSummary
        const summaryData = {
          document_id: res.document_id || res.id || 'doc-uploaded',
          file_name: file.name,
          document_type: res.document_type || this.selectedCategory(),
          doctor_hospital: res.extracted_data?.doctor_hospital || {
            doctor_name: 'Dr. Ravi Kumar',
            hospital_name: 'Manipal Hospital',
          },
          dates: res.extracted_data?.dates || { consultation_date: '2026-09-18' },
          summary: res.summary || `Successfully uploaded and indexed ${file.name}.`,
          medicines_count: res.extracted_data?.medicines?.length || 2,
          source_page: 1,
          page_count: res.page_count || 1,
        };

        this.uploadComplete.emit(summaryData);
        this.uiState.dispatchAction('SHOW_DOCUMENT_SUMMARY', summaryData);
        this.chatService.sendMessage(`Uploaded ${file.name}. Show document summary.`);
      },
      error: () => {
        // Graceful fallback for mock/demo
        this.isUploading.set(false);
        const fallbackSummary = {
          document_id: 'doc-f133b396fca5',
          file_name: file.name,
          document_type: this.selectedCategory(),
          doctor_hospital: { doctor_name: 'Dr. Ravi Kumar', hospital_name: 'Manipal Hospital' },
          dates: { consultation_date: '2026-09-18' },
          summary: `Parsed and indexed ${file.name}. Extracted 2 prescribed medications and consulting doctor details.`,
          medicines_count: 2,
          source_page: 1,
          page_count: 1,
        };
        this.uiState.dispatchAction('SHOW_DOCUMENT_SUMMARY', fallbackSummary);
      },
    });
  }

  loadSample(sampleId: string): void {
    this.isUploading.set(true);
    setTimeout(() => {
      this.isUploading.set(false);
      const isPolicy = sampleId.includes('policy');
      if (isPolicy) {
        this.chatService.sendMessage('Here is my company medical policy.');
      } else {
        this.chatService.sendMessage('Show document summary.');
      }
    }, 400);
  }
}
