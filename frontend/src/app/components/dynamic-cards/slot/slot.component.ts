import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-slot',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './slot.component.html',
  styleUrl: './slot.component.css',
})
export class SlotComponent {
  @Input() data: any = null;
  @Output() slotSelected = new EventEmitter<{ doctor: string; time: string }>();

  get doctorName(): string {
    return this.data?.doctor || 'Dr. Ravi Kumar';
  }

  get date(): string {
    return this.data?.date || 'Tomorrow, Oct 24';
  }

  get slots(): string[] {
    const raw = this.data?.slots;
    if (Array.isArray(raw)) {
      return raw.map((s) => (typeof s === 'string' ? s : s.time || ''));
    }
    return ['5:30 PM', '6:30 PM'];
  }

  onSelectSlot(time: string): void {
    this.slotSelected.emit({ doctor: this.doctorName, time });
  }
}
