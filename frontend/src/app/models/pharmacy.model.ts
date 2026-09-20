export interface MedicineInfo {
  medicine_name: string;
  generic_name?: string;
  therapeutic_class?: string;
  dosage_forms: string[];
  standard_strength?: string;
  common_uses: string[];
  storage_instructions?: string;
  prescription_required: boolean;
  public_summary?: string;
}

export interface PharmacyStore {
  id: string;
  name: string;
  chain: string;
  locality: string;
  address: string;
  phone: string;
  timing: string;
  is_24x7: boolean;
  delivery_available: boolean;
  rating: number;
  distance_km: number;
  in_stock_medicines: string[];
}

export interface MedicineSearchRequest {
  document_id?: string;
  explicit_medicines?: string[];
  locality?: string;
  lat?: number;
  lng?: number;
}

export interface MedicineSearchResponse {
  medicines_searched: string[];
  medicine_details: MedicineInfo[];
  location_searched: string;
  user_coordinates?: { lat: number; lng: number };
  pharmacies: PharmacyStore[];
  total_pharmacies_found: number;
  disclaimer: string;
}
