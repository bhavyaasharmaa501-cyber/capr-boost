using Dapper;
using CaprApi.Models;

namespace CaprApi.Data.Repositories;

public interface IModelVersionRepository
{
    Task<ModelVersion?> GetByIdAsync(int modelVersionId, CancellationToken ct = default);
    Task<ModelVersion?> GetActiveByDatasetAsync(string datasetName, CancellationToken ct = default);
    Task<IReadOnlyList<ModelVersion>> GetAllAsync(CancellationToken ct = default);

    Task<int> UpsertActiveAsync(ModelVersion mv, CancellationToken ct = default);
}

public class ModelVersionRepository : IModelVersionRepository
{
    private readonly IDbConnectionFactory _db;
    public ModelVersionRepository(IDbConnectionFactory db) => _db = db;

    public async Task<ModelVersion?> GetByIdAsync(int modelVersionId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<ModelVersion>(
            "SELECT * FROM dbo.ModelVersions WHERE ModelVersionId = @modelVersionId", new { modelVersionId });
    }

    public async Task<ModelVersion?> GetActiveByDatasetAsync(string datasetName, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<ModelVersion>(
            "SELECT * FROM dbo.ModelVersions WHERE DatasetName = @datasetName AND IsActive = 1",
            new { datasetName });
    }

    public async Task<IReadOnlyList<ModelVersion>> GetAllAsync(CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var rows = await conn.QueryAsync<ModelVersion>(
            "SELECT * FROM dbo.ModelVersions ORDER BY DatasetName, RegisteredAtUtc DESC");
        return rows.AsList();
    }

    public async Task<int> UpsertActiveAsync(ModelVersion mv, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        using var tx = conn.BeginTransaction();

        await conn.ExecuteAsync(
            "UPDATE dbo.ModelVersions SET IsActive = 0 WHERE DatasetName = @DatasetName",
            new { mv.DatasetName }, tx);

        var existingId = await conn.QuerySingleOrDefaultAsync<int?>("""
            SELECT ModelVersionId FROM dbo.ModelVersions
            WHERE DatasetName = @DatasetName AND MethodName = @MethodName
              AND LabelRatio = @LabelRatio AND ArtifactPath = @ArtifactPath
            """, mv, tx);

        int id;
        if (existingId is int existing)
        {
            await conn.ExecuteAsync("""
                UPDATE dbo.ModelVersions SET
                    FeatureNamesJson = @FeatureNamesJson, TestF1 = @TestF1, TestAucPr = @TestAucPr,
                    TestAucRoc = @TestAucRoc, TestFpr = @TestFpr, TestAccuracy = @TestAccuracy,
                    TestPrecision = @TestPrecision, TestRecall = @TestRecall, EnsembleSize = @EnsembleSize,
                    IsActive = 1, Notes = @Notes
                WHERE ModelVersionId = @Id
                """, new { mv.FeatureNamesJson, mv.TestF1, mv.TestAucPr, mv.TestAucRoc, mv.TestFpr,
                           mv.TestAccuracy, mv.TestPrecision, mv.TestRecall, mv.EnsembleSize,
                           mv.Notes, Id = existing }, tx);
            id = existing;
        }
        else
        {
            id = await conn.ExecuteScalarAsync<int>("""
                INSERT INTO dbo.ModelVersions
                    (DatasetName, MethodName, LabelRatio, ArtifactPath, FeatureNamesJson,
                     TestF1, TestAucPr, TestAucRoc, TestFpr, TestAccuracy, TestPrecision, TestRecall,
                     EnsembleSize, IsActive, Notes)
                VALUES
                    (@DatasetName, @MethodName, @LabelRatio, @ArtifactPath, @FeatureNamesJson,
                     @TestF1, @TestAucPr, @TestAucRoc, @TestFpr, @TestAccuracy, @TestPrecision, @TestRecall,
                     @EnsembleSize, 1, @Notes);
                SELECT CAST(SCOPE_IDENTITY() AS INT);
                """, mv, tx);
        }

        tx.Commit();
        return id;
    }
}
