using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CaprApi.Data.Repositories;
using CaprApi.Dtos;

namespace CaprApi.Controllers;

[ApiController]
[Route("api/predictions")]
[Authorize]
public class PredictionsController : ControllerBase
{
    private readonly IPredictionRepository _predictions;

    public PredictionsController(IPredictionRepository predictions) => _predictions = predictions;

    [HttpGet]
    public async Task<ActionResult<PagedResult<PredictionDto>>> GetByUpload(
        [FromQuery] int uploadId, [FromQuery] int page = 1, [FromQuery] int pageSize = 50,
        [FromQuery] bool anomaliesOnly = false, CancellationToken ct = default)
    {
        if (uploadId <= 0)
            return BadRequest(new { detail = "uploadId is required" });
        page = Math.Max(1, page);
        pageSize = Math.Clamp(pageSize, 1, 500);

        var (items, total) = await _predictions.GetByUploadPagedAsync(uploadId, page, pageSize, anomaliesOnly, ct);
        var dtos = items.Select(ToDto).ToList();
        return Ok(new PagedResult<PredictionDto>(dtos, page, pageSize, total));
    }

    [HttpGet("{id:long}")]
    public async Task<ActionResult<PredictionDto>> GetById(long id, CancellationToken ct)
    {
        var row = await _predictions.GetByIdAsync(id, ct);
        return row is null ? NotFound() : Ok(ToDto(row));
    }

    private static PredictionDto ToDto(PredictionWithFlow p)
    {
        List<FeatureContributionDto>? topFeatures = null;
        if (!string.IsNullOrWhiteSpace(p.TopFeaturesJson))
        {
            try { topFeatures = JsonSerializer.Deserialize<List<FeatureContributionDto>>(p.TopFeaturesJson); }
            catch { topFeatures = null; }
        }

        return new PredictionDto(
            p.PredictionId, p.FlowId, p.PcapUploadId, p.SrcIp, p.DstIp, p.SrcPort, p.DstPort,
            p.AnomalyProbability, p.Uncertainty, p.IsAnomaly, p.Threshold, p.ScoredAtUtc,
            p.InferenceMs, topFeatures);
    }
}
