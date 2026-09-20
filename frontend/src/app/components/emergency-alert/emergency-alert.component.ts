import { Component, inject, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UIStateService } from '../../services/ui-state.service';

@Component({
  selector: 'app-emergency-alert',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './emergency-alert.component.html',
  styleUrl: './emergency-alert.component.css',
})
export class EmergencyAlertComponent {
  readonly data = input<Record<string, any> | null>(null);
  private readonly uiState = inject(UIStateService);
  locality = '';
  locationUrl: string | null = null;
  locationError = '';

  get contacts(): Array<Record<string, any>> {
    return this.data()?.['contacts'] ?? [];
  }

  locateEmergencyDepartment(): void {
    this.locationError = '';
    if (!navigator.geolocation) {
      this.locationError = 'Location is unavailable. Enter your locality below.';
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        this.locationUrl = this.mapsUrl(`${position.coords.latitude},${position.coords.longitude}`);
      },
      () => {
        this.locationError = 'Location permission was not granted. Enter your locality below.';
      },
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 },
    );
  }

  searchByLocality(): void {
    const value = this.locality.trim();
    if (value) this.locationUrl = this.mapsUrl(`${value} emergency department`);
  }

  clearEmergencyState(): void {
    this.uiState.clearEmergencyState();
  }

  private mapsUrl(query: string): string {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
  }
}
