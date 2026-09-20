import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

import { InsuranceService } from '../../services/insurance.service';
import { DocumentService } from '../../services/document.service';
import {
  PolicyUploadCategory,
  PolicyListItem,
  ExtractedPolicyRules,
  CoverageComparisonResponse,
  PolicyAnswerResponse,
} from '../../models/insurance.model';
import { DocumentListItem } from '../../models/document.model';

@Component({
  selector: 'app-insurance-reimbursement',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './insurance-reimbursement.component.html',
  styleUrl: './insurance-reimbursement.component.css',
})
export class InsuranceReimbursementComponent implements OnInit {
  protected readonly insuranceService = inject(InsuranceService);
  protected readonly documentService = inject(DocumentService);

  readonly isDragOver = signal<boolean>(false);
  readonly selectedCategory = signal<PolicyUploadCategory>('COMPANY_HEALTH_INSURANCE');
  readonly selectedMedicalDocId = signal<string>('');
  readonly selectedPolicyId = signal<string>('');
  readonly userQueryInput = signal<string>('');
  readonly qaQuestionInput = signal<string>('');
  readonly uploadError = signal<string | null>(null);

  readonly supportedCategories = [
    {
      id: 'COMPANY_HEALTH_INSURANCE' as PolicyUploadCategory,
      title: 'Company Health Insurance',
      icon: '🏢',
      desc: 'Group Mediclaim, hospitalization, sum insured clauses',
    },
    {
      id: 'EMPLOYEE_REIMBURSEMENT' as PolicyUploadCategory,
      title: 'Employee Medical Reimbursement',
      icon: '💼',
      desc: 'Annual corporate OPD allowances, clinical expenses',
    },
    {
      id: 'INSURANCE_TERMS_CONDITIONS' as PolicyUploadCategory,
      title: 'Insurance Terms & Conditions',
      icon: '📋',
      desc: 'Exclusion lists, waiting periods, sub-limits & co-pay',
    },
    {
      id: 'PHARMACY_REIMBURSEMENT' as PolicyUploadCategory,
      title: 'Pharmacy Reimbursement Policy',
      icon: '💊',
      desc: 'Prescription medicines, itemized invoices, pharmacy caps',
    },
  ];

  readonly suggestedQuestions = [
    'Will this medicine bill be covered according to my company policy?',
    'What does my insurance policy say about outpatient medicines?',
    'Does my company policy mention pharmacy reimbursement?',
    'What is the claim submission deadline?',
    'What documents are required to submit an OPD claim?',
  ];

  ngOnInit(): void {
    this.insuranceService.loadPolicies();
    this.documentService.refreshDocuments();
  }

  onCategorySelect(cat: PolicyUploadCategory): void {
    this.selectedCategory.set(cat);
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
      this.handlePolicyFile(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handlePolicyFile(input.files[0]);
    }
  }

  private handlePolicyFile(file: File): void {
    this.uploadError.set(null);
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      this.uploadError.set('Only PDF policy documents (.pdf) are supported.');
      return;
    }

    this.insuranceService.uploadPolicy(file, this.selectedCategory()).subscribe({
      next: (res) => {
        if (res?.id) {
          this.selectedPolicyId.set(res.id);
        }
      },
    });
  }

  onSelectPolicy(policy: PolicyListItem): void {
    this.selectedPolicyId.set(policy.id);
    this.insuranceService.selectPolicy(policy);
  }

  onRunComparison(): void {
    const policyId = this.selectedPolicyId() || this.insuranceService.activePolicy()?.id;
    if (!policyId) {
      this.uploadError.set('Please select or upload an insurance/reimbursement policy first.');
      return;
    }

    const medDocId = this.selectedMedicalDocId();
    const query = this.userQueryInput().trim() || 'Will this medicine bill be covered according to my company policy?';

    this.insuranceService.compareCoverage(policyId, medDocId || undefined, query);
  }

  onAskQuestion(question?: string): void {
    const q = (question || this.qaQuestionInput()).trim();
    if (!q) return;

    this.qaQuestionInput.set(q);
    const policyId = this.selectedPolicyId() || this.insuranceService.activePolicy()?.id;
    this.insuranceService.queryPolicy(q, policyId);
  }
}
