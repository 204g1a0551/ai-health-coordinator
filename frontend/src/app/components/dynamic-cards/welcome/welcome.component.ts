import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-welcome',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './welcome.component.html',
  styleUrl: './welcome.component.css',
})
export class WelcomeComponent {
  @Input() data: any = null;
  @Output() promptSelected = new EventEmitter<string>();

  readonly starterPrompts = [
    'I have fever and headache for two days.',
    'Which department should I visit?',
    'Show doctors near Koramangala.',
    'Show available slots for Dr. Ravi.',
    'Show Dr. Ravi.',
    'Show my patient info.',
  ];

  selectPrompt(prompt: string): void {
    this.promptSelected.emit(prompt);
  }
}
