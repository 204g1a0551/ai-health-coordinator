import { Component, input } from '@angular/core';

@Component({
  selector: 'app-medical-expenses-card',
  standalone: true,
  template: `<div class="expense-card"><h3>🧾 Medical Expenses</h3><strong>₹{{ data()?.total || 0 }}</strong></div>`,
  styles: [`.expense-card { padding: 1rem; border-radius: 12px; background: #fff7ed; }`],
})
export class MedicalExpensesCardComponent {
  readonly data = input<any>(null);
}
