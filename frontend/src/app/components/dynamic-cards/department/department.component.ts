import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-department',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './department.component.html',
  styleUrl: './department.component.css',
})
export class DepartmentComponent {
  @Input() data: any = null;

  get departmentName(): string {
    return this.data?.department || 'General Medicine';
  }

  get departmentReason(): string {
    return this.data?.reason || `Based on your reported symptoms, consultation with ${this.departmentName} is recommended for comprehensive assessment.`;
  }
}
