namespace CaprApi.Models;

public class Alert
{
    public long AlertId { get; set; }
    public long PredictionId { get; set; }
    public string Severity { get; set; } = "Low";
    public string Title { get; set; } = "";
    public string? Description { get; set; }
    public string Status { get; set; } = "Open";
    public int? AcknowledgedBy { get; set; }
    public DateTime? AcknowledgedAtUtc { get; set; }
    public DateTime CreatedAtUtc { get; set; }
}

public static class AlertSeverity
{
    public const string Low = "Low";
    public const string Medium = "Medium";
    public const string High = "High";
    public const string Critical = "Critical";
}

public static class AlertStatus
{
    public const string Open = "Open";
    public const string Acknowledged = "Acknowledged";
    public const string Resolved = "Resolved";
    public const string FalsePositive = "FalsePositive";
}
