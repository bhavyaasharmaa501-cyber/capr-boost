import { HttpErrorResponse, HttpInterceptorFn, HttpRequest, HttpResponse } from '@angular/common/http';
import { Observable, delay, map, of, shareReplay, switchMap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AlertDto, AlertSeverity, AlertStatus } from '../models/alert.models';
import { UserDto } from '../models/auth.models';
import { ExperimentAggregateDto, ExperimentRunDto } from '../models/experiment.models';
import { ModelVersionDto } from '../models/model.models';
import { PredictionDto } from '../models/prediction.models';
import { UploadSummaryDto } from '../models/upload.models';

interface DemoData {
  runs: ExperimentRunDto[];
  aggregates: ExperimentAggregateDto[];
  models: ModelVersionDto[];
  features: Record<string, { feature: string; importance: number }[]>;
}

const RESET_CODE = '482913';
const API = environment.apiBaseUrl;

let data$: Observable<DemoData> | null = null;

function rng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function ip(r: () => number, internal: boolean): string {
  const o = () => Math.floor(r() * 254) + 1;
  return internal ? `192.168.${o()}.${o()}` : `${o()}.${o()}.${o()}.${o()}`;
}

const now = Date.now();
const iso = (minutesAgo: number) => new Date(now - minutesAgo * 60000).toISOString();

const uploads: UploadSummaryDto[] = [
  {
    pcapUploadId: 2,
    originalFileName: 'ids2018_test_sample.csv',
    fileSizeBytes: 622_480,
    status: 'Completed',
    errorMessage: null,
    modelVersionId: 2,
    flowCount: 1000,
    anomalyCount: 214,
    uploadedAtUtc: iso(95),
    completedAtUtc: iso(94),
  },
  {
    pcapUploadId: 1,
    originalFileName: 'darknet2020_test_sample.csv',
    fileSizeBytes: 751_903,
    status: 'Completed',
    errorMessage: null,
    modelVersionId: 1,
    flowCount: 1000,
    anomalyCount: 173,
    uploadedAtUtc: iso(180),
    completedAtUtc: iso(178),
  },
];

const predictionCache = new Map<number, PredictionDto[]>();

function predictionsFor(upload: UploadSummaryDto, d: DemoData): PredictionDto[] {
  const cached = predictionCache.get(upload.pcapUploadId);
  if (cached) return cached;
  const ds = upload.modelVersionId === 2 ? 'ids2018' : 'darknet2020';
  const feats = d.features[ds] ?? [];
  const r = rng(upload.pcapUploadId * 7919);
  const total = upload.flowCount ?? 0;
  const anomalies = upload.anomalyCount ?? 0;
  const step = Math.max(1, Math.floor(total / Math.max(1, anomalies)));
  const list: PredictionDto[] = [];
  let flagged = 0;
  for (let i = 0; i < total; i++) {
    const isAnomaly = i % step === 0 && flagged < anomalies;
    if (isAnomaly) flagged++;
    const p = isAnomaly ? 0.55 + r() * 0.45 : r() * 0.4;
    list.push({
      predictionId: upload.pcapUploadId * 100000 + i + 1,
      flowId: upload.pcapUploadId * 100000 + i + 1,
      pcapUploadId: upload.pcapUploadId,
      srcIp: ip(r, true),
      dstIp: ip(r, false),
      srcPort: 1024 + Math.floor(r() * 60000),
      dstPort: [443, 80, 53, 22, 8080, 9001, 1194][Math.floor(r() * 7)],
      anomalyProbability: +p.toFixed(4),
      uncertainty: +(r() * 0.08).toFixed(4),
      isAnomaly,
      threshold: 0.5,
      scoredAtUtc: upload.completedAtUtc ?? upload.uploadedAtUtc,
      inferenceMs: +(0.02 + r() * 0.02).toFixed(4),
      topFeatures: isAnomaly
        ? feats.slice(0, 5).map((f) => ({
            feature: f.feature,
            value: +(r() * 1000).toFixed(2),
            shap: +(f.importance * (0.6 + r() * 0.8)).toFixed(4),
          }))
        : null,
    });
  }
  predictionCache.set(upload.pcapUploadId, list);
  return list;
}

let alerts: AlertDto[] | null = null;

