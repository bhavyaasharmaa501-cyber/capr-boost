namespace CaprApi.Dtos;

public record ExperimentRunDto(
    int ExperimentRunId, string DatasetName, string MethodName, double LabelRatio,
    double NoiseRate, int Seed, double? Accuracy, double F1, double AucRoc, double AucPr,
    double Precision, double Recall, double Fpr, double? Mcc, double? FitTimeSeconds)
{
    public static ExperimentRunDto From(Models.ExperimentRun r) => new(
        r.ExperimentRunId, r.DatasetName, r.MethodName, r.LabelRatio, r.NoiseRate, r.Seed,
        r.Accuracy, r.F1, r.AucRoc, r.AucPr, r.Precision_, r.Recall_, r.Fpr, r.Mcc, r.FitTimeSeconds);
}

public record ImportExperimentsResult(int RowsRead, int RowsInserted, int RowsSkippedAsDuplicate);

public record ExperimentAggregateDto(
    string DatasetName, string MethodName, double LabelRatio, double NoiseRate, int NumSeeds,
    double? AccuracyMean, double? AccuracyStd, double F1Mean, double? F1Std, double AucPrMean, double? AucPrStd, double AucRocMean, double FprMean);
