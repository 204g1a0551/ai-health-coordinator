import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

interface NearbyDoctor {
  name: string;
  department: string;
  distance_km: number;
  hospital?: string;
  rating?: number;
  available?: boolean;
}

@Component({
  selector: 'app-nearby-doctors',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './nearby-doctors.component.html',
  styleUrl: './nearby-doctors.component.css',
})
export class NearbyDoctorsComponent {
  @Input() data: any = null;

  get location(): string {
    return this.data?.location || 'Bengaluru';
  }

  get doctors(): NearbyDoctor[] {
    const raw = this.data?.doctors;
    if (Array.isArray(raw) && raw.length > 0) return raw;
    // fallback demo data
    return [
      { name: 'Dr. Ravi Kumar', department: 'General Medicine', distance_km: 0.8, hospital: 'Apollo Clinic', rating: 4.7, available: true },
      { name: 'Dr. Ananya Sharma', department: 'General Medicine', distance_km: 1.4, hospital: 'Fortis Health', rating: 4.5, available: true },
      { name: 'Dr. Suresh Babu', department: 'General Medicine', distance_km: 2.1, hospital: 'Manipal Hospital', rating: 4.3, available: false },
    ];
  }

  distanceLabel(km: number): string {
    if (km < 1) return `${Math.round(km * 1000)} m`;
    return `${km.toFixed(1)} km`;
  }

  distanceClass(km: number): string {
    if (km < 1) return 'dist-close';
    if (km < 3) return 'dist-medium';
    return 'dist-far';
  }

  stars(rating: number = 0): string[] {
    return Array.from({ length: 5 }, (_, i) => (i < Math.round(rating) ? '★' : '☆'));
  }
}
