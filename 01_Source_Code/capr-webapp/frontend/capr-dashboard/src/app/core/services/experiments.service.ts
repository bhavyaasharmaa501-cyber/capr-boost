import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ExperimentAggregateDto, ExperimentRunDto, ImportExperimentsResult } from '../models/experiment.models';

@Injectable({ providedIn: 'root' })
export class ExperimentsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/experiments`;

  getAll(dataset?: string): Observable<ExperimentRunDto[]> {
    return this.http.get<ExperimentRunDto[]>(this.base, { params: dataset ? { dataset } : {} });
  }

  getAggregates(dataset?: string): Observable<ExperimentAggregateDto[]> {
    return this.http.get<ExperimentAggregateDto[]>(`${this.base}/aggregate`, {
      params: dataset ? { dataset } : {},
    });
  }

  import(file: File): Observable<ImportExperimentsResult> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<ImportExperimentsResult>(`${this.base}/import`, form);
  }
}
