using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CaprApi.Data.Repositories;
using CaprApi.Dtos;
using CaprApi.Models;

namespace CaprApi.Controllers;

[ApiController]
[Route("api/dashboard")]
[Authorize]
public class DashboardController : ControllerBase
{
    private readonly IPcapUploadRepository _uploads;
    private readonly IFlowRepository _flows;
    private readonly IPredictionRepository _predictions;
    private readonly IAlertRepository _alerts;
    private readonly IModelVersionRepository _models;

    public DashboardController(
        IPcapUploadRepository uploads, IFlowRepository flows, IPredictionRepository predictions,
        IAlertRepository alerts, IModelVersionRepository models)
    {
        _uploads = uploads;
        _flows = flows;
        _predictions = predictions;
        _alerts = alerts;
        _models = models;
    }

    [HttpGet("summary")]
    public async Task<ActionResult<DashboardSummaryDto>> GetSummary(CancellationToken ct)
    {
        var totalUploadsTask = _uploads.CountAsync(ct);
        var totalFlowsTask = _flows.CountAsync(ct);
        var totalAnomaliesTask = _predictions.CountAnomaliesAsync(ct);
        var openAlertsTask = _alerts.CountByStatusAsync(AlertStatus.Open, ct);
        var severityTask = _alerts.CountBySeverityAsync(AlertStatus.Open, ct);
        var recentAlertsTask = _alerts.GetRecentAsync(10, AlertStatus.Open, ct);
        var recentUploadsTask = _uploads.GetRecentAsync(10, ct);
        var modelsTask = _models.GetAllAsync(ct);

        await Task.WhenAll(totalUploadsTask, totalFlowsTask, totalAnomaliesTask, openAlertsTask,
            severityTask, recentAlertsTask, recentUploadsTask, modelsTask);

        var summary = new DashboardSummaryDto(
            TotalUploads: totalUploadsTask.Result,
            TotalFlows: totalFlowsTask.Result,
            TotalAnomalies: totalAnomaliesTask.Result,
            OpenAlerts: openAlertsTask.Result,
            AlertsBySeverity: severityTask.Result,
            ActiveModelCount: modelsTask.Result.Count(m => m.IsActive),
            RecentAlerts: recentAlertsTask.Result.Select(AlertDto.From).ToList(),
            RecentUploads: recentUploadsTask.Result.Select(UploadSummaryDto.From).ToList());

        return Ok(summary);
    }
}
