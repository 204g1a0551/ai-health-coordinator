import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../services/dashboard.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit {
  protected readonly dashboardService = inject(DashboardService);
  protected readonly state = this.dashboardService.state;
  protected readonly isLoading = this.dashboardService.isLoading;

  ngOnInit(): void {
    this.dashboardService.loadDashboard().subscribe();
  }

  onSelectSlot(slotId: string, isAvailable: boolean): void {
    if (!isAvailable) return;
    this.dashboardService.selectSlot(slotId);
  }
}
