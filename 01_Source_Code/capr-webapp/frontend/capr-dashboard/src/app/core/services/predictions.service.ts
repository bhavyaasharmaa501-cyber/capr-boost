import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { PagedResult, PredictionDto } from '../models/prediction.models';

@Injectable({ providedIn: 'root' })
export class PredictionsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/predictions`;

  getByUpload(
    uploadId: number,
    page = 1,
    pageSize = 50,
    anomaliesOnly = false,
  ): Observable<PagedResult<PredictionDto>> {
    return this.http.get<PagedResult<PredictionDto>>(this.base, {
      params: { uploadId, page, pageSize, anomaliesOnly },
    });
  }

  getById(id: number): Observable<PredictionDto> {
    return this.http.get<PredictionDto>(`${this.base}/${id}`);
  }
}
