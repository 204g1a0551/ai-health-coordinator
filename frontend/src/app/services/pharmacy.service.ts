import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  MedicineSearchRequest,
  MedicineSearchResponse,
  PharmacyStore,
  MedicineInfo,
} from '../models/pharmacy.model';

@Injectable({
  providedIn: 'root',
})
export class PharmacyService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiUrl}/pharmacies`;

  // Reactive state
  readonly searchResults = signal<MedicineSearchResponse | null>(null);
  readonly isLoading = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly selectedLocality = signal<string>('Koramangala');
  readonly userCoords = signal<{ lat: number; lng: number } | null>(null);
  readonly localities = signal<string[]>([
    'Koramangala',
    'Indiranagar',
    'HSR Layout',
    'Whitefield',
    'Jayanagar',
    'Hebbal',
    'Malleshwaram',
    'Bellandur',
  ]);

  constructor() {
    this.fetchLocalities();
  }

  fetchLocalities(): void {
    this.http.get<any>(`${this.apiUrl}/localities`).subscribe({
      next: (res) => {
        if (Array.isArray(res) && res.length > 0) {
          const names = res.map((item: any) =>
            typeof item === 'string' ? item : item.name || item.key || item
          );
          this.localities.set(names);
        } else if (res && res.localities && Array.isArray(res.localities)) {
          this.localities.set(res.localities);
        }
      },
      error: () => {},
    });
  }

  /**
   * Searches for nearby pharmacies stocking medicines from an uploaded document.
   */
  searchForDocument(
    documentId?: string,
    locality?: string,
    lat?: number,
    lng?: number
  ): Observable<MedicineSearchResponse> {
    const loc = locality || this.selectedLocality();
    const coords = lat && lng ? { lat, lng } : this.userCoords();

    this.isLoading.set(true);
    this.error.set(null);

    const req: MedicineSearchRequest = {
      document_id: documentId,
      locality: loc,
      lat: coords?.lat,
      lng: coords?.lng,
    };

    return this.http.post<MedicineSearchResponse>(`${this.apiUrl}/search`, req).pipe(
      tap({
        next: (res) => {
          this.isLoading.set(false);
          this.searchResults.set(res);
        },
        error: (err) => {
          this.isLoading.set(false);
          const msg = err.error?.detail || err.message || 'Failed to search pharmacies.';
          this.error.set(msg);
        },
      })
    );
  }

  /**
   * Searches for explicit medicines and returns nearby stores.
   */
  searchExplicitMedicines(
    medicines: string[],
    locality?: string,
    lat?: number,
    lng?: number
  ): Observable<MedicineSearchResponse> {
    const loc = locality || this.selectedLocality();
    const coords = lat && lng ? { lat, lng } : this.userCoords();

    this.isLoading.set(true);
    this.error.set(null);

    const req: MedicineSearchRequest = {
      explicit_medicines: medicines,
      locality: loc,
      lat: coords?.lat,
      lng: coords?.lng,
    };

    return this.http.post<MedicineSearchResponse>(`${this.apiUrl}/search`, req).pipe(
      tap({
        next: (res) => {
          this.isLoading.set(false);
          this.searchResults.set(res);
        },
        error: (err) => {
          this.isLoading.set(false);
          const msg = err.error?.detail || err.message || 'Failed to search pharmacies.';
          this.error.set(msg);
        },
      })
    );
  }

  /**
   * Request browser geolocation permission and store coordinates.
   */
  requestGeolocation(): Promise<{ lat: number; lng: number }> {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by your browser.'));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const coords = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          };
          this.userCoords.set(coords);
          resolve(coords);
        },
        (err) => {
          reject(err);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
      );
    });
  }

  clearResults(): void {
    this.searchResults.set(null);
    this.error.set(null);
  }
}
