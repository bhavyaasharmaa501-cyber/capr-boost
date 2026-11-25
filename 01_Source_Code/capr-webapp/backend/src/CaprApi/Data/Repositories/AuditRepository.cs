using Dapper;

namespace CaprApi.Data.Repositories;

public record AuditEventRow(long AuditEventId, int? UserId, string? Email, string EventType, string? Details,
                            string? IpAddress, DateTime CreatedAtUtc);

public interface IAuditRepository
{
    Task LogAsync(int? userId, string eventType, string? details, string? ip, CancellationToken ct = default);
    Task<IReadOnlyList<AuditEventRow>> GetRecentAsync(int take, CancellationToken ct = default);
}

public class AuditRepository : IAuditRepository
{
    private readonly IDbConnectionFactory _db;
    public AuditRepository(IDbConnectionFactory db) => _db = db;

    public async Task LogAsync(int? userId, string eventType, string? details, string? ip, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync("""
            INSERT INTO dbo.AuditEvents (UserId, EventType, Details, IpAddress)
            VALUES (@userId, @eventType, @details, @ip)
            """, new { userId, eventType, details, ip });
    }

    public async Task<IReadOnlyList<AuditEventRow>> GetRecentAsync(int take, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var rows = await conn.QueryAsync<AuditEventRow>("""
            SELECT TOP (@take) a.AuditEventId, a.UserId, u.Email, a.EventType, a.Details, a.IpAddress, a.CreatedAtUtc
            FROM dbo.AuditEvents a LEFT JOIN dbo.Users u ON u.UserId = a.UserId
            ORDER BY a.CreatedAtUtc DESC
            """, new { take });
        return rows.AsList();
    }
}
