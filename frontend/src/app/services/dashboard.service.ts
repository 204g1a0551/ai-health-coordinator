import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, of, tap } from 'rxjs';
import { DashboardState } from '../models/dashboard.model';

const INITIAL_DEFAULT_STATE: DashboardState = {
  patient: {
    name: 'John Doe',
    age: 34,
    gender: 'Male',
    contact: '+1 (555) 234-5678',
  },
  symptoms: [
    { name: 'Persistent Dry Cough', severity: 'Moderate', duration: '3 days' },
    { name: 'Mild Fever (100.2°F)', severity: 'Mild', duration: '2 days' },
    { name: 'Fatigue & Body Aches', severity: 'Mild', duration: '1 day' },
  ],
  suggested_department: {
    name: 'General Medicine',
    confidence: 'High',
    description: 'Recommended for initial evaluation of respiratory and febrile symptoms.',
  },
  available_doctors: [
    {
      id: 'doc-1',
      name: 'Dr. Sarah Jenkins, MD',
      specialty: 'General Internal Medicine',
      qualification: 'MD, Harvard Medical School',
      experience: '12 years',
    },
    {
      id: 'doc-2',
      name: 'Dr. Robert Miller, MD',
      specialty: 'Pulmonology & Respiratory Care',
      qualification: 'MD, Johns Hopkins',
      experience: '15 years',
    },
    {
      id: 'doc-3',
      name: 'Dr. Emily Chen, DO',
      specialty: 'Family & Community Medicine',
      qualification: 'DO, Stanford Medicine',
      experience: '8 years',
    },
  ],
  available_time_slots: [
    { id: 'slot-1', doctor_id: 'doc-1', time: '09:30 AM', date: 'Tomorrow, Oct 24', is_available: true },
    { id: 'slot-2', doctor_id: 'doc-1', time: '10:30 AM', date: 'Tomorrow, Oct 24', is_available: true },
    { id: 'slot-3', doctor_id: 'doc-1', time: '02:00 PM', date: 'Tomorrow, Oct 24', is_available: true },
    { id: 'slot-4', doctor_id: 'doc-2', time: '11:15 AM', date: 'Tomorrow, Oct 24', is_available: true },
    { id: 'slot-5', doctor_id: 'doc-2', time: '03:30 PM', date: 'Tomorrow, Oct 24', is_available: false },
    { id: 'slot-6', doctor_id: 'doc-3', time: '04:00 PM', date: 'Tomorrow, Oct 24', is_available: true },
  ],
  appointment_summary: {
    patient_name: 'John Doe',
    department: 'General Medicine',
    doctor_name: 'Dr. Sarah Jenkins, MD',
    slot_time: '10:30 AM',
    appointment_date: 'Tomorrow, Oct 24',
    status: 'Pending Confirmation',
  },
};

@Injectable({
  providedIn: 'root',
})
export class DashboardService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/dashboard';

  // Reactive state signal for the dashboard
  readonly state = signal<DashboardState>(INITIAL_DEFAULT_STATE);
  readonly isLoading = signal<boolean>(false);

  loadDashboard(): Observable<DashboardState> {
    this.isLoading.set(true);
    return this.http.get<DashboardState>(this.apiUrl).pipe(
      tap((data) => {
        if (data) {
          this.state.set(data);
        }
        this.isLoading.set(false);
      }),
      catchError((error) => {
        console.warn('Could not fetch dashboard from backend, using default initial state:', error);
        this.isLoading.set(false);
        return of(this.state());
      })
    );
  }

  updatePatient(name: string, contact?: string) {
    this.state.update((s) => ({
      ...s,
      patient: { ...s.patient, name, contact: contact ?? s.patient.contact },
      appointment_summary: { ...s.appointment_summary, patient_name: name },
    }));
  }

  selectSlot(slotId: string) {
    const slot = this.state().available_time_slots.find((s) => s.id === slotId);
    if (!slot) return;
    const doctor = this.state().available_doctors.find((d) => d.id === slot.doctor_id);

    this.state.update((s) => ({
      ...s,
      appointment_summary: {
        ...s.appointment_summary,
        slot_time: slot.time,
        appointment_date: slot.date,
        doctor_name: doctor ? doctor.name : s.appointment_summary.doctor_name,
        department: doctor ? doctor.specialty : s.appointment_summary.department,
      },
    }));
  }
}
