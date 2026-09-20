import { Component, Input, Output, EventEmitter, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface LabTestItem {
  test_name: string;
  result: string;
  unit: string;
  reference_range: string;
  status: string;
  is_out_of_range: boolean;
  source_page: number;
  panel_name?: string;
}

@Component({
  selector: 'app-lab-results',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './lab-results.component.html',
  styleUrl: './lab-results.component.css',
})
export class LabResultsComponent {
  @Input() data: any;
  @Output() actionClicked = new EventEmitter<string>();

  readonly filterMode = signal<'all' | 'outside'>('all');
  readonly searchQuery = signal<string>('');

  get tests(): LabTestItem[] {
    return this.data?.tests || [];
  }

  get documentName(): string {
    return this.data?.document_name || 'cbc_lab_report.pdf';
  }

  get laboratoryName(): string {
    return this.data?.laboratory_name || 'Metropolis Healthcare & Clinical Reference Lab';
  }

  get reportDate(): string {
    return this.data?.report_date || '2026-09-18';
  }

  get totalTests(): number {
    return this.tests.length;
  }

  get outOfRangeCount(): number {
    return this.tests.filter((t) => t.is_out_of_range).length;
  }

  get disclaimer(): string {
    return (
      this.data?.disclaimer ||
      'Important: Values outside the stated reference ranges are reported strictly as extracted ' +
      'from the laboratory document. This information is for clinical tracking only and does NOT constitute ' +
      'a medical diagnosis or clinical conclusion. Please consult a licensed physician.'
    );
  }

  readonly filteredTests = computed(() => {
    const list = this.tests;
    const mode = this.filterMode();
    const query = this.searchQuery().toLowerCase().trim();

    return list.filter((t) => {
      if (mode === 'outside' && !t.is_out_of_range) {
        return false;
      }
      if (query && !t.test_name.toLowerCase().includes(query) && !(t.panel_name || '').toLowerCase().includes(query)) {
        return false;
      }
      return true;
    });
  });

  setFilter(mode: 'all' | 'outside'): void {
    this.filterMode.set(mode);
  }

  onSelectAction(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