function buildAlerts(d: DemoData): AlertDto[] {
  if (alerts) return alerts;
  const sev = (p: number): AlertSeverity => (p > 0.95 ? 'Critical' : p > 0.85 ? 'High' : p > 0.7 ? 'Medium' : 'Low');
  const statuses: AlertStatus[] = ['Open', 'Open', 'Open', 'Acknowledged', 'Resolved', 'FalsePositive'];
  const out: AlertDto[] = [];
  let id = 1;
  for (const u of uploads) {
    predictionsFor(u, d)
      .filter((p) => p.isAnomaly)
      .slice(0, 20)
      .forEach((p, i) => {
        const s = sev(p.anomalyProbability);
        out.push({
          alertId: id++,
          predictionId: p.predictionId,
          severity: s,
          title: `${s} anomaly on port ${p.dstPort}`,
          description: `Encrypted flow ${p.srcIp} -> ${p.dstIp} scored ${(p.anomalyProbability * 100).toFixed(1)}% by CAPR-Boost`,
          status: statuses[i % statuses.length],
          acknowledgedBy: null,
          acknowledgedAtUtc: null,
          createdAtUtc: u.completedAtUtc ?? u.uploadedAtUtc,
          anomalyProbability: p.anomalyProbability,
          srcIp: p.srcIp,
          dstIp: p.dstIp,
          srcPort: p.srcPort,
          dstPort: p.dstPort,
        });
      });
  }
  alerts = out.sort((a, b) => b.anomalyProbability - a.anomalyProbability);
  return alerts;
}

const users: UserDto[] = [
  { userId: 1, email: 'admin@capr.local', displayName: 'Administrator', role: 'Admin', isActive: true, createdAtUtc: iso(60 * 24 * 10), lastLoginUtc: iso(5) },
  { userId: 2, email: 'analyst@capr.local', displayName: 'SOC Analyst', role: 'Analyst', isActive: true, createdAtUtc: iso(60 * 24 * 8), lastLoginUtc: iso(300) },
  { userId: 3, email: 'viewer@capr.local', displayName: 'Guest Viewer', role: 'Viewer', isActive: true, createdAtUtc: iso(60 * 24 * 3), lastLoginUtc: null },
];

function ok<T>(body: T): Observable<HttpResponse<T>> {
  return of(new HttpResponse({ status: 200, body })).pipe(delay(150));
}

function fail(status: number, message: string): Observable<never> {
  return throwError(() => new HttpErrorResponse({ status, error: { message, detail: message, title: message } }));
}

