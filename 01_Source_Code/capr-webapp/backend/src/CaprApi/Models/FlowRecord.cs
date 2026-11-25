namespace CaprApi.Models;

public class FlowRecord
{
    public long FlowId { get; set; }
    public int? PcapUploadId { get; set; }
    public string? SrcIp { get; set; }
    public string? DstIp { get; set; }
    public int? SrcPort { get; set; }
    public int? DstPort { get; set; }
    public byte? Protocol { get; set; }
    public DateTime? FlowStartUtc { get; set; }
    public double? DurationMs { get; set; }
    public string FeaturesJson { get; set; } = "[]";
    public DateTime CreatedAtUtc { get; set; }
}
