namespace CaprApi.Dtos;

public record ModelVersionDto(
    int ModelVersionId, string DatasetName, string MethodName, double LabelRatio,
    int NFeatures, double? TestAccuracy, double? TestPrecision, double? TestRecall,
    double? TestF1, double? TestAucPr, double? TestAucRoc, double? TestFpr,
    int EnsembleSize, bool IsActive, DateTime RegisteredAtUtc);
