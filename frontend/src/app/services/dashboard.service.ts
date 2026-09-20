import { Injectable, signal } from '@angular/core';
import { DashboardState } from '../models/dashboard.model';

export const MOCK_DASHBOARD_STATE: DashboardState = {
  patient: {
    name: 'Sarah Connor',
    age: 32,
    phone: '+1 (555) 019-2834',
  },
  symptoms: [
    { name: 'Fever', duration: '2 days' },
    { name: 'Headache', duration: '1 day' },
    { name: 'Fatigue', duration: '3 days' },
  ],
  suggestedDepartment: {
    name: 'General Medicine',
  },
  doctors: [
    {
      id: 'd1',
      name: 'Dr. Alex Taylor',
      department: 'General Medicine',
      availableStatus: 'Available',
    },
    {
      id: 'd2',
      name: 'Dr. Brenda Vance',
      department: 'Internal Medicine',
      availableStatus: 'Available',
    },
    {
      id: 'd3',
      name: 'Dr. Marcus Reed',
      department: 'Neurology',
      availableStatus: 'Unavailable',
    },
  ],
  availableSlots: [
    {
      id: 's1',
      date: 'Tomorrow, Oct 24',
      time: '09:30 AM',
      doctor: 'Dr. Alex Taylor',
      isAvailable: true,
    },
    {
      id: 's2',
      date: 'Tomorrow, Oct 24',
      time: '11:00 AM',
      doctor: 'Dr. Alex Taylor',
      isAvailable: true,
    },
    {
      id: 's3',
      date: 'Tomorrow, Oct 24',
      time: '02:15 PM',
      doctor: 'Dr. Brenda Vance',
      isAvailable: true,
    },
    {
      id: 's4',
      date: 'Tomorrow, Oct 24',
      time: '04:00 PM',
      doctor: 'Dr. Brenda Vance',
      isAvailable: false,
    },
  ],
  appointmentSummary: {
    doctor: 'Dr. Alex Taylor',
    department: 'General Medicine',
    date: 'Tomorrow, Oct 24',
    time: '11:00 AM',
    status: 'Pending Confirmation',
  },
};

@Injectable({
  providedIn: 'root',
})
export class DashboardService {
  // Reactive dashboard state initialized with mock data
  readonly state = signal<DashboardState>(MOCK_DASHBOARD_STATE);

  selectSlot(slotId: string): void {
    const slot = this.state().availableSlots.find((s) => s.id === slotId);
    if (!slot || !slot.isAvailable) return;

    const matchedDoctor = this.state().doctors.find((d) => d.name === slot.doctor);

    this.state.update((s) => ({
      ...s,
      appointmentSummary: {
        ...s.appointmentSummary,
        doctor: slot.doctor,
        department: matchedDoctor ? matchedDoctor.department : s.appointmentSummary.department,
        date: slot.date,
        time: slot.time,
        status: 'Selected',
      },
    }));
  }

  // Helper method to clear dashboard to demonstrate empty/default state handling
  resetToDefault(): void {
    this.state.set({
      patient: { name: '', age: undefined, phone: '' },
      symptoms: [],
      suggestedDepartment: { name: '' },
      doctors: [],
      availableSlots: [],
      appointmentSummary: {
        doctor: '',
        department: '',
        date: '',
        time: '',
        status: 'None',
      },
    });
  }

  // Restore mock data
  loadMockData(): void {
    this.state.set(MOCK_DASHBOARD_STATE);
  }
}
