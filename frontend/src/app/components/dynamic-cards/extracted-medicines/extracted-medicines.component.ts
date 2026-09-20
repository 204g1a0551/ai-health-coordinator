import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface PrescribedMedicine {
  name: string;
  dosage: string;
  frequency: string;
  duration?: string;
  instructions?: string;
  source_page?: number;
}

@Component({
  selector: 'app-extracted-medicines',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './extracted-medicines.component.html',
  styleUrl: './extracted-medicines.component.css',
})
export class ExtractedMedicinesComponent {
  @Input() data: any;
  @Output() actionClicked = new EventEmitter<string>();
  @Output() checkInteractions = new EventEmitter<void>();

  get medicines(): PrescribedMedicine[] {
    return this.data?.medicines || [
      {
        name: 'Augmentin 625mg',
        dosage: '625mg',
        frequency: 'Twice daily (after meals)',
        duration: '5 days',
        instructions: 'Complete full antibiotic course',
        source_page: 1,
      },
      {
        name: 'Dolo 650',
        dosage: '650mg',
        frequency: 'Once or twice daily as needed',
        duration: '3 days',
        instructions: 'Take after meals for fever/pain',
        source_page: 1,
      },
    ];
  }

  get docName(): string {
    return this.data?.document_name || 'prescription.pdf';
  }

  get sourcePage(): number {
    return this.data?.source_page || 1;
  }

  onSelectAction(prompt: string): void {
    this.actionClicked.emit(prompt);
  }

  onCheckInteractions(): void {
    this.checkInteractions.emit();
  }
}
