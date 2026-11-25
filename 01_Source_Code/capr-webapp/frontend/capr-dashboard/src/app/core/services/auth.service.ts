import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  ChangePasswordRequest,
  ForgotPasswordResponse,
  LoginRequest,
  LoginResponse,
  MessageResponse,
  ResetPasswordRequest,
  UserSummary,
} from '../models/auth.models';

const STORAGE_KEY = 'capr.auth';

interface StoredAuth {
  token: string;
  expiresAtUtc: string;
  user: UserSummary;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly stored = signal<StoredAuth | null>(this.readStorage());

  readonly user = computed(() => this.stored()?.user ?? null);
  readonly token = computed(() => this.stored()?.token ?? null);
  readonly isAuthenticated = computed(() => {
    const s = this.stored();
    return !!s && new Date(s.expiresAtUtc).getTime() > Date.now();
  });

  login(request: LoginRequest): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(`${environment.apiBaseUrl}/auth/login`, request)
      .pipe(tap((res) => this.setSession(res)));
  }

  forgotPassword(email: string): Observable<ForgotPasswordResponse> {
    return this.http.post<ForgotPasswordResponse>(`${environment.apiBaseUrl}/auth/forgot-password`, { email });
  }

  resetPassword(request: ResetPasswordRequest): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${environment.apiBaseUrl}/auth/reset-password`, request);
  }

  changePassword(request: ChangePasswordRequest): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${environment.apiBaseUrl}/auth/change-password`, request);
  }

  logout(): void {
    localStorage.removeItem(STORAGE_KEY);
    this.stored.set(null);
    void this.router.navigateByUrl('/login');
  }

  hasRole(...roles: string[]): boolean {
    const u = this.user();
    return !!u && roles.includes(u.role);
  }

  private setSession(res: LoginResponse): void {
    const value: StoredAuth = { token: res.token, expiresAtUtc: res.expiresAtUtc, user: res.user };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    this.stored.set(value);
  }

  private readStorage(): StoredAuth | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as StoredAuth) : null;
    } catch {
      return null;
    }
  }
}
