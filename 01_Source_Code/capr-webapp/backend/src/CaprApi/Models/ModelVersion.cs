namespace CaprApi.Models;

public class ModelVersion
{
    public int ModelVersionId { get; set; }
    public string DatasetName { get; set; } = "";
    public string MethodName { get; set; } = "";
    public double LabelRatio { get; set; }
    public string ArtifactPath { get; set; } = "";
    public string FeatureNamesJson { get; set; } = "[]";
    public double? TestF1 { get; set; }
    public double? TestAucPr { get; set; }
    public double? TestAucRoc { get; set; }
    public double? TestFpr { get; set; }
    public double? TestAccuracy { get; set; }
    public double? TestPrecision { get; set; }
    public double? TestRecall { get; set; }
    public int EnsembleSize { get; set; }
    public bool IsActive { get; set; }
    public DateTime RegisteredAtUtc { get; set; }
    public string? Notes { get; set; }
}
