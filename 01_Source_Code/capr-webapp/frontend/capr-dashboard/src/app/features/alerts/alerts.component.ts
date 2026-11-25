import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { AlertDto, AlertStatus } from '../../core/models/alert.models';
import { AlertsService } from '../../core/services/alerts.service';
import { SignalrService } from '../../core/services/signalr.service';
import { SeverityBadgeComponent } from '../../shared/severity-badge/severity-badge.component';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';

const STATUS_FILTERS: (AlertStatus | 'All')[] = ['Open', 'Acknowledged', 'Resolved', 'FalsePositive', 'All'];

@Component({
  selector: 'app-alerts',
  standalone: true,
  imports: [
    DatePipe,
    DecimalPipe,
    MatCardModule,
    MatTableModule,
    MatChipsModule,
    MatButtonModule,
    MatMenuModule,
    MatIconModule,
    MatProgressSpinnerModule,
    SeverityBadgeComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './alerts.component.html',
  styleUrl: './alerts.component.scss',
})
export class AlertsComponent implements OnInit {
  private readonly alertsService = inject(AlertsService);
  private readonly signalr = inject(SignalrService);
  private readonly snackBar = inject(MatSnackBar);

  readonly statusFilters = STATUS_FILTERS;
  readonly activeFilter = signal<AlertStatus | 'All'>('Open');
  readonly alerts = signal<AlertDto[]>([]);
  readonly loading = signal(true);

  readonly columns = ['severity', 'title', 'endpoint', 'probability', 'status', 'createdAt', 'actions'];

  ngOnInit(): void {
    this.load();
    this.signalr.newAlert$.subscribe((alert) => {
      if (this.activeFilter() === 'Open' || this.activeFilter() === 'All') {
        this.alerts.update((rows) => [alert, ...rows]);
      }
    });
  }

  setFilter(filter: AlertStatus | 'All'): void {
    this.activeFilter.set(filter);
    this.load();
  }

  load(): void {
    this.loading.set(true);
    const status = this.activeFilter() === 'All' ? undefined : (this.activeFilter() as AlertStatus);
    this.alertsService.getRecent(status, 200).subscribe({
      next: (rows) => {
        this.alerts.set(rows);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  act(alert: AlertDto, status: 'Acknowledged' | 'Resolved' | 'FalsePositive'): void {
    this.alertsService.updateStatus(alert.alertId, { status }).subscribe({
      next: (updated) => {
        const stillMatchesFilter = this.activeFilter() === 'All' || updated.status === this.activeFilter();
        this.alerts.update((rows) =>
          stillMatchesFilter
            ? rows.map((a) => (a.alertId === updated.alertId ? updated : a))
            : rows.filter((a) => a.alertId !== updated.alertId),
        );
        this.snackBar.open(`Alert marked ${status}`, 'Dismiss', { duration: 4000 });
      },
      error: () => this.snackBar.open('Could not update alert', 'Dismiss', { duration: 4000 }),
    });
  }
}
