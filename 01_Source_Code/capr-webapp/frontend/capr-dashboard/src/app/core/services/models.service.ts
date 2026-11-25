import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ModelVersionDto } from '../models/model.models';

@Injectable({ providedIn: 'root' })
export class ModelsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiBaseUrl}/models`;

  getAll(): Observable<ModelVersionDto[]> {
    return this.http.get<ModelVersionDto[]>(this.base);
  }

  sync(): Observable<ModelVersionDto[]> {
    return this.http.post<ModelVersionDto[]>(`${this.base}/sync`, {});
  }
}