function handle(req: HttpRequest<unknown>, d: DemoData): Observable<HttpResponse<unknown>> {
  const path = req.url.substring(API.length).split('?')[0];
  const q = (k: string) => req.params.get(k);
  const body = (req.body ?? {}) as Record<string, string>;
  const m = req.method;

  if (m === 'POST' && path === '/auth/login') {
    const email = (body['email'] || 'admin@capr.local').toLowerCase();
    const u = users.find((x) => x.email === email) ?? users[0];
    return ok({
      token: 'demo-token',
      expiresAtUtc: new Date(now + 12 * 3600000).toISOString(),
      user: { userId: u.userId, email: u.email, displayName: u.displayName, role: u.role },
    });
  }
  if (m === 'POST' && path === '/auth/forgot-password') {
    return ok({ message: 'A reset code has been generated.', emailSent: false, demoCode: RESET_CODE, expiresInMinutes: 15 });
  }
  if (m === 'POST' && path === '/auth/reset-password') {
    return body['code'] === RESET_CODE
      ? ok({ message: 'Password has been reset. Please sign in.' })
      : fail(400, 'Invalid or expired code.');
  }
  if (m === 'POST' && path === '/auth/change-password') return ok({ message: 'Password changed.' });

  if (path === '/dashboard/summary') {
    const a = buildAlerts(d);
    const bySev: Record<string, number> = {};
    a.filter((x) => x.status === 'Open').forEach((x) => (bySev[x.severity] = (bySev[x.severity] ?? 0) + 1));
    return ok({
      totalUploads: uploads.length,
      totalFlows: uploads.reduce((s, u) => s + (u.flowCount ?? 0), 0),
      totalAnomalies: uploads.reduce((s, u) => s + (u.anomalyCount ?? 0), 0),
      openAlerts: a.filter((x) => x.status === 'Open').length,
      alertsBySeverity: bySev,
      activeModelCount: d.models.filter((x) => x.isActive).length,
      recentAlerts: a.slice(0, 8),
      recentUploads: uploads.slice(0, 5),
    });
  }

  if (path === '/alerts' && m === 'GET') {
    const status = q('status');
    return ok(buildAlerts(d).filter((x) => !status || x.status === status));
  }
  const alertMatch = path.match(/^\/alerts\/(\d+)\/status$/);
  if (alertMatch && m === 'PATCH') {
    const a = buildAlerts(d).find((x) => x.alertId === +alertMatch[1]);
    if (!a) return fail(404, 'Alert not found');
    a.status = body['status'] as AlertStatus;
    a.acknowledgedBy = 1;
    a.acknowledgedAtUtc = new Date().toISOString();
    return ok(a);
  }

  if (path === '/uploads' && m === 'GET') return ok(uploads);
  const uploadMatch = path.match(/^\/uploads\/(\d+)$/);
  if (uploadMatch) {
    const u = uploads.find((x) => x.pcapUploadId === +uploadMatch[1]);
    return u ? ok(u) : fail(404, 'Upload not found');
  }
  if (m === 'POST' && (path === '/uploads/csv' || path === '/uploads/pcap')) {
    const form = req.body as FormData;
    const file = form?.get('file') as File | null;
    const dataset = String(form?.get('dataset') ?? 'darknet2020');
    const flows = 600 + Math.floor(Math.random() * 900);
    const u: UploadSummaryDto = {
      pcapUploadId: Math.max(...uploads.map((x) => x.pcapUploadId)) + 1,
      originalFileName: file?.name ?? 'upload.csv',
      fileSizeBytes: file?.size ?? 0,
      status: 'Completed',
      errorMessage: null,
      modelVersionId: dataset.includes('ids') ? 2 : 1,
      flowCount: flows,
      anomalyCount: Math.floor(flows * (0.12 + Math.random() * 0.1)),
      uploadedAtUtc: new Date().toISOString(),
      completedAtUtc: new Date().toISOString(),
    };
    uploads.unshift(u);
    return ok(u).pipe(delay(800));
  }

  if (path === '/predictions') {
    const u = uploads.find((x) => x.pcapUploadId === +(q('uploadId') ?? 0));
    if (!u) return ok({ items: [], page: 1, pageSize: 50, totalCount: 0 });
    const page = +(q('page') ?? 1);
    const size = +(q('pageSize') ?? 50);
    let list = predictionsFor(u, d);
    if (q('anomaliesOnly') === 'true') list = list.filter((p) => p.isAnomaly);
    return ok({ items: list.slice((page - 1) * size, page * size), page, pageSize: size, totalCount: list.length });
  }
  const predMatch = path.match(/^\/predictions\/(\d+)$/);
  if (predMatch) {
    const id = +predMatch[1];
    const u = uploads.find((x) => x.pcapUploadId === Math.floor(id / 100000));
    const p = u ? predictionsFor(u, d).find((x) => x.predictionId === id) : undefined;
    return p ? ok(p) : fail(404, 'Prediction not found');
  }

  if (path === '/models' || path === '/models/sync') return ok(d.models);

  if (path === '/experiments') {
    const ds = q('dataset');
    return ok(d.runs.filter((r) => !ds || r.datasetName === ds));
  }
  if (path === '/experiments/aggregate') {
    const ds = q('dataset');
    return ok(d.aggregates.filter((r) => !ds || r.datasetName === ds));
  }
  if (path === '/experiments/import') return ok({ rowsRead: 0, rowsInserted: 0, rowsSkippedAsDuplicate: 0 });

  if (path === '/users' && m === 'GET') return ok(users);
  if (path === '/users' && m === 'POST') {
    const u: UserDto = {
      userId: users.length + 1,
      email: body['email'],
      displayName: body['displayName'],
      role: body['role'] as UserDto['role'],
      isActive: true,
      createdAtUtc: new Date().toISOString(),
      lastLoginUtc: null,
    };
    users.push(u);
    return ok(u);
  }

  return fail(404, 'Not available in demo mode');
}

export const demoInterceptor: HttpInterceptorFn = (req, next) => {
  if (!environment.demo || !req.url.startsWith(API)) return next(req);
  if (!data$) {
    data$ = next(new HttpRequest('GET', 'demo/data.json')).pipe(
      map((e) => (e instanceof HttpResponse ? (e.body as DemoData) : null)),
      switchMap((b) => (b ? of(b) : [])),
      shareReplay(1),
    );
  }
  return data$.pipe(switchMap((d) => handle(req, d)));
};
