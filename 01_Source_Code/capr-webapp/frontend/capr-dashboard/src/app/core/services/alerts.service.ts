import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AcknowledgeAlertRequest, AlertDto, AlertStatus } from '../models/alert.models';

@Injectable({ providedIn: 'root' })
export class AlertsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/alerts`;

  getRecent(status?: AlertStatus, limit = 100): Observable<AlertDto[]> {
    const params: Record<string, string | number> = { limit };
    if (status) params['status'] = status;
    return this.http.get<AlertDto[]>(this.base, { params });
  }

  updateStatus(id: number, request: AcknowledgeAlertRequest): Observable<AlertDto> {
    return this.http.patch<AlertDto>(`${this.base}/${id}/status`, request);
  }
}
