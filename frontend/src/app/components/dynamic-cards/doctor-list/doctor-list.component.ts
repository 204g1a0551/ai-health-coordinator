import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-doctor-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './doctor-list.component.html',
  styleUrl: './doctor-list.component.css',
})
export class DoctorListComponent {
  @Input() data: any = null;
  @Output() selectDoctor = new EventEmitter<string>();
  @Output() selectSlot = new EventEmitter<{ doctor: string; time: string }>();

  get doctors(): any[] {
    if (this.data?.doctors && Array.isArray(this.data.doctors)) {
      return this.data.doctors;
    }
    return [];
  }

  get departmentName(): string {
    return this.data?.department || 'Specialists';
  }

  onDoctorClick(docName: string): void {
    this.selectDoctor.emit(docName);
  }

  onSlotClick(docName: string, time: string, event: Event): void {
    event.stopPropagation();
    this.selectSlot.emit({ doctor: docName, time });
  }
}
