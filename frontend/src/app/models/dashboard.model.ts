export interface Patient {
  name: string;
  age?: number;
  gender?: string;
  contact?: string;
}

export interface SymptomItem {
  name: string;
  severity: string;
  duration?: string;
}

export interface Department {
  name: string;
  confidence?: string;
  description?: string;
}

export interface Doctor {
  id: string;
  name: string;
  specialty: string;
  qualification: string;
  experience: string;
}

export interface TimeSlot {
  id: string;
  doctor_id: string;
  time: string;
  date: string;
  is_available: boolean;
}

export interface AppointmentSummary {
  patient_name: string;
  department: string;
  doctor_name: string;
  slot_time: string;
  appointment_date: string;
  status: string;
}

export interface DashboardState {
  patient: Patient;
  symptoms: SymptomItem[];
  suggested_department: Department;
  available_doctors: Doctor[];
  available_time_slots: TimeSlot[];
  appointment_summary: AppointmentSummary;
}
