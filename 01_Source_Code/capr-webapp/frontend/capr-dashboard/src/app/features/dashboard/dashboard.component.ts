import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { DashboardSummaryDto } from '../../core/models/dashboard.models';
import { DashboardService } from '../../core/services/dashboard.service';
import { ModelVersionDto } from '../../core/models/model.models';
import { ModelsService } from '../../core/services/models.service';
import { SignalrService } from '../../core/services/signalr.service';
import { SeverityBadgeComponent } from '../../shared/severity-badge/severity-badge.component';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    RouterLink,
    DatePipe,
    DecimalPipe,
    MatCardModule,
    MatIconModule,
    MatListModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    SeverityBadgeComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  private readonly dashboardService = inject(DashboardService);
  private readonly signalr = inject(SignalrService);
  private readonly modelsService = inject(ModelsService);

  readonly models = signal<ModelVersionDto[]>([]);

  readonly summary = signal<DashboardSummaryDto | null>(null);
  readonly loading = signal(true);

  readonly severityOrder = ['Critical', 'High', 'Medium', 'Low'];

  ngOnInit(): void {
    this.load();
    this.modelsService.getAll().subscribe({ next: (m) => this.models.set(m.filter((x) => x.isActive)) });
    this.signalr.newAlert$.subscribe(() => this.load());
    this.signalr.uploadCompleted$.subscribe(() => this.load());
  }

  load(): void {
    this.dashboardService.getSummary().subscribe({
      next: (s) => {
        this.summary.set(s);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  pct(v: number | null): string {
    return v === null ? '—' : `${(v * 100).toFixed(2)}%`;
  }

  severityCount(s: DashboardSummaryDto, severity: string): number {
    return s.alertsBySeverity[severity] ?? 0;
  }
}
