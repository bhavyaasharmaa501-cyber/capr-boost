import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { ModelVersionDto } from '../../core/models/model.models';
import { UploadSummaryDto } from '../../core/models/upload.models';
import { ModelsService } from '../../core/services/models.service';
import { SignalrService } from '../../core/services/signalr.service';
import { UploadsService } from '../../core/services/uploads.service';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';

@Component({
  selector: 'app-uploads',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    DatePipe,
    DecimalPipe,
    MatCardModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatTableModule,
    MatProgressBarModule,
    MatProgressSpinnerModule,
    StatusBadgeComponent,
  ],
  templateUrl: './uploads.component.html',
  styleUrl: './uploads.component.scss',
})
export class UploadsComponent implements OnInit {
  private readonly uploadsService = inject(UploadsService);
  private readonly modelsService = inject(ModelsService);
  private readonly signalr = inject(SignalrService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly fb = inject(FormBuilder);

  readonly uploads = signal<UploadSummaryDto[]>([]);
  readonly models = signal<ModelVersionDto[]>([]);
  readonly loading = signal(true);

  readonly selectedFile = signal<File | null>(null);
  readonly kind = signal<'csv' | 'pcap'>('pcap');
  readonly uploadPercent = signal<number | null>(null);

  readonly columns = ['fileName', 'dataset', 'status', 'flows', 'anomalies', 'uploadedAt'];

  readonly form = this.fb.nonNullable.group({
    dataset: ['', Validators.required],
  });

  ngOnInit(): void {
    this.loadModels();
    this.loadUploads();
    this.signalr.uploadCompleted$.subscribe(() => this.loadUploads());
  }

  loadModels(): void {
    this.modelsService.getAll().subscribe((models) => {
      this.models.set(models);
      const active = models.find((m) => m.isActive);
      if (active) this.form.patchValue({ dataset: active.datasetName });
    });
  }

  loadUploads(): void {
    this.loading.set(true);
    this.uploadsService.getRecent().subscribe({
      next: (rows) => {
        this.uploads.set(rows);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  datasetName(upload: UploadSummaryDto): string {
    if (upload.modelVersionId === null) return '—';
    return this.models().find((m) => m.modelVersionId === upload.modelVersionId)?.datasetName ?? '—';
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.selectedFile.set(file);
    if (file) {
      this.kind.set(file.name.toLowerCase().endsWith('.csv') ? 'csv' : 'pcap');
    }
  }

  submit(): void {
    const file = this.selectedFile();
    if (!file || this.form.invalid || this.uploadPercent() !== null) return;

    const dataset = this.form.getRawValue().dataset;
    this.uploadPercent.set(0);

    this.uploadsService.upload(this.kind(), dataset, file).subscribe({
      next: (progress) => {
        if (progress.stage === 'uploading') {
          this.uploadPercent.set(progress.percent);
        } else {
          this.uploadPercent.set(null);
          this.selectedFile.set(null);
          this.snackBar.open(
            `${file.name}: ${progress.result.flowCount ?? 0} flows scored, ` +
              `${progress.result.anomalyCount ?? 0} anomalies`,
            'Dismiss',
            { duration: 6000 },
          );
          this.loadUploads();
        }
      },
      error: (err: { error?: { detail?: string } }) => {
        this.uploadPercent.set(null);
        this.snackBar.open(err?.error?.detail ?? 'Upload failed', 'Dismiss', { duration: 8000 });
      },
    });
  }
}
