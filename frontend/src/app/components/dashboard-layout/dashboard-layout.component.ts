import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { DashboardComponent } from '../dashboard/dashboard.component';
import { ChatComponent } from '../chat/chat.component';
import { MedicalDocumentsComponent } from '../medical-documents/medical-documents.component';
import { InsuranceReimbursementComponent } from '../insurance-reimbursement/insurance-reimbursement.component';
import { LabReportsComponent } from '../lab-reports/lab-reports.component';
import { BillVerificationComponent } from '../bill-verification/bill-verification.component';
import { DrugInteractionPageComponent } from '../drug-interaction-page/drug-interaction-page.component';
import { CostSaverPageComponent } from '../cost-saver-page/cost-saver-page.component';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-dashboard-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    DashboardComponent,
    ChatComponent,
    MedicalDocumentsComponent,
    InsuranceReimbursementComponent,
    LabReportsComponent,
    BillVerificationComponent,
    DrugInteractionPageComponent,
    CostSaverPageComponent,
  ],
  templateUrl: './dashboard-layout.component.html',
  styleUrl: './dashboard-layout.component.css',
})
export class DashboardLayoutComponent {
  public authService = inject(AuthService);
  private router = inject(Router);

  isDocumentsPage = false;
  isInsurancePage = false;
  isLabReportsPage = false;
  isBillVerificationPage = false;
  isDrugInteractionsPage = false;
  isCostSaverPage = false;

  activeMobileTab: 'workspace' | 'chat' = 'workspace';

  constructor() {
    this.checkRoute(this.router.url);
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe((event) => {
        this.checkRoute(event.urlAfterRedirects || event.url);
      });
  }

  setMobileTab(tab: 'workspace' | 'chat'): void {
    this.activeMobileTab = tab;
  }

  private checkRoute(url: string): void {
    this.isDocumentsPage = url.includes('/documents');
    this.isInsurancePage = url.includes('/insurance');
    this.isLabReportsPage = url.includes('/lab-reports');
    this.isBillVerificationPage = url.includes('/bill-verification');
    this.isDrugInteractionsPage = url.includes('/drug-interactions');
    this.isCostSaverPage = url.includes('/cost-saver');
  }

  onLogout(): void {
    this.authService.logout();
  }
}
