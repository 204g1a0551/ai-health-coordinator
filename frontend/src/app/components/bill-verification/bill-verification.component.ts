import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { BillVerificationService } from '../../services/bill-verification.service';
import { BillVerificationData, MedicineComparisonItem, VerificationQuestionResponse } from '../../models/bill-verification.model';

@Component({
  selector: 'app-bill-verification',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './bill-verification.component.html',
  styleUrls: ['./bill-verification.component.css']
})
export class BillVerificationComponent implements OnInit {
  // Upload state
  prescriptionDocId = '';
  billDocId = '';
  prescriptionFile: File | null = null;
  billFile: File | null = null;
  prescriptionUploaded = false;
  billUploaded = false;
  uploading = false;
  uploadError = '';
  uploadStep: 'idle' | 'uploading_prescription' | 'uploading_bill' | 'verifying' | 'done' = 'idle';

  // Verification result
  verificationData: BillVerificationData | null = null;
  verifying = false;
  verificationError = '';

  // Q&A
  question = '';
  qaHistory: { q: string; a: string }[] = [];
  qaLoading = false;

  private readonly apiBase = 'http://localhost:8000';

  constructor(
    private bvService: BillVerificationService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.loadLatestVerification();
  }

  loadLatestVerification(): void {
    this.bvService.getLatestVerification().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.verificationData = res.data;
          this.uploadStep = 'done';
        }
      },
      error: () => { /* no data yet */ }
    });
  }

  onPrescriptionDrop(event: DragEvent): void {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0];
    if (file) this.prescriptionFile = file;
  }

  onBillDrop(event: DragEvent): void {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0];
    if (file) this.billFile = file;
  }

  onDragOver(event: DragEvent): void { event.preventDefault(); }

  onPrescriptionFileSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.[0]) this.prescriptionFile = input.files[0];
  }

  onBillFileSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.[0]) this.billFile = input.files[0];
  }

  async uploadPrescription(): Promise<void> {
    if (!this.prescriptionFile) return;
    this.uploadStep = 'uploading_prescription';
    this.uploadError = '';
    const form = new FormData();
    form.append('file', this.prescriptionFile);
    try {
      const res: any = await this.http.post(`${this.apiBase}/api/documents/upload`, form).toPromise();
      this.prescriptionDocId = res?.document_id || res?.data?.document_id || '';
      this.prescriptionUploaded = true;
    } catch (e: any) {
      this.uploadError = 'Failed to upload prescription.';
    } finally {
      if (this.uploadStep === 'uploading_prescription') this.uploadStep = 'idle';
    }
  }

  async uploadBill(): Promise<void> {
    if (!this.billFile) return;
    this.uploadStep = 'uploading_bill';
    this.uploadError = '';
    const form = new FormData();
    form.append('file', this.billFile);
    try {
      const res: any = await this.http.post(`${this.apiBase}/api/documents/upload`, form).toPromise();
      this.billDocId = res?.document_id || res?.data?.document_id || '';
      this.billUploaded = true;
    } catch (e: any) {
      this.uploadError = 'Failed to upload bill.';
    } finally {
      if (this.uploadStep === 'uploading_bill') this.uploadStep = 'idle';
    }
  }

  async verify(): Promise<void> {
    if (!this.prescriptionDocId || !this.billDocId) return;
    this.uploadStep = 'verifying';
    this.verificationError = '';
    this.bvService.verifyDocuments(this.prescriptionDocId, this.billDocId).subscribe({
      next: (res) => {
        if (res.success) {
          this.verificationData = res.data;
          this.uploadStep = 'done';
        } else {
          this.verificationError = 'Verification failed.';
          this.uploadStep = 'idle';
        }
      },
      error: (e) => {
        this.verificationError = e?.error?.detail || 'Verification failed.';
        this.uploadStep = 'idle';
      }
    });
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

  askQuestion(): void {
    if (!this.question.trim()) return;
    const q = this.question.trim();
    this.question = '';
    this.qaLoading = true;
    this.bvService.queryVerification(q).subscribe({
      next: (res) => {
        if (res.success) {
          this.qaHistory.unshift({ q, a: res.data.answer });
        }
        this.qaLoading = false;
      },
      error: () => {
        this.qaHistory.unshift({ q, a: 'Unable to answer that question right now.' });
        this.qaLoading = false;
      }
    });
  }

  reset(): void {
    this.prescriptionFile = null;
    this.billFile = null;
    this.prescriptionDocId = '';
    this.billDocId = '';
    this.prescriptionUploaded = false;
    this.billUploaded = false;
    this.verificationData = null;
    this.uploadStep = 'idle';
    this.uploadError = '';
    this.verificationError = '';
    this.qaHistory = [];
  }
}
