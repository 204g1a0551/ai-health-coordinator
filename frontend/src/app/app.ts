import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { ChatComponent } from './components/chat/chat.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, DashboardComponent, ChatComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  readonly title = 'AI Health Checkup & Appointment Coordinator';
}
