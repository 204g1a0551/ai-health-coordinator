import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

import { LabReportsService } from '../../services/lab-reports.service';
import { LabTestResult, LabReportData } from '../../models/lab-report.model';

@Component({
  selector: 'app-lab-reports',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './lab-reports.component.html',
  styleUrl: './lab-reports.component.css',
})
export class LabReportsComponent implements OnInit {
  protected readonly labService = inject(LabReportsService);

  readonly isDragOver = signal<boolean>(false);
  readonly filterMode = signal<'all' | 'outside'>('all');
  readonly searchQuery = signal<string>('');
  readonly userQuestionInput = signal<string>('');
  readonly uploadSuccessMsg = signal<string | null>(null);

  readonly suggestedQuestions = [
    'What tests are in this report?',
    'Which values are outside the reference range?',
    'What does page 3 say?',
    'Show my latest lab report.',
  ];

  ngOnInit(): void {
    this.labService.loadLatestReport();
  }

  readonly filteredTests = computed(() => {
    const report = this.labService.activeReport();
    if (!report || !report.tests) return [];

    const mode = this.filterMode();
    const query = this.searchQuery().toLowerCase().trim();

    return report.tests.filter((t) => {
      if (mode === 'outside' && !t.is_out_of_range) {
        return false;
      }
      if (query && !t.test_name.toLowerCase().includes(query) && !(t.panel_name || '').toLowerCase().includes(query)) {
        return false;
      }
      return true;
    });
  });

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);
  }

  onFileDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFileUpload(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFileUpload(input.files[0]);
    }
  }

  handleFileUpload(file: File): void {
    this.uploadSuccessMsg.set(null);
    this.labService.uploadLabReport(file).subscribe({
      next: (report) => {
        this.uploadSuccessMsg.set(`Laboratory report "${report.file_name}" uploaded and parsed successfully!`);
      },
    });
  }

  setFilter(mode: 'all' | 'outside'): void {
    this.filterMode.set(mode);
  }

  submitQuestion(q?: string): void {
    const question = q || this.userQuestionInput().trim();
    if (!question) return;

    this.userQuestionInput.set(question);
    this.labService.askQuestion(question);
  }
}
