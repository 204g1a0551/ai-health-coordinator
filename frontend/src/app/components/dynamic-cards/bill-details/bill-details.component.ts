import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BillVerificationData } from '../../../models/bill-verification.model';

@Component({
  selector: 'app-bill-details',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './bill-details.component.html',
  styleUrls: ['./bill-details.component.css']
})
export class BillDetailsComponent {
  @Input() data: any = {};
  @Output() actionClicked = new EventEmitter<string>();

  get verificationData(): BillVerificationData | null {
    return this.data?.verification || this.data || null;
  }

  askAbout(prompt: string): void {
    this.actionClicked.emit(prompt);
  }
}
