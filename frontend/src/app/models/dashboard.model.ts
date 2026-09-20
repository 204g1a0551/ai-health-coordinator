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
}

export interface TimeSlot {
  id: string;
  date: string;
  time: string;
  doctor: string;
  isAvailable: boolean;
}

export interface AppointmentSummary {
  doctor: string;
  department: string;
  date: string;
  time: string;
  status: string;
}

export interface DashboardState {
  patient: PatientInfo;
  symptoms: Symptom[];
  suggestedDepartment: SuggestedDepartment;
  doctors: Doctor[];
  availableSlots: TimeSlot[];
  appointmentSummary: AppointmentSummary;
}

export interface UIAction {
  action: string;
  payload: any;
  type?: string;
}
