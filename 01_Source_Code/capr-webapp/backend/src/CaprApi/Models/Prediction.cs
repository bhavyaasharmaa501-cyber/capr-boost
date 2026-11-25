namespace CaprApi.Models;

public class Prediction
{
    public long PredictionId { get; set; }
    public long FlowId { get; set; }
    public int ModelVersionId { get; set; }
    public double AnomalyProbability { get; set; }
    public double? Uncertainty { get; set; }
    public bool IsAnomaly { get; set; }
    public double Threshold { get; set; } = 0.5;
    public string? TopFeaturesJson { get; set; }
    public DateTime ScoredAtUtc { get; set; }
    public double? InferenceMs { get; set; }
}
