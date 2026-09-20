import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-lab-report',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './lab-report.component.html',
  styleUrl: './lab-report.component.css',
})
export class LabReportComponent {
  @Input() data: any;
  @Output() actionClicked = new EventEmitter<string>();

  get documentName(): string {
    return this.data?.file_name || 'cbc_lab_report.pdf';
  }

  get laboratoryName(): string {
    return this.data?.laboratory_name || 'Metropolis Healthcare & Clinical Reference Lab';
  }

  get reportDate(): string {
    return this.data?.report_date || '2026-09-18';
  }

  get patientName(): string {
    return this.data?.patient_name || 'Sarah Connor';
  }

  get totalTests(): number {
    return this.data?.total_tests || (this.data?.tests?.length ?? 16);
  }

  get outOfRangeCount(): number {
    return this.data?.out_of_range_count ?? (this.data?.tests?.filter((t: any) => t.is_out_of_range)?.length ?? 0);
  }

  get summary(): string {
    return (
      this.data?.summary ||
      `Laboratory report contains ${this.totalTests} test parameters across 3 pages. ` +
      `${this.outOfRangeCount} test result(s) are outside explicitly stated biological reference ranges.`
    );
  }

  get disclaimer(): string {
    return (
      this.data?.disclaimer ||
      'Important: Values outside the stated reference ranges are reported strictly as extracted ' +
      'from the laboratory document. This information is for clinical tracking only and does NOT constitute ' +
      'a medical diagnosis or clinical conclusion. Please consult a licensed physician.'
    );
  }

  onSelectAction(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
