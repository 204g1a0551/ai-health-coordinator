import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-symptoms',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './symptoms.component.html',
  styleUrl: './symptoms.component.css',
})
export class SymptomsComponent {
  @Input() data: any = null;

  get symptomsList(): Array<{ name: string; duration?: string }> {
    if (this.data?.symptoms && Array.isArray(this.data.symptoms)) {
      return this.data.symptoms;
    }
    return [];
  }
}
