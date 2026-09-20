import { Injectable, signal } from '@angular/core';
import { DashboardState, Symptom } from '../models/dashboard.model';

export const INITIAL_DASHBOARD_STATE: DashboardState = {
  patient: {
    name: 'Sarah Connor',
    age: 32,
    phone: '+1 (555) 019-2834',
  },
  symptoms: [], // Empty initially until user shares symptoms with AI agent
  suggestedDepartment: {
    name: '', // Unassigned initially
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
  readonly state = signal<DashboardState>(INITIAL_DASHBOARD_STATE);

  /**
   * Dynamically update symptoms based on Symptom Agent structured output
   */
  updateSymptoms(symptoms: Symptom[]): void {
    this.state.update((s) => ({
      ...s,
      symptoms: symptoms.map((item) => ({
        name: item.name,
        duration: item.duration || undefined,
      })),
    }));
  }

  /**
   * Dynamically update suggested department based on Department Agent structured output
   */
  updateDepartment(departmentName: string): void {
    this.state.update((s) => ({
      ...s,
      suggestedDepartment: {
        name: departmentName,
      },
      appointmentSummary: {
        ...s.appointmentSummary,
        department: departmentName,
      },
    }));
  }

  /**
   * Process structured UI actions returned by the backend coordinator
   */
  applyActions(actions: any[]): void {
    if (!actions || !Array.isArray(actions)) return;

    for (const action of actions) {
      if (action.type === 'UPDATE_SYMPTOMS' && action.payload?.symptoms) {
        this.updateSymptoms(action.payload.symptoms);
      } else if (action.type === 'UPDATE_DEPARTMENT' && action.payload?.department) {
        this.updateDepartment(action.payload.department);
      }
    }
  }

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
}
