using Dapper;
using CaprApi.Models;

namespace CaprApi.Data.Repositories;

public interface IFlowRepository
{
    Task<FlowRecord?> GetByIdAsync(long flowId, CancellationToken ct = default);
    Task<IReadOnlyList<FlowRecord>> GetByUploadAsync(int pcapUploadId, CancellationToken ct = default);
    Task<long> CreateAsync(FlowRecord flow, CancellationToken ct = default);
    Task<int> CountAsync(CancellationToken ct = default);
}

public class FlowRepository : IFlowRepository
{
    private readonly IDbConnectionFactory _db;
    public FlowRepository(IDbConnectionFactory db) => _db = db;

    public async Task<FlowRecord?> GetByIdAsync(long flowId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.QuerySingleOrDefaultAsync<FlowRecord>(
            "SELECT * FROM dbo.Flows WHERE FlowId = @flowId", new { flowId });
    }

    public async Task<IReadOnlyList<FlowRecord>> GetByUploadAsync(int pcapUploadId, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        var rows = await conn.QueryAsync<FlowRecord>(
            "SELECT * FROM dbo.Flows WHERE PcapUploadId = @pcapUploadId ORDER BY FlowId", new { pcapUploadId });
        return rows.AsList();
    }

    public async Task<long> CreateAsync(FlowRecord flow, CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        const string sql = """
            INSERT INTO dbo.Flows
                (PcapUploadId, SrcIp, DstIp, SrcPort, DstPort, Protocol, FlowStartUtc, DurationMs, FeaturesJson)
            VALUES
                (@PcapUploadId, @SrcIp, @DstIp, @SrcPort, @DstPort, @Protocol, @FlowStartUtc, @DurationMs, @FeaturesJson);
            SELECT CAST(SCOPE_IDENTITY() AS BIGINT);
            """;
        return await conn.ExecuteScalarAsync<long>(sql, flow);
    }

    public async Task<int> CountAsync(CancellationToken ct = default)
    {
        using var conn = await _db.CreateOpenConnectionAsync(ct);
        return await conn.ExecuteScalarAsync<int>("SELECT COUNT(*) FROM dbo.Flows");
    }
}
