import { AlertDto } from './alert.models';
import { UploadSummaryDto } from './upload.models';

export interface DashboardSummaryDto {
  totalUploads: number;
  totalFlows: number;
  totalAnomalies: number;
  openAlerts: number;
  alertsBySeverity: Record<string, number>;
  activeModelCount: number;
  recentAlerts: AlertDto[];
  recentUploads: UploadSummaryDto[];
}
