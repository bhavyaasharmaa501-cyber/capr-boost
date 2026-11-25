export interface ModelVersionDto {
  modelVersionId: number;
  datasetName: string;
  methodName: string;
  labelRatio: number;
  nFeatures: number;
  testAccuracy: number | null;
  testPrecision: number | null;
  testRecall: number | null;
  testF1: number | null;
  testAucPr: number | null;
  testAucRoc: number | null;
  testFpr: number | null;
  ensembleSize: number;
  isActive: boolean;
  registeredAtUtc: string;
}
