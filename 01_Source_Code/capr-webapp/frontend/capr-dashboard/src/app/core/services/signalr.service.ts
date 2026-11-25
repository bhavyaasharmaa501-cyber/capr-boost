import { Injectable, inject } from '@angular/core';
import * as signalR from '@microsoft/signalr';
import { Subject } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AlertDto } from '../models/alert.models';
import { UploadNotification } from '../models/upload.models';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class SignalrService {
  private readonly auth = inject(AuthService);
  private connection: signalR.HubConnection | null = null;

  readonly newAlert$ = new Subject<AlertDto>();
  readonly uploadCompleted$ = new Subject<UploadNotification>();

  start(): void {
    if (this.connection || environment.demo) return;

    this.connection = new signalR.HubConnectionBuilder()
      .withUrl(environment.hubUrl, { accessTokenFactory: () => this.auth.token() ?? '' })
      .withAutomaticReconnect()
      .build();

    this.connection.on('NewAlert', (alert: AlertDto) => this.newAlert$.next(alert));
    this.connection.on('UploadCompleted', (n: UploadNotification) => this.uploadCompleted$.next(n));
    this.connection.on('UploadStatusChanged', (n: UploadNotification) => this.uploadCompleted$.next(n));

    this.connection.start().catch((err: unknown) => console.error('SignalR connection failed', err));
  }

  stop(): void {
    void this.connection?.stop();
    this.connection = null;
  }
}
