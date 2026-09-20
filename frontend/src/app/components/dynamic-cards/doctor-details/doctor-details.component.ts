import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-doctor-details',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './doctor-details.component.html',
  styleUrl: './doctor-details.component.css',
})
export class DoctorDetailsComponent {
  @Input() data: any = null;
  @Output() viewSlots = new EventEmitter<string>();

  get doctor(): any {
    return this.data?.doctor || {
      name: 'Dr. Ravi Kumar',
      department: 'General Medicine',
      hospital: 'Manipal Hospital',
      locality: 'Old Airport Road',
      address: '98 HAL Old Airport Road, Kodihalli, Bengaluru',
      consultationFee: '₹700',
      consultationType: 'In-Person & Teleconsultation',
      experience: '12+ yrs experience',
      rating: 4.9,
      bio: 'Senior Consultant Physician specializing in general diagnostics, internal medicine, and preventive healthcare.',
    };
  }

  onViewSlots(): void {
    this.viewSlots.emit(this.doctor.name);
  }
}
