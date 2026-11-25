import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ModelVersionDto } from '../../core/models/model.models';
import { AuthService } from '../../core/services/auth.service';
import { ModelsService } from '../../core/services/models.service';

@Component({
  selector: 'app-models',
  standalone: true,
  imports: [
    DatePipe,
    DecimalPipe,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './models.component.html',
  styleUrl: './models.component.scss',
})
export class ModelsComponent implements OnInit {
  private readonly modelsService = inject(ModelsService);
  private readonly auth = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);

  readonly isAdmin = computed(() => this.auth.hasRole('Admin'));
  readonly models = signal<ModelVersionDto[]>([]);
  readonly loading = signal(true);
  readonly syncing = signal(false);

  readonly columns = [
    'dataset',
    'method',
    'labelRatio',
    'nFeatures',
    'accuracy',
    'f1',
    'aucPr',
    'aucRoc',
    'fpr',
    'ensembleSize',
    'status',
    'registeredAt',
  ];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.modelsService.getAll().subscribe({
      next: (rows) => {
        this.models.set(rows);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  sync(): void {
    this.syncing.set(true);
    this.modelsService.sync().subscribe({
      next: (rows) => {
        this.models.set(rows);
        this.syncing.set(false);
        this.snackBar.open(`Synced ${rows.length} model version(s) from the ml-service`, 'Dismiss', {
          duration: 5000,
        });
      },
      error: (err: { error?: { detail?: string } }) => {
        this.syncing.set(false);
        this.snackBar.open(err?.error?.detail ?? 'Sync failed', 'Dismiss', { duration: 8000 });
      },
    });
  }
}
