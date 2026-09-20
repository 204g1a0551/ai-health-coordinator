import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-insurance-policy',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './insurance-policy.component.html',
  styleUrl: './insurance-policy.component.css',
})
export class InsurancePolicyComponent {
  @Input() data: any;
  @Output() actionClicked = new EventEmitter<string>();

  get policyName(): string {
    return this.data?.policy_name || 'Corporate Health & Reimbursement Policy';
  }

  get category(): string {
    return this.data?.category || 'Company Health Insurance';
  }

  get source(): string {
    return this.data?.source || 'Company Policy — Page 1';
  }

  get summary(): string {
    return (
      this.data?.summary ||
      'Covers eligible inpatient hospitalizations, day care procedures, and outpatient pharmacy expenses up to annual limits.'
    );
  }

  get limits(): string {
    return this.data?.rules?.limits?.[0]?.description || 'Outpatient Pharmacy: ₹15,000 per financial year';
  }

  get deadline(): string {
    return this.data?.rules?.deadlines?.[0]?.timeframe || 'Within 30 days of consultation or invoice';
  }

  onSelectAction(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
