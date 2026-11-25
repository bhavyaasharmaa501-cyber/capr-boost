export interface FeatureContributionDto {
  feature: string;
  value: number;
  shap: number;
}

export interface PredictionDto {
  predictionId: number;
  flowId: number;
  pcapUploadId: number | null;
  srcIp: string | null;
  dstIp: string | null;
  srcPort: number | null;
  dstPort: number | null;
  anomalyProbability: number;
  uncertainty: number | null;
  isAnomaly: boolean;
  threshold: number;
  scoredAtUtc: string;
  inferenceMs: number | null;
  topFeatures: FeatureContributionDto[] | null;
}

export interface PagedResult<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalCount: number;
}
