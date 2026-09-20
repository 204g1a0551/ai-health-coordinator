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
import { NearbyPharmaciesComponent } from '../dynamic-cards/nearby-pharmacies/nearby-pharmacies.component';
import { AppointmentComponent } from '../dynamic-cards/appointment/appointment.component';
import { MedicalDocumentUploadComponent } from '../dynamic-cards/medical-document-upload/medical-document-upload.component';
import { DocumentSummaryComponent } from '../dynamic-cards/document-summary/document-summary.component';
import { ExtractedMedicinesComponent } from '../dynamic-cards/extracted-medicines/extracted-medicines.component';
import { MedicineInformationComponent } from '../dynamic-cards/medicine-information/medicine-information.component';
import { InsurancePolicyComponent } from '../dynamic-cards/insurance-policy/insurance-policy.component';
import { CoverageAnalysisComponent } from '../dynamic-cards/coverage-analysis/coverage-analysis.component';
import { DocumentEvidenceComponent } from '../dynamic-cards/document-evidence/document-evidence.component';
import { LabReportComponent } from '../dynamic-cards/lab-report/lab-report.component';
import { LabResultsComponent } from '../dynamic-cards/lab-results/lab-results.component';
import { LabEvidenceComponent } from '../dynamic-cards/lab-evidence/lab-evidence.component';
import { EmergencyAlertComponent } from '../emergency-alert/emergency-alert.component';
import { DDIInteractionComponent } from '../ddi-interaction/ddi-interaction.component';
import { DDIService } from '../../services/ddi.service';

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
    NearbyPharmaciesComponent,
    AppointmentComponent,
    MedicalDocumentUploadComponent,
    DocumentSummaryComponent,
    ExtractedMedicinesComponent,
    MedicineInformationComponent,
    InsurancePolicyComponent,
    CoverageAnalysisComponent,
    DocumentEvidenceComponent,
    LabReportComponent,
    LabResultsComponent,
    LabEvidenceComponent,
    EmergencyAlertComponent,
    DDIInteractionComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent {
  protected readonly uiState = inject(UIStateService);
  protected readonly chatService = inject(ChatService);
  protected readonly ddiService = inject(DDIService);

  /** Handle document upload completion */
  onDocumentUploaded(summaryData: any): void {
    this.uiState.dispatchAction('SHOW_DOCUMENT_SUMMARY', summaryData);
  }

  /** Forward prompt-chip selection from WelcomeComponent to the chat */
  onPromptSelected(prompt: string): void {
    this.chatService.sendMessage(prompt).subscribe({
      error: () => {/* handled by ChatService itself */}
    });
  }

  onCheckDrugInteractions(): void {
    this.ddiService.check().subscribe({
      next: (result) => this.uiState.dispatchAction('SHOW_DRUG_INTERACTIONS', result),
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
