namespace CaprApi.Dtos;

public record AlertDto(
    long AlertId, long PredictionId, string Severity, string Title, string? Description,
    string Status, int? AcknowledgedBy, DateTime? AcknowledgedAtUtc, DateTime CreatedAtUtc,
    double AnomalyProbability, string? SrcIp, string? DstIp, int? SrcPort, int? DstPort)
{
    public static AlertDto From(Data.Repositories.AlertWithContext a) => new(
        a.AlertId, a.PredictionId, a.Severity, a.Title, a.Description, a.Status,
        a.AcknowledgedBy, a.AcknowledgedAtUtc, a.CreatedAtUtc,
        a.AnomalyProbability, a.SrcIp, a.DstIp, a.SrcPort, a.DstPort);
}

public record AcknowledgeAlertRequest(string Status);
