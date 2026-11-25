using Dapper;
using CaprApi.Models;

namespace CaprApi.Data.Repositories;

public interface IPasswordResetRepository
{
    Task<int> CountRecentAsync(int userId, TimeSpan window, CancellationToken ct = default);
    Task CreateAsync(int userId, string codeHash, DateTime expiresAtUtc, string? requestIp, CancellationToken ct = default);
    Task<PasswordResetToken?> GetLatestActiveAsync(int userId, CancellationToken ct = default);
    Task IncrementAttemptsAsync(int resetTokenId, CancellationToken ct = default);
    Task MarkUsedAsync(int userId, CancellationToken ct = default);
}

public class PasswordResetRepository : IPasswordResetRepository
{
    private readonly IDbConnectionFactory _db;
    public PasswordResetRepository(IDbConnectionFactory db) => _db = db;

    public async Task<int> CountRecentAsync(int userId, TimeSpan window, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<int>(
            "SELECT COUNT(*) FROM dbo.PasswordResetTokens WHERE UserId = @userId AND CreatedAtUtc > @since",
            new { userId, since = DateTime.UtcNow - window });
    }

    public async Task CreateAsync(int userId, string codeHash, DateTime expiresAtUtc, string? requestIp, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync("""
            UPDATE dbo.PasswordResetTokens SET UsedAtUtc = SYSUTCDATETIME()
            WHERE UserId = @userId AND UsedAtUtc IS NULL;
            INSERT INTO dbo.PasswordResetTokens (UserId, CodeHash, ExpiresAtUtc, RequestIp)
            VALUES (@userId, @codeHash, @expiresAtUtc, @requestIp);
            """, new { userId, codeHash, expiresAtUtc, requestIp });
    }

    public async Task<PasswordResetToken?> GetLatestActiveAsync(int userId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<PasswordResetToken>("""
            SELECT TOP 1 * FROM dbo.PasswordResetTokens
            WHERE UserId = @userId AND UsedAtUtc IS NULL AND ExpiresAtUtc > SYSUTCDATETIME()
            ORDER BY CreatedAtUtc DESC
            """, new { userId });
    }

    public async Task IncrementAttemptsAsync(int resetTokenId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync(
            "UPDATE dbo.PasswordResetTokens SET Attempts = Attempts + 1 WHERE ResetTokenId = @resetTokenId",
            new { resetTokenId });
    }

    public async Task MarkUsedAsync(int userId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync(
            "UPDATE dbo.PasswordResetTokens SET UsedAtUtc = SYSUTCDATETIME() WHERE UserId = @userId AND UsedAtUtc IS NULL",
            new { userId });
    }
}
