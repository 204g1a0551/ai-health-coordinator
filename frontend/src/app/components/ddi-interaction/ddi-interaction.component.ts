import { Component, inject, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DDIService } from '../../services/ddi.service';

@Component({
  selector: 'app-ddi-interaction',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ddi-interaction.component.html',
  styleUrl: './ddi-interaction.component.css',
})
export class DDIInteractionComponent {
  readonly data = input<any>(null);
  protected readonly ddiService = inject(DDIService);

  get result(): any {
    return this.data() || this.ddiService.result();
  }

  get interactions(): any[] {
    return this.result?.interactions || [];
  }

  get medicines(): any[] {
    return this.result?.medicines || [];
  }
}
