import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UIStateService } from '../../services/ui-state.service';
import { ChatService } from '../../services/chat.service';

import { WelcomeComponent } from '../dynamic-cards/welcome/welcome.component';
import { PatientInfoComponent } from '../dynamic-cards/patient-info/patient-info.component';
import { SymptomsComponent } from '../dynamic-cards/symptoms/symptoms.component';
import { DepartmentComponent } from '../dynamic-cards/department/department.component';
import { DoctorListComponent } from '../dynamic-cards/doctor-list/doctor-list.component';
import { DoctorDetailsComponent } from '../dynamic-cards/doctor-details/doctor-details.component';
import { SlotComponent } from '../dynamic-cards/slot/slot.component';
import { NearbyDoctorsComponent } from '../dynamic-cards/nearby-doctors/nearby-doctors.component';
import { AppointmentComponent } from '../dynamic-cards/appointment/appointment.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    WelcomeComponent,
    PatientInfoComponent,
    SymptomsComponent,
    DepartmentComponent,
    DoctorListComponent,
    DoctorDetailsComponent,
    SlotComponent,
    NearbyDoctorsComponent,
    AppointmentComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent {
  protected readonly uiState = inject(UIStateService);
  protected readonly chatService = inject(ChatService);

  /** Forward prompt-chip selection from WelcomeComponent to the chat */
  onPromptSelected(prompt: string): void {
    this.chatService.sendMessage(prompt).subscribe({
      error: () => {/* handled by ChatService itself */}
    });
  }

  /** Forward slot selection to chat as a booking message */
  onSlotSelected(event: { doctor: string; time: string }): void {
    const msg = `Book ${event.doctor} at ${event.time}`;
    this.chatService.sendMessage(msg).subscribe({
      error: () => {}
    });
  }

  /** Forward doctor selection from list to chat */
  onSelectDoctor(docName: string): void {
    this.chatService.sendMessage(`Tell me more about ${docName}`).subscribe({
      error: () => {}
    });
  }

  /** Forward "View Slots" from doctor details to chat */
  onViewSlots(docName: string): void {
    this.chatService.sendMessage(`Show available slots for ${docName}`).subscribe({
      error: () => {}
    });
  }
}
