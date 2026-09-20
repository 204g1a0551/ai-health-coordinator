export interface PatientInfo {
  name: string;
  age?: number | string;
  phone?: string;
  preferredDepartment?: string;
}

export interface Symptom {
  name: string;
  duration?: string;
}

export interface SuggestedDepartment {
  name: string;
}

export interface Doctor {
  id: string;
  name: string;
  department: string;
  availableStatus: 'Available' | 'Unavailable' | 'In Consultation';
  hospital?: string;
  clinic?: string;
  locality?: string;
  address?: string;
  consultationFee?: string;
  consultationType?: string;
  experience?: string;
  rating?: number;
  dataSource?: string;
  timestamp?: string;
}

export interface TimeSlot {
  id: string;
  date: string;
  time: string;
  doctor: string;
  isAvailable: boolean;
  hospital?: string;
  locality?: string;
  consultationType?: string;
  dataSource?: string;
  timestamp?: string;
}

export interface ProviderInfo {
  dataSource?: string;
  timestamp?: string;
  locality?: string;
}

export interface AppointmentSummary {
  doctor: string;
  department: string;
  date: string;
  time: string;
  status: string;
  hospital?: string;
  locality?: string;
}

export interface DashboardState {
  patient: PatientInfo;
  symptoms: Symptom[];
  suggestedDepartment: SuggestedDepartment;
  doctors: Doctor[];
  availableSlots: TimeSlot[];
  appointmentSummary: AppointmentSummary;
  providerInfo?: ProviderInfo;
}

export interface UIAction {
  action: string;
  payload: any;
  type?: string;
}

