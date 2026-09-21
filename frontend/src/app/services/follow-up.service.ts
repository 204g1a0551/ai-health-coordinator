import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface FollowUpNotification {
  notification_id: string;
  channel: string;
  recipient: string;
  message: string;
  language: string;
  dispatched_at: string;
  status: string;
}

export interface FollowUpTask {
  task_id: string;
  patient_id: string;
  patient_name: string;
  patient_phone?: string;
  patient_language: string;
  source_type: string;
  source_id: string;
  created_at: string;
  trigger_at: string;
  status: string;
  channels: string[];
  clinical_context: any;
  follow_up_prompt_english?: string;
  follow_up_prompt_vernacular?: string;
  notifications: FollowUpNotification[];
  patient_response?: any;
}

@Injectable({
  providedIn: 'root',
})
export class FollowUpService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${environment.apiUrl}/follow-up`;

  readonly tasks = signal<FollowUpTask[]>([]);
  readonly activeNotification = signal<FollowUpTask | null>(null);
  readonly isLoading = signal<boolean>(false);

  loadTasks(patientId?: string): Observable<FollowUpTask[]> {
    this.isLoading.set(true);
    const url = patientId ? `${this.apiUrl}/tasks?patient_id=${patientId}` : `${this.apiUrl}/tasks`;
    return this.http.get<FollowUpTask[]>(url).pipe(
      tap((taskList) => {
        this.tasks.set(taskList);
        this.isLoading.set(false);
        // Find latest dispatched or pending task for demonstration
        const latestDispatched = taskList.find(
          (t) => t.status === 'DISPATCHED' && !t.patient_response
        );
        if (latestDispatched) {
          this.activeNotification.set(latestDispatched);
        }
      })
    );
  }

  triggerDay2Simulation(taskId: string): Observable<FollowUpTask> {
    this.isLoading.set(true);
    return this.http.post<FollowUpTask>(`${this.apiUrl}/trigger/${taskId}`, {}).pipe(
      tap((task) => {
        this.activeNotification.set(task);
        this.isLoading.set(false);
        this.loadTasks().subscribe();
      })
    );
  }

  submitResponse(taskId: string, responseText: string, recoveryStatus: string = 'BETTER'): Observable<FollowUpTask> {
    this.isLoading.set(true);
    return this.http.post<FollowUpTask>(`${this.apiUrl}/respond/${taskId}`, {
      task_id: taskId,
      response_text: responseText,
      recovery_status: recoveryStatus,
    }).pipe(
      tap((task) => {
        this.activeNotification.set(null);
        this.isLoading.set(false);
        this.loadTasks().subscribe();
      })
    );
  }

  dismissNotification(): void {
    this.activeNotification.set(null);
  }
}
