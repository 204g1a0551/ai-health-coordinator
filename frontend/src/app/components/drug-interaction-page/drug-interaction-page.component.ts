import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DrugInteractionService } from '../../services/drug-interaction.service';
import {
  DDIAnalysisResult,
  DrugInteractionPair,
  NormalizedMedication,
  InteractionSeverity,
} from '../../models/drug-interaction.model';

@Component({
  selector: 'app-drug-interaction-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './drug-interaction-page.component.html',
  styleUrls: ['./drug-interaction-page.component.css'],
})
export class DrugInteractionPageComponent implements OnInit {
  analysis: DDIAnalysisResult | null = null;
  loading = false;
  errorMsg = '';

  // Manual pair check inputs
  medA = '';
  medB = '';
  pairResult: DrugInteractionPair | null = null;
  checkingPair = false;

  // Q&A
  question = '';
  qaHistory: Array<{ q: string; a: string }> = [];
  qaLoading = false;

  constructor(private ddiService: DrugInteractionService) {}

  ngOnInit(): void {
    this.loadAnalysis();
  }

  loadAnalysis(): void {
    this.loading = true;
    this.ddiService.getLatestAnalysis().subscribe({
      next: (res) => {
        this.analysis = res;
        this.loading = false;
      },
      error: () => {
        this.errorMsg = 'Unable to load interaction analysis at this time.';
        this.loading = false;
      },
    });
  }

  checkSinglePair(): void {
    if (!this.medA.trim() || !this.medB.trim()) return;
    this.checkingPair = true;
    this.pairResult = null;
    this.ddiService.checkPair(this.medA.trim(), this.medB.trim()).subscribe({
      next: (res) => {
        this.pairResult = res;
        this.checkingPair = false;
      },
      error: () => {
        this.checkingPair = false;
      },
    });
  }

  askQuestion(): void {
    if (!this.question.trim()) return;
    const q = this.question.trim();
    this.question = '';
    this.qaLoading = true;
    this.ddiService.queryInteractions(q).subscribe({
      next: (res) => {
        this.qaHistory.unshift({ q, a: res.answer });
        this.qaLoading = false;
      },
      error: () => {
        this.qaHistory.unshift({
          q,
          a: 'Interaction information could not be verified from the configured source.',
        });
        this.qaLoading = false;
      },
    });
  }

  getSeverityClass(severity: InteractionSeverity | string): string {
    switch (severity) {
      case 'HIGH':
      case 'MAJOR':
        return 'sev-high';
      case 'MODERATE':
        return 'sev-mod';
      case 'MINOR':
        return 'sev-minor';
      default:
        return 'sev-unverified';
    }
  }
}
