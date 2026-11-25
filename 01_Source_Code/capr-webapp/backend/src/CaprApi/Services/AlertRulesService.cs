using CaprApi.Data.Repositories;
using CaprApi.Models;

namespace CaprApi.Services;

public class AlertRulesService
{
    private readonly IAlertRepository _alerts;

    public AlertRulesService(IAlertRepository alerts) => _alerts = alerts;

    public async Task<Alert> CreateForPredictionAsync(
        long predictionId, double probability, double? uncertainty,
        string? srcIp, string? dstIp, int? srcPort, int? dstPort, CancellationToken ct = default)
    {
        var severity = ClassifySeverity(probability, uncertainty);
        var endpoint = srcIp is not null && dstIp is not null
            ? $"{srcIp}:{(srcPort?.ToString() ?? "?")} -> {dstIp}:{(dstPort?.ToString() ?? "?")}"
            : "endpoint not present in the uploaded file";

        var alert = new Alert
        {
            PredictionId = predictionId,
            Severity = severity,
            Title = $"Anomalous flow detected ({probability:P0} confidence)",
            Description = $"Flow {endpoint} scored {probability:F3} anomaly probability" +
                           (uncertainty is double u ? $", ensemble uncertainty {u:F3}" : "") + ".",
            Status = AlertStatus.Open,
        };
        alert.AlertId = await _alerts.CreateAsync(alert, ct);
        return alert;
    }

    public static string ClassifySeverity(double probability, double? uncertainty)
    {
        var uncertain = uncertainty is double u && u > 0.08;
        return probability switch
        {
            >= 0.9 when !uncertain => AlertSeverity.Critical,
            >= 0.9 => AlertSeverity.High,
            >= 0.75 when !uncertain => AlertSeverity.High,
            >= 0.75 => AlertSeverity.Medium,
            >= 0.6 => AlertSeverity.Medium,
            _ => AlertSeverity.Low,
        };
    }
}
