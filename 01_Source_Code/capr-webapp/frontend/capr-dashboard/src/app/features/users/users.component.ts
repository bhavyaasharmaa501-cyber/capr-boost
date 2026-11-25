import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { UserDto, UserRole } from '../../core/models/auth.models';
import { UsersService } from '../../core/services/users.service';

const ROLES: UserRole[] = ['Admin', 'Analyst', 'Viewer'];

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    DatePipe,
    MatCardModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './users.component.html',
  styleUrl: './users.component.scss',
})
export class UsersComponent implements OnInit {
  private readonly usersService = inject(UsersService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);

  readonly roles = ROLES;
  readonly users = signal<UserDto[]>([]);
  readonly loading = signal(true);
  readonly creating = signal(false);
  readonly hidePassword = signal(true);

  readonly columns = ['email', 'displayName', 'role', 'status', 'createdAt', 'lastLogin'];

  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    displayName: ['', [Validators.required]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    role: ['Analyst' as UserRole, [Validators.required]],
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.usersService.getAll().subscribe({
      next: (rows) => {
        this.users.set(rows);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  submit(): void {
    if (this.form.invalid || this.creating()) return;
    this.creating.set(true);

    this.usersService.create(this.form.getRawValue()).subscribe({
      next: (user) => {
        this.creating.set(false);
        this.users.update((rows) => [user, ...rows]);
        this.form.reset({ email: '', displayName: '', password: '', role: 'Analyst' });
        this.snackBar.open(`${user.email} created`, 'Dismiss', { duration: 5000 });
      },
      error: (err: { error?: { detail?: string } }) => {
        this.creating.set(false);
        this.snackBar.open(err?.error?.detail ?? 'Could not create user', 'Dismiss', { duration: 8000 });
      },
    });
  }
}
