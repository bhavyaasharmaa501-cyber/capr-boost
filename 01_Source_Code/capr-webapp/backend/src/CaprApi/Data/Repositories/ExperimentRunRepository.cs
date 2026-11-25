using Dapper;
using CaprApi.Models;

namespace CaprApi.Data.Repositories;

public class ExperimentAggregateRow
{
    public string DatasetName { get; set; } = "";
    public string MethodName { get; set; } = "";
    public double LabelRatio { get; set; }
    public double NoiseRate { get; set; }
    public int NumSeeds { get; set; }
    public double? AccuracyMean { get; set; }
    public double? AccuracyStd { get; set; }
    public double F1Mean { get; set; }
    public double? F1Std { get; set; }
    public double AucPrMean { get; set; }
    public double? AucPrStd { get; set; }
    public double AucRocMean { get; set; }
    public double FprMean { get; set; }
}

public interface IExperimentRunRepository
{
    Task<IReadOnlyList<ExperimentRun>> GetAllAsync(string? datasetName, CancellationToken ct = default);
    Task<IReadOnlyList<ExperimentAggregateRow>> GetAggregatesAsync(string? datasetName, CancellationToken ct = default);
    Task<bool> ExistsAsync(ExperimentRun run, CancellationToken ct = default);
    Task<int> CreateAsync(ExperimentRun run, CancellationToken ct = default);
    Task<int> CountAsync(CancellationToken ct = default);
}

public class ExperimentRunRepository : IExperimentRunRepository
{
    private readonly IDbConnectionFactory _db;
    public ExperimentRunRepository(IDbConnectionFactory db) => _db = db;

    public async Task<IReadOnlyList<ExperimentRun>> GetAllAsync(string? datasetName, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var filter = datasetName is null ? "" : "WHERE DatasetName = @datasetName";
        var rows = await conn.QueryAsync<ExperimentRun>($"""
            SELECT * FROM dbo.ExperimentRuns {filter}
            ORDER BY DatasetName, LabelRatio, NoiseRate, MethodName, Seed
            """, new { datasetName });
        return rows.AsList();
    }

    public async Task<IReadOnlyList<ExperimentAggregateRow>> GetAggregatesAsync(
        string? datasetName, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var filter = datasetName is null ? "" : "WHERE DatasetName = @datasetName";
        var rows = await conn.QueryAsync<ExperimentAggregateRow>($"""
            SELECT DatasetName, MethodName, LabelRatio, NoiseRate,
                   COUNT(*) AS NumSeeds,
                   AVG(Accuracy) AS AccuracyMean, STDEV(Accuracy) AS AccuracyStd,
                   AVG(F1) AS F1Mean, STDEV(F1) AS F1Std,
                   AVG(AucPr) AS AucPrMean, STDEV(AucPr) AS AucPrStd,
                   AVG(AucRoc) AS AucRocMean, AVG(Fpr) AS FprMean
            FROM dbo.ExperimentRuns
            {filter}
            GROUP BY DatasetName, MethodName, LabelRatio, NoiseRate
            ORDER BY DatasetName, LabelRatio, NoiseRate, MethodName
            """, new { datasetName });
        return rows.AsList();
    }

    public async Task<bool> ExistsAsync(ExperimentRun run, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var count = await conn.ExecuteScalarAsync<int>("""
            SELECT COUNT(*) FROM dbo.ExperimentRuns
            WHERE DatasetName = @DatasetName AND MethodName = @MethodName
              AND LabelRatio = @LabelRatio AND NoiseRate = @NoiseRate AND Seed = @Seed
            """, run);
        return count > 0;
    }

    public async Task<int> CreateAsync(ExperimentRun run, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        const string sql = """
            INSERT INTO dbo.ExperimentRuns
                (DatasetName, MethodName, LabelRatio, NoiseRate, Seed, Accuracy, F1, AucRoc, AucPr,
                 Precision_, Recall_, Fpr, Mcc, FitTimeSeconds)
            VALUES
                (@DatasetName, @MethodName, @LabelRatio, @NoiseRate, @Seed, @Accuracy, @F1, @AucRoc, @AucPr,
                 @Precision_, @Recall_, @Fpr, @Mcc, @FitTimeSeconds);
            SELECT CAST(SCOPE_IDENTITY() AS INT);
            """;
        return await conn.ExecuteScalarAsync<int>(sql, run);
    }

    public async Task<int> CountAsync(CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM dbo.ExperimentRuns");
    }
}
