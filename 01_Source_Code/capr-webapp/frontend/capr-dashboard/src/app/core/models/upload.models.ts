export type UploadStatus = 'Pending' | 'Extracting' | 'Predicting' | 'Completed' | 'Failed';

export interface UploadSummaryDto {
  pcapUploadId: number;
  originalFileName: string;
  fileSizeBytes: number;
  status: UploadStatus;
  errorMessage: string | null;
  modelVersionId: number | null;
  flowCount: number | null;
  anomalyCount: number | null;
  uploadedAtUtc: string;
  completedAtUtc: string | null;
}

export interface UploadNotification {
  pcapUploadId: number;
  originalFileName: string;
  status: UploadStatus;
  flowCount: number | null;
  anomalyCount: number | null;
  note: string | null;
}
