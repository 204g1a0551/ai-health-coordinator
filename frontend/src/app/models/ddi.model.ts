export interface NormalizedMedicine {
  originalName: string;
  normalizedName?: string;
  rxcui?: string;
  sourceDocumentIds: string[];
  status: string;
  message?: string;
}

export interface DDIInteraction {
  medicineA: string;
  medicineB: string;
  interactionDescription: string;
  severity?: string;
  category?: string;
  source: string;
  warning: string;
  recommendation: string;
}

export interface DDIInteractionResponse {
  medicines: NormalizedMedicine[];
  interactions: DDIInteraction[];
  unresolvedMedicines: string[];
  databaseStatus: string;
  message: string;
  disclaimer: string;
}
