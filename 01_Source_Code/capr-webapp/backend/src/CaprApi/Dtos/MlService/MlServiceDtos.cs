using System.Text.Json.Serialization;

namespace CaprApi.Dtos.MlService;

public class MlFlowFeatures
{
    [JsonPropertyName("flow_id")] public string? FlowId { get; set; }
    [JsonPropertyName("features")] public List<double> Features { get; set; } = new();
}

public class MlPredictRequest
{
    [JsonPropertyName("dataset")] public string Dataset { get; set; } = "";
    [JsonPropertyName("flows")] public List<MlFlowFeatures> Flows { get; set; } = new();
    [JsonPropertyName("threshold")] public double? Threshold { get; set; }
    [JsonPropertyName("mc_uncertainty")] public bool McUncertainty { get; set; } = true;
}

public class MlPredictionResult
{
    [JsonPropertyName("flow_id")] public string? FlowId { get; set; }
    [JsonPropertyName("anomaly_probability")] public double AnomalyProbability { get; set; }
    [JsonPropertyName("uncertainty")] public double? Uncertainty { get; set; }
    [JsonPropertyName("is_anomaly")] public bool IsAnomaly { get; set; }
    [JsonPropertyName("threshold")] public double Threshold { get; set; }
    [JsonPropertyName("coverage")] public double? Coverage { get; set; }
    [JsonPropertyName("src_ip")] public string? SrcIp { get; set; }
    [JsonPropertyName("dst_ip")] public string? DstIp { get; set; }
    [JsonPropertyName("src_port")] public int? SrcPort { get; set; }
    [JsonPropertyName("dst_port")] public int? DstPort { get; set; }
    [JsonPropertyName("features")] public List<double>? Features { get; set; }
}

public class MlPredictResponse
{
    [JsonPropertyName("dataset")] public string Dataset { get; set; } = "";
    [JsonPropertyName("model_version")] public string ModelVersion { get; set; } = "";
    [JsonPropertyName("results")] public List<MlPredictionResult> Results { get; set; } = new();
    [JsonPropertyName("inference_ms_total")] public double InferenceMsTotal { get; set; }
    [JsonPropertyName("note")] public string? Note { get; set; }
}

public class MlExplainRequest
{
    [JsonPropertyName("dataset")] public string Dataset { get; set; } = "";
    [JsonPropertyName("features")] public List<double> Features { get; set; } = new();
    [JsonPropertyName("top_k")] public int TopK { get; set; } = 8;
}

public class MlFeatureContribution
{
    [JsonPropertyName("feature")] public string Feature { get; set; } = "";
    [JsonPropertyName("value")] public double Value { get; set; }
    [JsonPropertyName("shap")] public double Shap { get; set; }
}

public class MlExplainResponse
{
    [JsonPropertyName("dataset")] public string Dataset { get; set; } = "";
    [JsonPropertyName("anomaly_probability")] public double AnomalyProbability { get; set; }
    [JsonPropertyName("base_value")] public double BaseValue { get; set; }
    [JsonPropertyName("top_features")] public List<MlFeatureContribution> TopFeatures { get; set; } = new();
}

public class MlModelInfo
{
    [JsonPropertyName("dataset")] public string Dataset { get; set; } = "";
    [JsonPropertyName("method")] public string Method { get; set; } = "";
    [JsonPropertyName("label_ratio")] public double LabelRatio { get; set; }
    [JsonPropertyName("n_features")] public int NFeatures { get; set; }
    [JsonPropertyName("features")] public List<string> Features { get; set; } = new();
    [JsonPropertyName("test_f1")] public double? TestF1 { get; set; }
    [JsonPropertyName("test_auc_pr")] public double? TestAucPr { get; set; }
    [JsonPropertyName("test_auc_roc")] public double? TestAucRoc { get; set; }
    [JsonPropertyName("test_fpr")] public double? TestFpr { get; set; }
    [JsonPropertyName("ensemble_size")] public int EnsembleSize { get; set; }
    [JsonPropertyName("variant")] public string? Variant { get; set; }
    [JsonPropertyName("test_accuracy")] public double? TestAccuracy { get; set; }
    [JsonPropertyName("test_precision")] public double? TestPrecision { get; set; }
    [JsonPropertyName("test_recall")] public double? TestRecall { get; set; }
}

public class MlHealthResponse
{
    [JsonPropertyName("status")] public string Status { get; set; } = "";
    [JsonPropertyName("datasets_loaded")] public List<string> DatasetsLoaded { get; set; } = new();
}
