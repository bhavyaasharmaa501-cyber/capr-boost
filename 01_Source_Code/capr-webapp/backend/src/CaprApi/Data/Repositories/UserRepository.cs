using Dapper;
using CaprApi.Models;

namespace CaprApi.Data.Repositories;

public interface IUserRepository
{
    Task<User?> GetByIdAsync(int userId, CancellationToken ct = default);
    Task<User?> GetByEmailAsync(string email, CancellationToken ct = default);
    Task<IReadOnlyList<User>> GetAllAsync(CancellationToken ct = default);
    Task<int> CreateAsync(User user, CancellationToken ct = default);
    Task UpdatePasswordHashAsync(int userId, string passwordHash, CancellationToken ct = default);
    Task UpdateLastLoginAsync(int userId, CancellationToken ct = default);
}

public class UserRepository : IUserRepository
{
    private readonly IDbConnectionFactory _db;
    public UserRepository(IDbConnectionFactory db) => _db = db;

    public async Task<User?> GetByIdAsync(int userId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<User>(
            "SELECT * FROM dbo.Users WHERE UserId = @userId", new { userId });
    }

    public async Task<User?> GetByEmailAsync(string email, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<User>(
            "SELECT * FROM dbo.Users WHERE Email = @email", new { email });
    }

    public async Task<IReadOnlyList<User>> GetAllAsync(CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var rows = await conn.QueryAsync<User>("SELECT * FROM dbo.Users ORDER BY CreatedAtUtc");
        return rows.AsList();
    }

    public async Task<int> CreateAsync(User user, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        const string sql = """
            INSERT INTO dbo.Users (Email, DisplayName, PasswordHash, Role, IsActive)
            VALUES (@Email, @DisplayName, @PasswordHash, @Role, @IsActive);
            SELECT CAST(SCOPE_IDENTITY() AS INT);
            """;
        return await conn.ExecuteScalarAsync<int>(sql, user);
    }

    public async Task UpdatePasswordHashAsync(int userId, string passwordHash, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync("UPDATE dbo.Users SET PasswordHash = @passwordHash, PasswordChangedAtUtc = SYSUTCDATETIME() WHERE UserId = @userId",
            new { userId, passwordHash });
    }

    public async Task UpdateLastLoginAsync(int userId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        await conn.ExecuteAsync(
            "UPDATE dbo.Users SET LastLoginUtc = SYSUTCDATETIME() WHERE UserId = @userId", new { userId });
    }
}
