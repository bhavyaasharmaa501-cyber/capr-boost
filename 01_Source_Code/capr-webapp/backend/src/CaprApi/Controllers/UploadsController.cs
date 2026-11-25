using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CaprApi.Auth;
using CaprApi.Data.Repositories;
using CaprApi.Dtos;
using CaprApi.Models;
using CaprApi.Services;

namespace CaprApi.Controllers;

[ApiController]
[Route("api/uploads")]
[Authorize]
public class UploadsController : ControllerBase
{
    private readonly UploadProcessingService _processing;
    private readonly IPcapUploadRepository _uploads;

    public UploadsController(UploadProcessingService processing, IPcapUploadRepository uploads)
    {
        _processing = processing;
        _uploads = uploads;
    }

    [HttpGet]
    public async Task<ActionResult<List<UploadSummaryDto>>> GetRecent(
        [FromQuery] int limit = 50, CancellationToken ct = default)
    {
        var rows = await _uploads.GetRecentAsync(Math.Clamp(limit, 1, 200), ct);
        return Ok(rows.Select(UploadSummaryDto.From).ToList());
    }

    [HttpGet("{id:int}")]
    public async Task<ActionResult<UploadSummaryDto>> GetById(int id, CancellationToken ct)
    {
        var upload = await _uploads.GetByIdAsync(id, ct);
        return upload is null ? NotFound() : Ok(UploadSummaryDto.From(upload));
    }

    [HttpPost("csv")]
    [Authorize(Roles = "Admin,Analyst")]
    [RequestSizeLimit(200_000_000)]
    public Task<ActionResult<UploadSummaryDto>> UploadCsv(
        [FromForm] string dataset, IFormFile file, CancellationToken ct)
        => UploadCommon(dataset, file, UploadKind.Csv, ct);

    [HttpPost("pcap")]
    [Authorize(Roles = "Admin,Analyst")]
    [RequestSizeLimit(200_000_000)]
    public Task<ActionResult<UploadSummaryDto>> UploadPcap(
        [FromForm] string dataset, IFormFile file, CancellationToken ct)
        => UploadCommon(dataset, file, UploadKind.Pcap, ct);

    private async Task<ActionResult<UploadSummaryDto>> UploadCommon(
        string dataset, IFormFile file, UploadKind kind, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(dataset))
            return BadRequest(new { detail = "'dataset' is required, e.g. 'darknet2020'" });
        if (file is null || file.Length == 0)
            return BadRequest(new { detail = "No file uploaded, or the file is empty" });

        try
        {
            await using var stream = file.OpenReadStream();
            var upload = await _processing.ProcessAsync(
                User.GetUserId(), dataset, kind, stream, file.FileName, file.Length, ct);
            return Ok(UploadSummaryDto.From(upload));
        }
        catch (InvalidOperationException ex)
        {
            return UnprocessableEntity(new { detail = ex.Message });
        }
        catch (MlServiceException ex)
        {
            return StatusCode(StatusCodes.Status502BadGateway,
                new { detail = ex.ExtractDetail() ?? ex.Message });
        }
    }
}
