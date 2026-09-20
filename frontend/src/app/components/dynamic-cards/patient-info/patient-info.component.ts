import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-patient-info',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './patient-info.component.html',
  styleUrl: './patient-info.component.css',
})
export class PatientInfoComponent {
  @Input() data: any = null;

  get name(): string {
    return this.data?.name || this.data?.patient_name || 'Guest Patient';
  }

  get age(): string | number {
    return this.data?.age || '—';
  }

  get gender(): string {
    return this.data?.gender || '—';
  }

  get phone(): string {
    return this.data?.phone || this.data?.contact || '—';
  }

  get email(): string {
    return this.data?.email || '—';
  }

  get bloodGroup(): string {
    return this.data?.blood_group || this.data?.bloodGroup || '—';
  }

  get allergies(): string[] {
    const raw = this.data?.allergies;
    if (Array.isArray(raw)) return raw;
    if (typeof raw === 'string' && raw.trim()) return raw.split(',').map((s: string) => s.trim());
    return [];
  }

  get medicalHistory(): string[] {
    const raw = this.data?.medical_history || this.data?.medicalHistory;
    if (Array.isArray(raw)) return raw;
    if (typeof raw === 'string' && raw.trim()) return raw.split(',').map((s: string) => s.trim());
    return [];
  }

  get initials(): string {
    return this.name
      .split(' ')
      .map((w: string) => w[0] || '')
      .join('')
      .toUpperCase()
      .substring(0, 2);
  }
}
