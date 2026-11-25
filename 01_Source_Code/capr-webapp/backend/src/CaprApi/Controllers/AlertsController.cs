using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CaprApi.Auth;
using CaprApi.Data.Repositories;
using CaprApi.Dtos;
using CaprApi.Models;

namespace CaprApi.Controllers;

[ApiController]
[Route("api/alerts")]
[Authorize]
public class AlertsController : ControllerBase
{
    private static readonly string[] ValidTransitions =
        { AlertStatus.Acknowledged, AlertStatus.Resolved, AlertStatus.FalsePositive };

    private readonly IAlertRepository _alerts;

    public AlertsController(IAlertRepository alerts) => _alerts = alerts;

    [HttpGet]
    public async Task<ActionResult<List<AlertDto>>> GetRecent(
        [FromQuery] string? status = null, [FromQuery] int limit = 100, CancellationToken ct = default)
    {
        var rows = await _alerts.GetRecentAsync(Math.Clamp(limit, 1, 500), status, ct);
        return Ok(rows.Select(AlertDto.From).ToList());
    }

    [HttpGet("{id:long}")]
    public async Task<ActionResult<AlertDto>> GetById(long id, CancellationToken ct)
    {
        var row = await _alerts.GetByIdAsync(id, ct);
        return row is null ? NotFound() : Ok(AlertDto.From(row));
    }

    [HttpPatch("{id:long}/status")]
    public async Task<ActionResult<AlertDto>> UpdateStatus(
        long id, AcknowledgeAlertRequest request, CancellationToken ct)
    {
        if (!ValidTransitions.Contains(request.Status))
            return BadRequest(new { detail = $"status must be one of: {string.Join(", ", ValidTransitions)}" });

        var updated = await _alerts.SetStatusAsync(id, request.Status, User.GetUserId(), ct);
        if (!updated)
            return NotFound();

        var row = await _alerts.GetByIdAsync(id, ct);
        return row is null ? NotFound() : Ok(AlertDto.From(row));
    }
}
