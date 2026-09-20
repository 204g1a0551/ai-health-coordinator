import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MedicineInfo, PharmacyStore } from '../../../models/pharmacy.model';

@Component({
  selector: 'app-nearby-pharmacies',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './nearby-pharmacies.component.html',
  styleUrl: './nearby-pharmacies.component.css',
})
export class NearbyPharmaciesComponent {
  @Input() data: any;

  get medicines(): MedicineInfo[] {
    return this.data?.medicine_details || [];
  }

  get medicineNames(): string[] {
    return this.data?.medicines_searched || [];
  }

  get location(): string {
    return this.data?.location_searched || 'Bengaluru';
  }

  get pharmacies(): PharmacyStore[] {
    return this.data?.pharmacies || [];
  }

  get disclaimer(): string {
    return (
      this.data?.disclaimer ||
      'Medicines are listed strictly as extracted from your uploaded prescription. Please consult your physician or pharmacist.'
    );
  }

  distanceLabel(km: number): string {
    if (km < 1) {
      return `${Math.round(km * 1000)} m away`;
    }
    return `${km.toFixed(1)} km away`;
  }

  distanceClass(km: number): string {
    if (km <= 1.5) return 'dist-close';
    if (km <= 5.0) return 'dist-mid';
    return 'dist-far';
  }

  stars(rating: number): string[] {
    const full = Math.round(rating);
    return Array.from({ length: 5 }, (_, i) => (i < full ? '★' : '☆'));
  }
}
