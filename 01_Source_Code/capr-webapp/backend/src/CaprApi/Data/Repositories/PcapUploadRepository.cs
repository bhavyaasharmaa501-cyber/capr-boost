using Dapper;
using CaprApi.Models;

namespace CaprApi.Data.Repositories;

public interface IPcapUploadRepository
{
    Task<PcapUpload?> GetByIdAsync(int id, CancellationToken ct = default);
    Task<IReadOnlyList<PcapUpload>> GetRecentAsync(int limit, CancellationToken ct = default);
    Task<IReadOnlyList<PcapUpload>> GetByUserAsync(int userId, int limit, CancellationToken ct = default);
    Task<int> CreateAsync(PcapUpload upload, CancellationToken ct = default);
    Task SetStatusAsync(int id, string status, CancellationToken ct = default);
    Task SetModelVersionAsync(int id, int modelVersionId, CancellationToken ct = default);
    Task CompleteAsync(int id, int flowCount, int anomalyCount, CancellationToken ct = default);
    Task FailAsync(int id, string errorMessage, CancellationToken ct = default);
    Task<int> CountAsync(CancellationToken ct = default);
}

public class PcapUploadRepository : IPcapUploadRepository
{
    private readonly IDbConnectionFactory _db;
    public PcapUploadRepository(IDbConnectionFactory db) => _db = db;

    public async Task<PcapUpload?> GetByIdAsync(int id, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<PcapUpload>(
            "SELECT * FROM dbo.PcapUploads WHERE PcapUploadId = @id", new { id });
    }

    public async Task<IReadOnlyList<PcapUpload>> GetRecentAsync(int limit, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var rows = await conn.QueryAsync<PcapUpload>(
            "SELECT TOP (@limit) * FROM dbo.PcapUploads ORDER BY UploadedAtUtc DESC", new { limit });
        return rows.AsList();
    }

    public async Task<IReadOnlyList<PcapUpload>> GetByUserAsync(int userId, int limit, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var rows = await conn.QueryAsync<PcapUpload>("""
            SELECT TOP (@limit) * FROM dbo.PcapUploads
            WHERE UserId = @userId ORDER BY UploadedAtUtc DESC
            """, new { userId, limit });
        return rows.AsList();
    }

    public async Task<int> CreateAsync(PcapUpload upload, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        const string sql = """
            INSERT INTO dbo.PcapUploads
                (UserId, OriginalFileName, StoredPath, FileSizeBytes, Status, ModelVersionId)
            VALUES (@UserId, @OriginalFileName, @StoredPath, @FileSizeBytes, @Status, @ModelVersionId);
            SELECT CAST(SCOPE_IDENTITY() AS INT);
            """;
        return await conn.ExecuteScalarAsync<int>(sql, upload);
    }

    public async Task SetStatusAsync(int id, string status, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync("UPDATE dbo.PcapUploads SET Status = @status WHERE PcapUploadId = @id",
            new { id, status });
    }

    public async Task SetModelVersionAsync(int id, int modelVersionId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync(
            "UPDATE dbo.PcapUploads SET ModelVersionId = @modelVersionId WHERE PcapUploadId = @id",
            new { id, modelVersionId });
    }

    public async Task CompleteAsync(int id, int flowCount, int anomalyCount, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync("""
            UPDATE dbo.PcapUploads
            SET Status = 'Completed', FlowCount = @flowCount, AnomalyCount = @anomalyCount,
                CompletedAtUtc = SYSUTCDATETIME()
            WHERE PcapUploadId = @id
            """, new { id, flowCount, anomalyCount });
    }

    public async Task FailAsync(int id, string errorMessage, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync("""
            UPDATE dbo.PcapUploads
            SET Status = 'Failed', ErrorMessage = @errorMessage, CompletedAtUtc = SYSUTCDATETIME()
            WHERE PcapUploadId = @id
            """, new { id, errorMessage });
    }

    public async Task<int> CountAsync(CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM dbo.PcapUploads");
    }
}
