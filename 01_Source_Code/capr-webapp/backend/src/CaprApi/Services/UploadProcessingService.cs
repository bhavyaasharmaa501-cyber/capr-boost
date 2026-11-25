using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.SignalR;
using CaprApi.Data.Repositories;
using CaprApi.Dtos;
using CaprApi.Dtos.MlService;
using CaprApi.Hubs;
using CaprApi.Models;

namespace CaprApi.Services;

public enum UploadKind { Pcap, Csv }

public class UploadProcessingService
{
    private readonly IPcapUploadRepository _uploads;
    private readonly IFlowRepository _flows;
    private readonly IPredictionRepository _predictions;
    private readonly IModelVersionRepository _modelVersions;
    private readonly AlertRulesService _alertRules;
    private readonly ModelSyncService _modelSync;
    private readonly MlServiceClient _ml;
    private readonly IHubContext<AlertsHub, IAlertsClient> _hub;
    private readonly IWebHostEnvironment _env;
    private readonly IConfiguration _config;
    private readonly ILogger<UploadProcessingService> _log;

    public UploadProcessingService(
        IPcapUploadRepository uploads, IFlowRepository flows, IPredictionRepository predictions,
        IModelVersionRepository modelVersions, AlertRulesService alertRules, ModelSyncService modelSync,
        MlServiceClient ml, IHubContext<AlertsHub, IAlertsClient> hub, IWebHostEnvironment env,
        IConfiguration config, ILogger<UploadProcessingService> log)
    {
        _uploads = uploads;
        _flows = flows;
        _predictions = predictions;
        _modelVersions = modelVersions;
        _alertRules = alertRules;
        _modelSync = modelSync;
        _ml = ml;
        _hub = hub;
        _env = env;
        _config = config;
        _log = log;
    }

