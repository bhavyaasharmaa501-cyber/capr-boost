namespace CaprApi.Models;

public class ExperimentRun
{
    public int ExperimentRunId { get; set; }
    public string DatasetName { get; set; } = "";
    public string MethodName { get; set; } = "";
    public double LabelRatio { get; set; }
    public double NoiseRate { get; set; }
    public int Seed { get; set; }
    public double? Accuracy { get; set; }
    public double F1 { get; set; }
    public double AucRoc { get; set; }
    public double AucPr { get; set; }
    public double Precision_ { get; set; }
    public double Recall_ { get; set; }
    public double Fpr { get; set; }
    public double? Mcc { get; set; }
    public double? FitTimeSeconds { get; set; }
    public DateTime ImportedAtUtc { get; set; }
}
