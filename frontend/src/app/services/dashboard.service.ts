import { Injectable, signal } from '@angular/core';
import { DashboardState, PatientInfo, Symptom, Doctor, TimeSlot } from '../models/dashboard.model';

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
  doctors: [], // Initially empty until doctor/slot agent runs
  availableSlots: [], // Initially empty until slots are queried
  appointmentSummary: {
    doctor: '',
    department: '',
    date: '',
    time: '',
    status: 'Pending',
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
   * Dynamically update available doctors and time slots from Doctor/Slot Agent
   */
  updateDoctorsAndSlots(payload: {
    department?: string;
    date?: string;
    doctors: Doctor[];
    slots: TimeSlot[];
  }): void {
    this.state.update((s) => ({
      ...s,
      suggestedDepartment: {
        name: payload.department || s.suggestedDepartment.name,
      },
      doctors: payload.doctors,
      availableSlots: payload.slots,
      appointmentSummary: {
        ...s.appointmentSummary,
        department: payload.department || s.appointmentSummary.department,
        doctor: payload.doctors.length > 0 ? payload.doctors[0].name : s.appointmentSummary.doctor,
        date: payload.date || s.appointmentSummary.date,
        time: payload.slots.length > 0 ? payload.slots[0].time : s.appointmentSummary.time,
        status: 'Available to Confirm',
      },
    }));
  }

  /**
   * Update appointment state when an appointment is booked
   */
  bookAppointment(appt: {
    doctor: string;
    department: string;
    date: string;
    displayDate?: string;
    time: string;
    status: string;
  }): void {
    const formattedDate = appt.displayDate || (appt.date === '2026-09-21' ? '21 Sep 2026' : appt.date);
    const formattedTime = (appt.time === '18:00' || appt.time === '6 PM') ? '6:00 PM' : appt.time;

    this.state.update((s) => ({
      ...s,
      suggestedDepartment: {
        name: appt.department || s.suggestedDepartment.name,
      },
      appointmentSummary: {
        doctor: appt.doctor,
        department: appt.department,
        date: formattedDate,
        time: formattedTime,
        status: 'Confirmed',
      },
    }));
  }

  /**
   * Cancel active appointment
   */
  cancelAppointment(): void {
    this.state.update((s) => ({
      ...s,
      appointmentSummary: {
        ...s.appointmentSummary,
        status: 'Cancelled',
      },
    }));
  }

  /**
   * Dynamically update patient info from Patient Info Agent structured output
   */
  updatePatient(data: Partial<PatientInfo> & { preferred_department?: string }): void {
    this.state.update((s) => ({
      ...s,
      patient: {
        ...s.patient,
        ...data,
        preferredDepartment: data.preferred_department || data.preferredDepartment || s.patient.preferredDepartment,
      },
    }));
  }

  /**
   * Process structured UI actions returned by the backend coordinator
   */
  applyActions(actions: any[]): void {
    if (!actions || !Array.isArray(actions)) return;

    for (const action of actions) {
      if (action.type === 'UPDATE_PATIENT' || action.action === 'UPDATE_PATIENT') {
        const payloadData = action.data || action.payload?.data || action.payload;
        if (payloadData) {
          this.updatePatient(payloadData);
        }
      } else if (action.type === 'UPDATE_SYMPTOMS' && action.payload?.symptoms) {
        this.updateSymptoms(action.payload.symptoms);
      } else if (action.type === 'UPDATE_DEPARTMENT' && action.payload?.department) {
        this.updateDepartment(action.payload.department);
      } else if (action.type === 'UPDATE_DOCTORS_AND_SLOTS' && action.payload) {
        this.updateDoctorsAndSlots(action.payload);
      } else if (action.type === 'BOOK_APPOINTMENT' && action.payload?.appointment) {
        this.bookAppointment(action.payload.appointment);
      } else if (action.type === 'CANCEL_APPOINTMENT') {
        this.cancelAppointment();
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
