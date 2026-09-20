import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-medicine-information',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './medicine-information.component.html',
  styleUrl: './medicine-information.component.css',
})
export class MedicineInformationComponent {
  @Input() data: any;
  @Output() findPharmacies = new EventEmitter<string>();

  get medicineName(): string {
    return this.data?.medicine_name || 'Augmentin 625mg';
  }

  get genericName(): string {
    return this.data?.generic_name || 'Amoxicillin + Clavulanic Acid';
  }

  get category(): string {
    return this.data?.category || 'Broad-spectrum Antibiotic';
  }

  get indication(): string {
    return (
      this.data?.indication ||
      'Prescribed for bacterial respiratory tract, ENT, and soft tissue infections.'
    );
  }

  get dosageForm(): string {
    return this.data?.dosage_form || 'Oral Film-coated Tablet';
  }

  get administrationAdvice(): string {
    return (
      this.data?.administration_advice ||
      'Take at the start of a meal to minimize GI discomfort. Complete the full course.'
    );
  }

  get sideEffects(): string[] {
    return this.data?.common_side_effects || ['Mild nausea', 'Diarrhea', 'Headache'];
  }

  get sourceReference(): string {
    return this.data?.source_reference || 'National Pharmacology Grid & Verified Formulary';
  }

  onFindPharmacies(): void {
    this.findPharmacies.emit('Where can I buy these medicines?');
  }
}
