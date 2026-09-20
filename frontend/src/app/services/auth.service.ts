import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, catchError, map, tap, throwError } from 'rxjs';
import { LoginRequest, LoginResponse, RegisterRequest, UserProfile } from '../models/auth.model';

const TOKEN_KEY = 'hc_auth_token';
const USER_KEY = 'hc_auth_user';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  private readonly baseUrl = 'http://127.0.0.1:8000/api/auth';

  private currentUserSubject = new BehaviorSubject<UserProfile | null>(this.getStoredUser());
  public currentUser$ = this.currentUserSubject.asObservable();

  private isAuthenticatedSubject = new BehaviorSubject<boolean>(this.hasValidToken());
  public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();

  constructor() {
    // If token exists, verify in background with /me
    if (this.hasValidToken()) {
      this.fetchCurrentUser().subscribe({
        error: () => this.clearSession(),
      });
    }
  }

  public get currentUserValue(): UserProfile | null {
    return this.currentUserSubject.value;
  }

  public isAuthenticated(): boolean {
    return this.isAuthenticatedSubject.value;
  }

  public getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
  }

  private hasValidToken(): boolean {
    const token = this.getToken();
    return !!token && token.length > 10;
  }

  private getStoredUser(): UserProfile | null {
    try {
      const raw = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  public login(credentials: LoginRequest): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.baseUrl}/login`, credentials).pipe(
      tap((res) => {
        const storage = credentials.remember_me ? localStorage : sessionStorage;
        // Clean both to prevent conflicting sessions
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        sessionStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(USER_KEY);

        storage.setItem(TOKEN_KEY, res.access_token);
        storage.setItem(USER_KEY, JSON.stringify(res.user));

        this.currentUserSubject.next(res.user);
        this.isAuthenticatedSubject.next(true);
      }),
      catchError(this.handleError)
    );
  }

  public register(payload: RegisterRequest): Observable<UserProfile> {
    return this.http.post<UserProfile>(`${this.baseUrl}/register`, payload).pipe(
      catchError(this.handleError)
    );
  }

  public fetchCurrentUser(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.baseUrl}/me`).pipe(
      tap((user) => {
        this.currentUserSubject.next(user);
        this.isAuthenticatedSubject.next(true);
        const storage = localStorage.getItem(TOKEN_KEY) ? localStorage : sessionStorage;
        storage.setItem(USER_KEY, JSON.stringify(user));
      }),
      catchError(this.handleError)
    );
  }

  public logout(): void {
    this.http.post(`${this.baseUrl}/logout`, {}).subscribe({
      next: () => {},
      error: () => {},
    });
    this.clearSession();
    this.router.navigate(['/login']);
  }

  public clearSession(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);

    this.currentUserSubject.next(null);
    this.isAuthenticatedSubject.next(false);
  }

  private handleError(error: HttpErrorResponse) {
    let message = 'An unexpected healthcare system error occurred. Please try again.';
    if (error.error?.detail) {
      message = typeof error.error.detail === 'string'
        ? error.error.detail
        : JSON.stringify(error.error.detail);
    } else if (error.message) {
      message = error.message;
    }
    return throwError(() => new Error(message));
  }
}
