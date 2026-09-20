import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CostSaverService } from '../../services/cost-saver.service';
import {
  CostSaverAnalysisResult,
  MedicineComparison,
  MedicinePriceItem,
} from '../../models/cost-saver.model';

@Component({
  selector: 'app-cost-saver-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cost-saver-page.component.html',
  styleUrls: ['./cost-saver-page.component.css'],
})
export class CostSaverPageComponent implements OnInit {
  analysis: CostSaverAnalysisResult | null = null;
  loading = false;
  errorMsg = '';

  // Single medicine lookup
  lookupName = '';
  lookupResult: MedicineComparison | null = null;
  lookupLoading = false;

  // Q&A
  question = '';
  qaHistory: Array<{ q: string; a: string }> = [];
  qaLoading = false;

  constructor(private costSaverService: CostSaverService) {}

  ngOnInit(): void {
    this.loadAnalysis();
  }

  loadAnalysis(): void {
    this.loading = true;
    this.costSaverService.getLatestAnalysis().subscribe({
      next: (res) => {
        this.analysis = res;
        this.loading = false;
      },
      error: () => {
        this.errorMsg = 'Unable to load generic medicine cost analysis.';
        this.loading = false;
      },
    });
  }

  lookupMedicine(): void {
    if (!this.lookupName.trim()) return;
    this.lookupLoading = true;
    this.lookupResult = null;
    this.costSaverService.checkMedicine(this.lookupName.trim()).subscribe({
      next: (res) => {
        this.lookupResult = res;
        this.lookupLoading = false;
      },
      error: () => {
        this.lookupLoading = false;
      },
    });
  }

  askQuestion(): void {
    if (!this.question.trim()) return;
    const q = this.question.trim();
    this.question = '';
    this.qaLoading = true;
    this.costSaverService.queryCostSaver(q).subscribe({
      next: (res) => {
        this.qaHistory.unshift({ q, a: res.answer });
        this.qaLoading = false;
      },
      error: () => {
        this.qaHistory.unshift({
          q,
          a: 'Equivalent product could not be reliably verified.',
        });
        this.qaLoading = false;
      },
    });
  }
}
