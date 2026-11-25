namespace CaprApi.Dtos;

public record UploadSummaryDto(
    int PcapUploadId, string OriginalFileName, long FileSizeBytes, string Status,
    string? ErrorMessage, int? ModelVersionId, int? FlowCount, int? AnomalyCount,
    DateTime UploadedAtUtc, DateTime? CompletedAtUtc)
{
    public static UploadSummaryDto From(Models.PcapUpload u) => new(
        u.PcapUploadId, u.OriginalFileName, u.FileSizeBytes, u.Status, u.ErrorMessage,
        u.ModelVersionId, u.FlowCount, u.AnomalyCount, u.UploadedAtUtc, u.CompletedAtUtc);
}

public record UploadNotification(int PcapUploadId, string OriginalFileName, string Status,
                                  int? FlowCount, int? AnomalyCount, string? Note);