    public async Task<PcapUpload> ProcessAsync(
        int userId, string datasetName, UploadKind kind, Stream fileStream,
        string originalFileName, long fileSizeBytes, CancellationToken ct = default)
    {
        var modelVersion = await _modelVersions.GetActiveByDatasetAsync(datasetName, ct);
        if (modelVersion is null)
        {
            await _modelSync.SyncAsync(ct);
            modelVersion = await _modelVersions.GetActiveByDatasetAsync(datasetName, ct);
        }
        if (modelVersion is null)
            throw new InvalidOperationException(
                $"No active model registered for dataset '{datasetName}', and the ml-service's " +
                "GET /models doesn't list it either. Copy train_final.py's output into " +
                "ml-service/artifacts/<dataset>/ and reload it first.");

        var storedPath = await SaveToDiskAsync(fileStream, originalFileName, ct);
        var upload = new PcapUpload
        {
            UserId = userId, OriginalFileName = originalFileName, StoredPath = storedPath,
            FileSizeBytes = fileSizeBytes, Status = UploadStatus.Pending,
            UploadedAtUtc = DateTime.UtcNow,
            ModelVersionId = modelVersion.ModelVersionId,
        };
        upload.PcapUploadId = await _uploads.CreateAsync(upload, ct);

        try
        {
            await _uploads.SetStatusAsync(upload.PcapUploadId, UploadStatus.Extracting, ct);
            MlPredictResponse mlResponse;
            await using (var readStream = File.OpenRead(storedPath))
            {
                mlResponse = kind == UploadKind.Pcap
                    ? await _ml.PredictPcapAsync(datasetName, readStream, originalFileName, mcUncertainty: true, ct: ct)
                    : await _ml.PredictCsvAsync(datasetName, readStream, originalFileName, mcUncertainty: true, ct: ct);
            }

            await _uploads.SetStatusAsync(upload.PcapUploadId, UploadStatus.Predicting, ct);
            var (flowCount, anomalyCount) = await PersistResultsAsync(
                upload.PcapUploadId, modelVersion.ModelVersionId, datasetName, mlResponse, ct);

            await _uploads.CompleteAsync(upload.PcapUploadId, flowCount, anomalyCount, ct);
            upload.Status = UploadStatus.Completed;
            upload.FlowCount = flowCount;
            upload.AnomalyCount = anomalyCount;
            upload.CompletedAtUtc = DateTime.UtcNow;

            await _hub.Clients.All.UploadCompleted(new UploadNotification(
                upload.PcapUploadId, originalFileName, upload.Status, flowCount, anomalyCount, mlResponse.Note));
            return upload;
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Processing upload {UploadId} ({FileName}) failed",
                upload.PcapUploadId, originalFileName);
            await _uploads.FailAsync(upload.PcapUploadId, ex.Message, ct);
            upload.Status = UploadStatus.Failed;
            upload.ErrorMessage = ex.Message;
            throw;
        }
    }

    private async Task<(int FlowCount, int AnomalyCount)> PersistResultsAsync(
        int uploadId, int modelVersionId, string datasetName, MlPredictResponse resp, CancellationToken ct)
    {
        var autoExplain = _config.GetValue("Explainability:AutoExplainAnomalies", true);
        var maxExplain = _config.GetValue("Explainability:MaxPerUpload", 50);
        var perFlowMs = resp.Results.Count > 0 ? resp.InferenceMsTotal / resp.Results.Count : (double?)null;
        int anomalyCount = 0, explained = 0;

        foreach (var r in resp.Results)
        {
            var flow = new FlowRecord
            {
                PcapUploadId = uploadId, SrcIp = r.SrcIp, DstIp = r.DstIp,
                SrcPort = r.SrcPort, DstPort = r.DstPort,
                FeaturesJson = JsonSerializer.Serialize(r.Features ?? new List<double>()),
            };
            flow.FlowId = await _flows.CreateAsync(flow, ct);

            var pred = new Prediction
            {
                FlowId = flow.FlowId, ModelVersionId = modelVersionId,
                AnomalyProbability = r.AnomalyProbability, Uncertainty = r.Uncertainty,
                IsAnomaly = r.IsAnomaly, Threshold = r.Threshold, InferenceMs = perFlowMs,
            };
            pred.PredictionId = await _predictions.CreateAsync(pred, ct);

            if (!r.IsAnomaly)
                continue;
            anomalyCount++;

            if (autoExplain && explained < maxExplain && r.Features is { Count: > 0 })
            {
                explained++;
                try
                {
                    var explain = await _ml.ExplainAsync(new MlExplainRequest
                    {
                        Dataset = datasetName, Features = r.Features, TopK = 8,
                    }, ct);
                    var topFeatures = explain.TopFeatures
                        .Select(f => new FeatureContributionDto(f.Feature, f.Value, f.Shap))
                        .ToList();
                    await _predictions.SetTopFeaturesAsync(
                        pred.PredictionId, JsonSerializer.Serialize(topFeatures), ct);
                }
                catch (Exception ex)
                {
                    _log.LogWarning(ex,
                        "Explain call failed for prediction {PredictionId}; the alert is still " +
                        "raised, just without SHAP top-features", pred.PredictionId);
                }
            }

            var alert = await _alertRules.CreateForPredictionAsync(
                pred.PredictionId, r.AnomalyProbability, r.Uncertainty,
                r.SrcIp, r.DstIp, r.SrcPort, r.DstPort, ct);
            await _hub.Clients.All.NewAlert(new AlertDto(
                alert.AlertId, alert.PredictionId, alert.Severity, alert.Title, alert.Description,
                alert.Status, alert.AcknowledgedBy, alert.AcknowledgedAtUtc, alert.CreatedAtUtc,
                r.AnomalyProbability, r.SrcIp, r.DstIp, r.SrcPort, r.DstPort));
        }

        return (resp.Results.Count, anomalyCount);
    }

    private async Task<string> SaveToDiskAsync(Stream source, string originalFileName, CancellationToken ct)
    {
        var uploadsRoot = Path.Combine(_env.ContentRootPath, _config["Storage:UploadsPath"] ?? "App_Data/uploads");
        Directory.CreateDirectory(uploadsRoot);
        var safeName = Path.GetFileName(originalFileName);
        var storedName = $"{Guid.NewGuid():N}_{safeName}";
        var fullPath = Path.Combine(uploadsRoot, storedName);
        await using var dest = File.Create(fullPath);
        await source.CopyToAsync(dest, ct);
        return fullPath;
    }
}
