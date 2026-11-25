using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CaprApi.Data.Repositories;
using CaprApi.Dtos;
using CaprApi.Models;
using CaprApi.Services;

namespace CaprApi.Controllers;

[ApiController]
[Route("api/models")]
[Authorize]
public class ModelsController : ControllerBase
{
    private readonly IModelVersionRepository _repo;
    private readonly ModelSyncService _sync;

    public ModelsController(IModelVersionRepository repo, ModelSyncService sync)
    {
        _repo = repo;
        _sync = sync;
    }

    [HttpGet]
    public async Task<ActionResult<List<ModelVersionDto>>> GetAll(CancellationToken ct)
    {
        var rows = await _repo.GetAllAsync(ct);
        return Ok(rows.Select(ToDto).ToList());
    }

    [HttpPost("sync")]
    [Authorize(Roles = Roles.Admin)]
    public async Task<ActionResult<List<ModelVersionDto>>> Sync(CancellationToken ct)
    {
        try
        {
            var models = await _sync.SyncAsync(ct);
            return Ok(models.Select(ToDto).ToList());
        }
        catch (Exception ex)
        {
            return StatusCode(StatusCodes.Status502BadGateway,
                new { detail = $"Could not reach the ml-service: {ex.Message}" });
        }
    }

    private static ModelVersionDto ToDto(ModelVersion m)
    {
        List<string> features;
        try { features = JsonSerializer.Deserialize<List<string>>(m.FeatureNamesJson) ?? new(); }
        catch { features = new(); }

        return new ModelVersionDto(
            m.ModelVersionId, m.DatasetName, m.MethodName, m.LabelRatio, features.Count,
            m.TestAccuracy, m.TestPrecision, m.TestRecall, m.TestF1, m.TestAucPr, m.TestAucRoc, m.TestFpr,
            m.EnsembleSize, m.IsActive, m.RegisteredAtUtc);
    }
}
