using Dapper;
using CaprApi.Models;

namespace CaprApi.Data.Repositories;

public class AlertWithContext
{
    public long AlertId { get; set; }
    public long PredictionId { get; set; }
    public string Severity { get; set; } = "";
    public string Title { get; set; } = "";
    public string? Description { get; set; }
    public string Status { get; set; } = "";
    public int? AcknowledgedBy { get; set; }
    public DateTime? AcknowledgedAtUtc { get; set; }
    public DateTime CreatedAtUtc { get; set; }
    public double AnomalyProbability { get; set; }
    public string? SrcIp { get; set; }
    public string? DstIp { get; set; }
    public int? SrcPort { get; set; }
    public int? DstPort { get; set; }
}

public interface IAlertRepository
{
    Task<AlertWithContext?> GetByIdAsync(long alertId, CancellationToken ct = default);
    Task<IReadOnlyList<AlertWithContext>> GetRecentAsync(int limit, string? status, CancellationToken ct = default);
    Task<long> CreateAsync(Alert alert, CancellationToken ct = default);
    Task<bool> SetStatusAsync(long alertId, string status, int acknowledgedByUserId, CancellationToken ct = default);
    Task<int> CountByStatusAsync(string status, CancellationToken ct = default);
    Task<Dictionary<string, int>> CountBySeverityAsync(string status, CancellationToken ct = default);
}

public class AlertRepository : IAlertRepository
{
    private readonly IDbConnectionFactory _db;
    public AlertRepository(IDbConnectionFactory db) => _db = db;

    private const string BaseSelect = """
        SELECT a.AlertId, a.PredictionId, a.Severity, a.Title, a.Description, a.Status,
               a.AcknowledgedBy, a.AcknowledgedAtUtc, a.CreatedAtUtc,
               p.AnomalyProbability, f.SrcIp, f.DstIp, f.SrcPort, f.DstPort
        FROM dbo.Alerts a
        JOIN dbo.Predictions p ON p.PredictionId = a.PredictionId
        JOIN dbo.Flows f ON f.FlowId = p.FlowId
        """;

    public async Task<AlertWithContext?> GetByIdAsync(long alertId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<AlertWithContext>(
            BaseSelect + " WHERE a.AlertId = @alertId", new { alertId });
    }

    public async Task<IReadOnlyList<AlertWithContext>> GetRecentAsync(
        int limit, string? status, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var statusFilter = status is null ? "" : " WHERE a.Status = @status";
        var rows = await conn.QueryAsync<AlertWithContext>(
            $"{BaseSelect}{statusFilter} ORDER BY a.CreatedAtUtc DESC OFFSET 0 ROWS FETCH NEXT @limit ROWS ONLY",
            new { limit, status });
        return rows.AsList();
    }

    public async Task<long> CreateAsync(Alert alert, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        const string sql = """
            INSERT INTO dbo.Alerts (PredictionId, Severity, Title, Description, Status)
            VALUES (@PredictionId, @Severity, @Title, @Description, @Status);
            SELECT CAST(SCOPE_IDENTITY() AS BIGINT);
            """;
        return await conn.ExecuteScalarAsync<long>(sql, alert);
    }

    public async Task<bool> SetStatusAsync(
        long alertId, string status, int acknowledgedByUserId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var affected = await conn.ExecuteAsync("""
            UPDATE dbo.Alerts
            SET Status = @status, AcknowledgedBy = @acknowledgedByUserId, AcknowledgedAtUtc = SYSUTCDATETIME()
            WHERE AlertId = @alertId
            """, new { alertId, status, acknowledgedByUserId });
        return affected > 0;
    }

    public async Task<int> CountByStatusAsync(string status, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<int>(
            "SELECT COUNT(*) FROM dbo.Alerts WHERE Status = @status", new { status });
    }

    public async Task<Dictionary<string, int>> CountBySeverityAsync(string status, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var rows = await conn.QueryAsync<SeverityCount>("""
            SELECT Severity, COUNT(*) AS Count FROM dbo.Alerts WHERE Status = @status GROUP BY Severity
            """, new { status });
        return rows.ToDictionary(r => r.Severity, r => r.Count);
    }

    private class SeverityCount
    {
        public string Severity { get; set; } = "";
        public int Count { get; set; }
    }
}
