import { HttpClient, HttpEventType, HttpRequest, HttpResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, filter, map } from 'rxjs';
import { environment } from '../../../environments/environment';
import { UploadSummaryDto } from '../models/upload.models';

@Injectable({ providedIn: 'root' })
export class UploadsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/uploads`;

  getRecent(limit = 50): Observable<UploadSummaryDto[]> {
    return this.http.get<UploadSummaryDto[]>(this.base, { params: { limit } });
  }

  getById(id: number): Observable<UploadSummaryDto> {
    return this.http.get<UploadSummaryDto>(`${this.base}/${id}`);
  }

  upload(kind: 'csv' | 'pcap', dataset: string, file: File): Observable<UploadProgress> {
    const form = new FormData();
    form.append('dataset', dataset);
    form.append('file', file);

    const req = new HttpRequest('POST', `${this.base}/${kind}`, form, { reportProgress: true });
    return this.http.request<UploadSummaryDto>(req).pipe(
      filter((event) => event.type === HttpEventType.UploadProgress || event instanceof HttpResponse),
      map((event): UploadProgress => {
        if (event instanceof HttpResponse) {
          return { stage: 'done', percent: 100, result: event.body as UploadSummaryDto };
        }
        const progress = event as { loaded: number; total?: number };
        const percent = progress.total ? Math.round((100 * progress.loaded) / progress.total) : 0;
        return { stage: 'uploading', percent };
      }),
    );
  }
}

export type UploadProgress =
  | { stage: 'uploading'; percent: number }
  | { stage: 'done'; percent: 100; result: UploadSummaryDto };
