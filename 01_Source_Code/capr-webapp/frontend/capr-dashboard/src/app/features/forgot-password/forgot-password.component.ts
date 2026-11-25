import { Component, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../core/services/auth.service';

export const PASSWORD_PATTERN = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/;

export function matchPasswords(group: AbstractControl): ValidationErrors | null {
  const a = group.get('newPassword')?.value;
  const b = group.get('confirmPassword')?.value;
  return a && b && a !== b ? { mismatch: true } : null;
}

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './forgot-password.component.html',
  styleUrl: '../login/login.component.scss',
})
export class ForgotPasswordComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly step = signal<1 | 2 | 3>(1);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly info = signal<string | null>(null);
  readonly demoCode = signal<string | null>(null);
  readonly hidePassword = signal(true);

  readonly emailForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });

  readonly resetForm = this.fb.nonNullable.group(
    {
      code: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
      newPassword: ['', [Validators.required, Validators.pattern(PASSWORD_PATTERN)]],
      confirmPassword: ['', [Validators.required]],
    },
    { validators: matchPasswords },
  );

  requestCode(): void {
    if (this.emailForm.invalid || this.loading()) return;
    this.loading.set(true);
    this.error.set(null);
    this.auth.forgotPassword(this.emailForm.getRawValue().email).subscribe({
      next: (res) => {
        this.loading.set(false);
        this.info.set(res.emailSent
          ? `${res.message} Check your inbox. The code is valid for ${res.expiresInMinutes} minutes.`
          : `${res.message} The code is valid for ${res.expiresInMinutes} minutes.`);
        this.demoCode.set(res.demoCode);
        this.step.set(2);
      },
      error: (err: { error?: { detail?: string } }) => {
        this.loading.set(false);
        this.error.set(err?.error?.detail ?? 'Could not send the reset code. Try again.');
      },
    });
  }

  resetPassword(): void {
    if (this.resetForm.invalid || this.loading()) return;
    this.loading.set(true);
    this.error.set(null);
    const v = this.resetForm.getRawValue();
    this.auth
      .resetPassword({ email: this.emailForm.getRawValue().email, code: v.code, newPassword: v.newPassword })
      .subscribe({
        next: (res) => {
          this.loading.set(false);
          this.info.set(res.message);
          this.step.set(3);
        },
        error: (err: { error?: { detail?: string } }) => {
          this.loading.set(false);
          this.error.set(err?.error?.detail ?? 'Could not reset the password.');
        },
      });
  }

  backToLogin(): void {
    void this.router.navigateByUrl('/login');
  }
}
