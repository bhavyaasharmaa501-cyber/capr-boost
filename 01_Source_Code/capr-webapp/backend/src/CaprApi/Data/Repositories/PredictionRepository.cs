using Dapper;
using CaprApi.Models;

namespace CaprApi.Data.Repositories;

public class PredictionWithFlow
{
    public long PredictionId { get; set; }
    public long FlowId { get; set; }
    public int? PcapUploadId { get; set; }
    public string? SrcIp { get; set; }
    public string? DstIp { get; set; }
    public int? SrcPort { get; set; }
    public int? DstPort { get; set; }
    public double AnomalyProbability { get; set; }
    public double? Uncertainty { get; set; }
    public bool IsAnomaly { get; set; }
    public double Threshold { get; set; }
    public string? TopFeaturesJson { get; set; }
    public DateTime ScoredAtUtc { get; set; }
    public double? InferenceMs { get; set; }
}

public interface IPredictionRepository
{
    Task<PredictionWithFlow?> GetByIdAsync(long predictionId, CancellationToken ct = default);
    Task<(IReadOnlyList<PredictionWithFlow> Items, int TotalCount)> GetByUploadPagedAsync(
        int pcapUploadId, int page, int pageSize, bool anomaliesOnly, CancellationToken ct = default);
    Task<long> CreateAsync(Prediction prediction, CancellationToken ct = default);
    Task SetTopFeaturesAsync(long predictionId, string topFeaturesJson, CancellationToken ct = default);
    Task<int> CountAsync(CancellationToken ct = default);
    Task<int> CountAnomaliesAsync(CancellationToken ct = default);
}

public class PredictionRepository : IPredictionRepository
{
    private readonly IDbConnectionFactory _db;
    public PredictionRepository(IDbConnectionFactory db) => _db = db;

    private const string BaseSelect = """
        SELECT p.PredictionId, p.FlowId, f.PcapUploadId, f.SrcIp, f.DstIp, f.SrcPort, f.DstPort,
               p.AnomalyProbability, p.Uncertainty, p.IsAnomaly, p.Threshold, p.TopFeaturesJson,
               p.ScoredAtUtc, p.InferenceMs
        FROM dbo.Predictions p
        JOIN dbo.Flows f ON f.FlowId = p.FlowId
        """;

    public async Task<PredictionWithFlow?> GetByIdAsync(long predictionId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<PredictionWithFlow>(
            BaseSelect + " WHERE p.PredictionId = @predictionId", new { predictionId });
    }

    public async Task<(IReadOnlyList<PredictionWithFlow> Items, int TotalCount)> GetByUploadPagedAsync(
        int pcapUploadId, int page, int pageSize, bool anomaliesOnly, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var anomalyFilter = anomaliesOnly ? " AND p.IsAnomaly = 1" : "";
        var offset = Math.Max(0, page - 1) * pageSize;

        var total = await conn.ExecuteScalarAsync<int>($"""
            SELECT COUNT(*) FROM dbo.Predictions p JOIN dbo.Flows f ON f.FlowId = p.FlowId
            WHERE f.PcapUploadId = @pcapUploadId {anomalyFilter}
            """, new { pcapUploadId });

        var rows = await conn.QueryAsync<PredictionWithFlow>($"""
            {BaseSelect}
            WHERE f.PcapUploadId = @pcapUploadId {anomalyFilter}
            ORDER BY p.ScoredAtUtc DESC
            OFFSET @offset ROWS FETCH NEXT @pageSize ROWS ONLY
            """, new { pcapUploadId, offset, pageSize });

        return (rows.AsList(), total);
    }

    public async Task<long> CreateAsync(Prediction prediction, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        const string sql = """
            INSERT INTO dbo.Predictions
                (FlowId, ModelVersionId, AnomalyProbability, Uncertainty, IsAnomaly, Threshold,
                 TopFeaturesJson, InferenceMs)
            VALUES
                (@FlowId, @ModelVersionId, @AnomalyProbability, @Uncertainty, @IsAnomaly, @Threshold,
                 @TopFeaturesJson, @InferenceMs);
            SELECT CAST(SCOPE_IDENTITY() AS BIGINT);
            """;
        return await conn.ExecuteScalarAsync<long>(sql, prediction);
    }

    public async Task SetTopFeaturesAsync(long predictionId, string topFeaturesJson, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync(
            "UPDATE dbo.Predictions SET TopFeaturesJson = @topFeaturesJson WHERE PredictionId = @predictionId",
            new { predictionId, topFeaturesJson });
    }

    public async Task<int> CountAsync(CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM dbo.Predictions");
    }

    public async Task<int> CountAnomaliesAsync(CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM dbo.Predictions WHERE IsAnomaly = 1");
    }
}
