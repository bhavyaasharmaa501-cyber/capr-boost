export type AlertSeverity = 'Low' | 'Medium' | 'High' | 'Critical';
export type AlertStatus = 'Open' | 'Acknowledged' | 'Resolved' | 'FalsePositive';

export interface AlertDto {
  alertId: number;
  predictionId: number;
  severity: AlertSeverity;
  title: string;
  description: string | null;
  status: AlertStatus;
  acknowledgedBy: number | null;
  acknowledgedAtUtc: string | null;
  createdAtUtc: string;
  anomalyProbability: number;
  srcIp: string | null;
  dstIp: string | null;
  srcPort: number | null;
  dstPort: number | null;
}

export interface AcknowledgeAlertRequest {
  status: 'Acknowledged' | 'Resolved' | 'FalsePositive';
}
