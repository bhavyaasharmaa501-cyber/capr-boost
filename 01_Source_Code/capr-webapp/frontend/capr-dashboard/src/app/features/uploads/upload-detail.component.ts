import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { PredictionDto } from '../../core/models/prediction.models';
import { UploadSummaryDto } from '../../core/models/upload.models';
import { PredictionsService } from '../../core/services/predictions.service';
import { UploadsService } from '../../core/services/uploads.service';
import { StatusBadgeComponent } from '../../shared/status-badge/status-badge.component';

@Component({
  selector: 'app-upload-detail',
  standalone: true,
  imports: [
    RouterLink,
    DatePipe,
    DecimalPipe,
    MatCardModule,
    MatTableModule,
    MatPaginatorModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    StatusBadgeComponent,
  ],
  templateUrl: './upload-detail.component.html',
  styleUrl: './upload-detail.component.scss',
})
export class UploadDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly predictionsService = inject(PredictionsService);
  private readonly uploadsService = inject(UploadsService);

  readonly uploadId = Number(this.route.snapshot.paramMap.get('id'));
  readonly upload = signal<UploadSummaryDto | null>(null);
  readonly predictions = signal<PredictionDto[]>([]);
  readonly totalCount = signal(0);
  readonly page = signal(0);
  readonly pageSize = signal(25);
  readonly anomaliesOnly = signal(true);
  readonly loading = signal(true);
  readonly selected = signal<PredictionDto | null>(null);

  readonly columns = ['endpoint', 'probability', 'uncertainty', 'isAnomaly', 'scoredAt'];

  ngOnInit(): void {
    this.uploadsService.getById(this.uploadId).subscribe((u) => this.upload.set(u));
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.predictionsService
      .getByUpload(this.uploadId, this.page() + 1, this.pageSize(), this.anomaliesOnly())
      .subscribe({
        next: (res) => {
          this.predictions.set(res.items);
          this.totalCount.set(res.totalCount);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  onPage(event: PageEvent): void {
    this.page.set(event.pageIndex);
    this.pageSize.set(event.pageSize);
    this.load();
  }

  setAnomaliesOnly(value: boolean): void {
    this.anomaliesOnly.set(value);
    this.page.set(0);
    this.load();
  }

  select(row: PredictionDto): void {
    this.selected.set(row);
  }

  barWidth(shap: number, all: { shap: number }[]): number {
    const max = Math.max(1e-9, ...all.map((f) => Math.abs(f.shap)));
    return (Math.abs(shap) / max) * 100;
  }
}
