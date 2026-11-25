using System.Data;
using Microsoft.Data.SqlClient;

namespace CaprApi.Data;

public class SqlConnectionFactory : IDbConnectionFactory
{
    private readonly string _connectionString;

    public SqlConnectionFactory(IConfiguration config)
    {
        _connectionString = config.GetConnectionString("CaprDb")
            ?? throw new InvalidOperationException(
                "Missing ConnectionStrings:CaprDb -- set it in appsettings.json, an environment " +
                "variable (ConnectionStrings__CaprDb), or `dotnet user-secrets`.");
    }

    public async Task<IDbConnection> CreateOpenConnectionAsync(CancellationToken ct = default)
    {
        var conn = new SqlConnection(_connectionString);
        await conn.OpenAsync(ct);
        return conn;
    }
}
