import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { AuthService } from '../../core/services/auth.service';
import { PASSWORD_PATTERN, matchPasswords } from '../forgot-password/forgot-password.component';

@Component({
  selector: 'app-change-password-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatButtonModule],
  template: `
    <h2 mat-dialog-title>Change password</h2>
    <form [formGroup]="form" (ngSubmit)="save()">
      <mat-dialog-content class="dialog-body">
        <mat-form-field appearance="outline">
          <mat-label>Current password</mat-label>
          <input matInput type="password" formControlName="currentPassword" autocomplete="current-password" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>New password</mat-label>
          <input matInput type="password" formControlName="newPassword" autocomplete="new-password" />
          <mat-hint>Min 8 characters, at least one letter and one digit</mat-hint>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Confirm new password</mat-label>
          <input matInput type="password" formControlName="confirmPassword" autocomplete="new-password" />
        </mat-form-field>
        @if (form.hasError('mismatch')) {
          <p class="err">Passwords do not match.</p>
        }
        @if (error()) {
          <p class="err">{{ error() }}</p>
        }
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancel</button>
        <button mat-flat-button color="primary" type="submit" [disabled]="form.invalid || saving()">Save</button>
      </mat-dialog-actions>
    </form>
  `,
  styles: [
    `.dialog-body { display: flex; flex-direction: column; gap: 6px; min-width: 340px; padding-top: 8px; }
     .err { color: #c62828; font-size: 13px; margin: 0; }`,
  ],
})
export class ChangePasswordDialogComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly ref = inject(MatDialogRef<ChangePasswordDialogComponent>);
  private readonly snack = inject(MatSnackBar);

  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group(
    {
      currentPassword: ['', Validators.required],
      newPassword: ['', [Validators.required, Validators.pattern(PASSWORD_PATTERN)]],
      confirmPassword: ['', Validators.required],
    },
    { validators: matchPasswords },
  );

  save(): void {
    if (this.form.invalid) return;
    this.saving.set(true);
    const v = this.form.getRawValue();
    this.auth.changePassword({ currentPassword: v.currentPassword, newPassword: v.newPassword }).subscribe({
      next: (res) => {
        this.saving.set(false);
        this.snack.open(res.message, 'OK', { duration: 3000 });
        this.ref.close(true);
      },
      error: (err: { error?: { detail?: string } }) => {
        this.saving.set(false);
        this.error.set(err?.error?.detail ?? 'Could not change the password.');
      },
    });
  }
}
