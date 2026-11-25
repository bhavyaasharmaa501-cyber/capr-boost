import { Component, OnDestroy, OnInit, computed, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatToolbarModule } from '@angular/material/toolbar';
import { AuthService } from '../../core/services/auth.service';
import { SignalrService } from '../../core/services/signalr.service';
import { ChangePasswordDialogComponent } from '../account/change-password-dialog.component';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  roles?: string[];
}

const NAV_ITEMS: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
  { path: '/uploads', label: 'Uploads', icon: 'upload_file' },
  { path: '/alerts', label: 'Alerts', icon: 'notifications_active' },
  { path: '/models', label: 'Models', icon: 'model_training' },
  { path: '/experiments', label: 'Research', icon: 'science' },
  { path: '/users', label: 'Users', icon: 'group', roles: ['Admin'] },
];

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatToolbarModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatBadgeModule,
    MatDialogModule,
  ],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
})
export class ShellComponent implements OnInit, OnDestroy {
  private readonly auth = inject(AuthService);
  private readonly signalr = inject(SignalrService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);

  readonly user = this.auth.user;
  readonly visibleNavItems = computed(() =>
    NAV_ITEMS.filter((item) => !item.roles || this.auth.hasRole(...item.roles)),
  );

  ngOnInit(): void {
    this.signalr.start();
    this.signalr.newAlert$.subscribe((alert) => {
      const ref = this.snackBar.open(`${alert.severity} alert: ${alert.title}`, 'View', { duration: 6000 });
      ref.onAction().subscribe(() => void this.router.navigateByUrl('/alerts'));
    });
  }

  ngOnDestroy(): void {
    this.signalr.stop();
  }

  changePassword(): void {
    this.dialog.open(ChangePasswordDialogComponent, { width: '420px' });
  }

  logout(): void {
    this.signalr.stop();
    this.auth.logout();
  }
}
