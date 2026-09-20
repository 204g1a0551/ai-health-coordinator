import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-appointment',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './appointment.component.html',
  styleUrl: './appointment.component.css',
})
export class AppointmentComponent {
  @Input() data: any = null;

  get appointmentId(): string {
    return this.data?.appointment_id || this.data?.id || 'APT-' + Math.random().toString(36).substring(2, 8).toUpperCase();
  }

  get doctorName(): string {
    return this.data?.doctor || this.data?.doctor_name || 'Dr. Ravi Kumar';
  }

  get department(): string {
    return this.data?.department || 'General Medicine';
  }

  get date(): string {
    return this.data?.date || 'Tomorrow';
  }

  get time(): string {
    return this.data?.time || '6:00 PM';
  }

  get hospital(): string {
    return this.data?.hospital || this.data?.location || 'Apollo Clinic, Koramangala';
  }

  get status(): string {
    return (this.data?.status || 'confirmed').toLowerCase();
  }

  get statusLabel(): string {
    const s = this.status;
    if (s === 'confirmed') return 'Confirmed';
    if (s === 'pending')   return 'Pending';
    if (s === 'cancelled') return 'Cancelled';
    return 'Confirmed';
  }

  get statusClass(): string {
    const s = this.status;
    if (s === 'confirmed') return 'status-confirmed';
    if (s === 'pending')   return 'status-pending';
    if (s === 'cancelled') return 'status-cancelled';
    return 'status-confirmed';
  }

  get patientName(): string {
    return this.data?.patient || this.data?.patient_name || 'You';
  }
}
