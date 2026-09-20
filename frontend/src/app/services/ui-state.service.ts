import { Injectable, signal } from '@angular/core';

export type UIActionType =
  | 'SHOW_WELCOME'
  | 'SHOW_PATIENT_INFO'
  | 'SHOW_SYMPTOMS'
  | 'SHOW_DEPARTMENT'
  | 'SHOW_DOCTORS'
  | 'SHOW_DOCTOR_DETAILS'
  | 'SHOW_SLOTS'
  | 'SHOW_NEARBY_DOCTORS'
  | 'SHOW_PHARMACIES'
  | 'SHOW_APPOINTMENT'
  | 'HIDE_COMPONENT'
  | 'CLEAR_DASHBOARD';

export interface UIState {
  currentComponent: UIActionType;
  currentData: any;
  conversationContext?: any;
  lastUpdated: string;
}

const INITIAL_UI_STATE: UIState = {
  currentComponent: 'SHOW_WELCOME',
  currentData: null,
  conversationContext: null,
  lastUpdated: new Date().toISOString(),
};

@Injectable({
  providedIn: 'root',
})
export class UIStateService {
  readonly state = signal<UIState>(INITIAL_UI_STATE);

  /**
   * Dispatches a controlled UI action and updates the left dynamic dashboard canvas
   */
  dispatchAction(action: string, data: any, context?: any): void {
    const normalized = this.normalizeAction(action);
    this.state.set({
      currentComponent: normalized,
      currentData: data,
      conversationContext: context || this.state().conversationContext,
      lastUpdated: new Date().toISOString(),
    });
  }

  /**
   * Resets the dynamic canvas to the initial WelcomeComponent
   */
  clearDashboard(): void {
    this.state.set({
      currentComponent: 'SHOW_WELCOME',
      currentData: null,
      conversationContext: null,
      lastUpdated: new Date().toISOString(),
    });
  }

  hideComponent(): void {
    this.clearDashboard();
  }

  private normalizeAction(action: string): UIActionType {
    const act = (action || '').toUpperCase().trim();
    switch (act) {
      case 'SHOW_WELCOME':
        return 'SHOW_WELCOME';
      case 'SHOW_PATIENT_INFO':
      case 'UPDATE_PATIENT':
        return 'SHOW_PATIENT_INFO';
      case 'SHOW_SYMPTOMS':
      case 'UPDATE_SYMPTOMS':
        return 'SHOW_SYMPTOMS';
      case 'SHOW_DEPARTMENT':
      case 'UPDATE_DEPARTMENT':
        return 'SHOW_DEPARTMENT';
      case 'SHOW_DOCTORS':
      case 'UPDATE_DOCTORS_AND_SLOTS':
        return 'SHOW_DOCTORS';
      case 'SHOW_DOCTOR_DETAILS':
        return 'SHOW_DOCTOR_DETAILS';
      case 'SHOW_SLOTS':
        return 'SHOW_SLOTS';
      case 'SHOW_NEARBY_DOCTORS':
        return 'SHOW_NEARBY_DOCTORS';
      case 'SHOW_PHARMACIES':
        return 'SHOW_PHARMACIES';
      case 'SHOW_APPOINTMENT':
      case 'BOOK_APPOINTMENT':
        return 'SHOW_APPOINTMENT';
      case 'CLEAR_DASHBOARD':
      case 'CLEAR_APPOINTMENT':
      case 'HIDE_COMPONENT':
        return 'SHOW_WELCOME';
      default:
        return 'SHOW_WELCOME';
    }
  }
}
