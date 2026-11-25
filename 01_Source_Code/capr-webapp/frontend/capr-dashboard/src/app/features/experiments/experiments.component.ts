import { Component, ElementRef, Injector, OnInit, ViewChild, afterNextRender, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { Chart, registerables } from 'chart.js';
import { ExperimentAggregateDto } from '../../core/models/experiment.models';
import { AuthService } from '../../core/services/auth.service';
import { ExperimentsService } from '../../core/services/experiments.service';

Chart.register(...registerables);

@Component({
  selector: 'app-experiments',
  standalone: true,
  imports: [
    DecimalPipe,
    MatCardModule,
    MatTableModule,
    MatSelectModule,
    MatFormFieldModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './experiments.component.html',
  styleUrl: './experiments.component.scss',
})
export class ExperimentsComponent implements OnInit {
  private readonly experimentsService = inject(ExperimentsService);
  private readonly auth = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly injector = inject(Injector);

  @ViewChild('chartCanvas') chartCanvas?: ElementRef<HTMLCanvasElement>;
  private chart?: Chart;

  readonly isAdmin = computed(() => this.auth.hasRole('Admin'));
  readonly loading = signal(true);
  readonly importing = signal(false);
  readonly all = signal<ExperimentAggregateDto[]>([]);
  readonly selectedDataset = signal<string | null>(null);

  readonly datasets = computed(() => Array.from(new Set(this.all().map((r) => r.datasetName))).sort());
  readonly rows = computed(() => {
    const ds = this.selectedDataset();
    return ds ? this.all().filter((r) => r.datasetName === ds) : this.all();
  });

  readonly chartTitle = signal('');
  readonly columns = ['method', 'labelRatio', 'noiseRate', 'numSeeds', 'accuracy', 'f1', 'aucPr', 'aucRoc', 'fpr'];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.experimentsService.getAggregates().subscribe({
      next: (rows) => {
        this.all.set(rows);
        if (rows.length > 0 && !rows.some((r) => r.datasetName === this.selectedDataset())) {
          this.selectedDataset.set(rows[0].datasetName);
        }
        this.loading.set(false);
        if (rows.length > 0) {
          afterNextRender(() => this.renderChart(), { injector: this.injector });
        }
      },
      error: () => this.loading.set(false),
    });
  }

  setDataset(dataset: string): void {
    this.selectedDataset.set(dataset);
    this.renderChart();
  }

  onImportFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;

    this.importing.set(true);
    this.experimentsService.import(file).subscribe({
      next: (res) => {
        this.importing.set(false);
        this.snackBar.open(
          `Imported ${res.rowsInserted} new row(s), ${res.rowsSkippedAsDuplicate} duplicate(s) skipped ` +
            `(of ${res.rowsRead} read)`,
          'Dismiss',
          { duration: 8000 },
        );
        this.load();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.importing.set(false);
        this.snackBar.open(err?.error?.detail ?? 'Import failed', 'Dismiss', { duration: 8000 });
      },
    });
  }

  private renderChart(): void {
    const canvas = this.chartCanvas?.nativeElement;
    if (!canvas) return;

    const all = this.rows();
    const clean5 = all.filter((r) => Math.abs(r.noiseRate) < 1e-9 && Math.abs(r.labelRatio - 0.05) < 1e-9);
    const rows = clean5.length ? clean5 : all;
    this.chartTitle.set(clean5.length ? 'Clean labels, 5% labelled' : 'All runs');
    this.chart?.destroy();
    this.chart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: rows.map((r) => r.methodName),
        datasets: [
          { label: 'Accuracy (mean)', data: rows.map((r) => r.accuracyMean), backgroundColor: '#3949ab' },
          { label: 'F1 (mean)', data: rows.map((r) => r.f1Mean), backgroundColor: '#00897b' },
        ],
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true, max: 1 } },
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }
}
