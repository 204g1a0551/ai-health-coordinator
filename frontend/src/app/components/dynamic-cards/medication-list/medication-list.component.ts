import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NormalizedMedication } from '../../../models/drug-interaction.model';

@Component({
  selector: 'app-medication-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './medication-list.component.html',
  styleUrls: ['./medication-list.component.css'],
})
export class MedicationListComponent {
  @Input() data: any = {};
  @Output() actionClicked = new EventEmitter<string>();

  get medications(): NormalizedMedication[] {
    return this.data?.medications || this.data?.analysis?.medications || [];
  }

  get duplicates(): any[] {
    return this.data?.duplicates || this.data?.analysis?.duplicate_medications || [];
  }

  askAbout(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
