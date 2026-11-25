using System.Text.Json;
using CaprApi.Data.Repositories;
using CaprApi.Models;

namespace CaprApi.Services;

public class ModelSyncService
{
    private readonly MlServiceClient _ml;
    private readonly IModelVersionRepository _repo;
    private readonly ILogger<ModelSyncService> _log;

    public ModelSyncService(MlServiceClient ml, IModelVersionRepository repo, ILogger<ModelSyncService> log)
    {
        _ml = ml;
        _repo = repo;
        _log = log;
    }

    public async Task<IReadOnlyList<ModelVersion>> SyncAsync(CancellationToken ct = default)
    {
        var models = await _ml.GetModelsAsync(ct);
        var result = new List<ModelVersion>(models.Count);

        foreach (var m in models)
        {
            var mv = new ModelVersion
            {
                DatasetName = m.Dataset,
                MethodName = m.Method,
                LabelRatio = m.LabelRatio,
                ArtifactPath = $"artifacts/{m.Dataset}",
                FeatureNamesJson = JsonSerializer.Serialize(m.Features),
                TestF1 = m.TestF1,
                TestAucPr = m.TestAucPr,
                TestAucRoc = m.TestAucRoc,
                TestFpr = m.TestFpr,
                TestAccuracy = m.TestAccuracy,
                TestPrecision = m.TestPrecision,
                TestRecall = m.TestRecall,
                EnsembleSize = m.EnsembleSize,
                Notes = m.Variant is null ? null : $"variant: {m.Variant}",
            };
            var id = await _repo.UpsertActiveAsync(mv, ct);
            result.Add(await _repo.GetByIdAsync(id, ct) ?? mv);
        }

        _log.LogInformation("Model sync: {Count} dataset(s) registered from ml-service ({Names})",
            result.Count, string.Join(", ", result.Select(r => r.DatasetName)));
        return result;
    }

    public async Task TrySyncAtStartupAsync(CancellationToken ct = default)
    {
        try
        {
            await SyncAsync(ct);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex,
                "Could not sync models from the ml-service at startup (it may still be starting). " +
                "POST /api/models/sync once it's up, or it will retry on the next upload.");
        }
    }
}
