import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../services/dashboard.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent {
  protected readonly dashboardService = inject(DashboardService);
  protected readonly state = this.dashboardService.state;

  onSelectSlot(slotId: string): void {
    this.dashboardService.selectSlot(slotId);
  }
}
