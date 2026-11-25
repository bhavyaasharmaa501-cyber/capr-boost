namespace CaprApi.Dtos;

public record FeatureContributionDto(string Feature, double Value, double Shap);

public record PredictionDto(
    long PredictionId, long FlowId, int? PcapUploadId,
    string? SrcIp, string? DstIp, int? SrcPort, int? DstPort,
    double AnomalyProbability, double? Uncertainty, bool IsAnomaly, double Threshold,
    DateTime ScoredAtUtc, double? InferenceMs, List<FeatureContributionDto>? TopFeatures);

public record PagedResult<T>(IReadOnlyList<T> Items, int Page, int PageSize, int TotalCount);
