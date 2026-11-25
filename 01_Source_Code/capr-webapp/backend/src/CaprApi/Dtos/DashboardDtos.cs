namespace CaprApi.Dtos;

public record DashboardSummaryDto(
    int TotalUploads, int TotalFlows, int TotalAnomalies, int OpenAlerts,
    Dictionary<string, int> AlertsBySeverity, int ActiveModelCount,
    IReadOnlyList<AlertDto> RecentAlerts, IReadOnlyList<UploadSummaryDto> RecentUploads);
