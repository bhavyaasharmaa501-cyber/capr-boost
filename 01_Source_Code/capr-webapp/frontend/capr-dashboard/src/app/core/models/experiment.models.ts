export interface ExperimentRunDto {
  experimentRunId: number;
  datasetName: string;
  methodName: string;
  labelRatio: number;
  noiseRate: number;
  seed: number;
  accuracy: number | null;
  f1: number;
  aucRoc: number;
  aucPr: number;
  precision: number;
  recall: number;
  fpr: number;
  mcc: number | null;
  fitTimeSeconds: number | null;
}

export interface ExperimentAggregateDto {
  datasetName: string;
  methodName: string;
  labelRatio: number;
  noiseRate: number;
  numSeeds: number;
  accuracyMean: number | null;
  accuracyStd: number | null;
  f1Mean: number;
  f1Std: number | null;
  aucPrMean: number;
  aucPrStd: number | null;
  aucRocMean: number;
  fprMean: number;
}

export interface ImportExperimentsResult {
  rowsRead: number;
  rowsInserted: number;
  rowsSkippedAsDuplicate: number;
}
