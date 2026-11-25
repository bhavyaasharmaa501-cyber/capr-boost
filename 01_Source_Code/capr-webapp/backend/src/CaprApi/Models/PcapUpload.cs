namespace CaprApi.Models;

public class PcapUpload
{
    public int PcapUploadId { get; set; }
    public int UserId { get; set; }
    public string OriginalFileName { get; set; } = "";
    public string StoredPath { get; set; } = "";
    public long FileSizeBytes { get; set; }
    public string Status { get; set; } = "Pending";
    public string? ErrorMessage { get; set; }
    public int? ModelVersionId { get; set; }
    public int? FlowCount { get; set; }
    public int? AnomalyCount { get; set; }
    public DateTime UploadedAtUtc { get; set; }
    public DateTime? CompletedAtUtc { get; set; }
}

public static class UploadStatus
{
    public const string Pending = "Pending";
    public const string Extracting = "Extracting";
    public const string Predicting = "Predicting";
    public const string Completed = "Completed";
    public const string Failed = "Failed";
}
