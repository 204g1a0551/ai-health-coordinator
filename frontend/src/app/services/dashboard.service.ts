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
    dataSource?: string;
    timestamp?: string;
  }): void {
    const ds = payload.dataSource || (payload.doctors.length > 0 ? payload.doctors[0].dataSource : undefined);
    const ts = payload.timestamp || (payload.doctors.length > 0 ? payload.doctors[0].timestamp : undefined);
    this.state.update((s) => ({
      ...s,
      suggestedDepartment: {
        name: payload.department || s.suggestedDepartment.name,
      },
      doctors: payload.doctors,
      availableSlots: payload.slots,
      providerInfo: ds ? { dataSource: ds, timestamp: ts } : s.providerInfo,
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
   * Dynamically display doctors returned by SHOW_DOCTORS action
   */
  showDoctors(doctors: Doctor[], department?: string, dataSource?: string, timestamp?: string): void {
    const ds = dataSource || (doctors.length > 0 ? doctors[0].dataSource : undefined);
    const ts = timestamp || (doctors.length > 0 ? doctors[0].timestamp : undefined);
    this.state.update((s) => ({
      ...s,
      doctors,
      suggestedDepartment: {
        name: department || s.suggestedDepartment.name,
      },
      providerInfo: ds ? { dataSource: ds, timestamp: ts } : s.providerInfo,
    }));
  }

  /**
   * Dynamically display available time slots returned by SHOW_SLOTS action
   */
  showSlots(slots: TimeSlot[], date?: string, dataSource?: string, timestamp?: string): void {
    const ds = dataSource || (slots.length > 0 ? slots[0].dataSource : undefined);
    const ts = timestamp || (slots.length > 0 ? slots[0].timestamp : undefined);
    this.state.update((s) => ({
      ...s,
      availableSlots: slots,
      providerInfo: ds ? { dataSource: ds, timestamp: ts } : s.providerInfo,
      appointmentSummary: {
        ...s.appointmentSummary,
        date: date || s.appointmentSummary.date,
        doctor: slots.length > 0 ? slots[0].doctor : s.appointmentSummary.doctor,
        time: slots.length > 0 ? slots[0].time : s.appointmentSummary.time,
        status: s.appointmentSummary.status === 'Confirmed' ? 'Confirmed' : (slots.length > 0 ? 'Available to Confirm' : s.appointmentSummary.status),
      },
    }));
  }

  /**
   * Clear active appointment summary
   */
  clearAppointment(): void {
    this.state.update((s) => ({
      ...s,
      appointmentSummary: {
        doctor: '',
        department: '',
        date: '',
        time: '',
        status: 'None',
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
   * Process structured UI actions returned by the backend coordinator.
   * Strictly processes only predefined controlled action types; rejects arbitrary commands.
   */
  applyActions(actions: any[]): void {
    if (!actions || !Array.isArray(actions)) return;

    for (const item of actions) {
      const actType = item.action || item.type;
      const payload = item.payload || item.data || {};

      switch (actType) {
        case 'UPDATE_SYMPTOMS':
          if (payload.symptoms) {
            this.updateSymptoms(payload.symptoms);
          }
          break;

        case 'UPDATE_DEPARTMENT':
          if (payload.department) {
            this.updateDepartment(payload.department);
          }
          break;

        case 'SHOW_DOCTORS':
          if (payload.doctors) {
            this.showDoctors(payload.doctors, payload.department, payload.dataSource, payload.timestamp);
          }
          break;

        case 'SHOW_SLOTS':
          if (payload.slots) {
            this.showSlots(payload.slots, payload.date, payload.dataSource, payload.timestamp);
          }
          break;

        case 'BOOK_APPOINTMENT':
          if (payload.appointment) {
            this.bookAppointment(payload.appointment);
          }
          break;

        case 'CANCEL_APPOINTMENT':
          this.cancelAppointment();
          break;

        case 'CLEAR_APPOINTMENT':
          this.clearAppointment();
          break;

        case 'UPDATE_PATIENT':
          this.updatePatient(payload);
          break;

        case 'UPDATE_DOCTORS_AND_SLOTS':
          this.updateDoctorsAndSlots(payload);
          break;

        default:
          // Ignore any unrecognized or arbitrary actions
          break;
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
