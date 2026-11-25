using System.Globalization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CaprApi.Data.Repositories;
using CaprApi.Dtos;
using CaprApi.Models;

namespace CaprApi.Controllers;

[ApiController]
[Route("api/experiments")]
[Authorize]
public class ExperimentsController : ControllerBase
{
    private static readonly string[] RequiredColumns =
        { "dataset", "method", "label_ratio", "noise_rate", "seed",
          "f1", "auc_roc", "auc_pr", "precision", "recall", "fpr" };

    private readonly IExperimentRunRepository _repo;

    public ExperimentsController(IExperimentRunRepository repo) => _repo = repo;

    [HttpGet]
    public async Task<ActionResult<List<ExperimentRunDto>>> GetAll(
        [FromQuery] string? dataset, CancellationToken ct)
    {
        var rows = await _repo.GetAllAsync(dataset, ct);
        return Ok(rows.Select(ExperimentRunDto.From).ToList());
    }

    [HttpGet("aggregate")]
    public async Task<ActionResult<List<ExperimentAggregateDto>>> GetAggregates(
        [FromQuery] string? dataset, CancellationToken ct)
    {
        var rows = await _repo.GetAggregatesAsync(dataset, ct);
        return Ok(rows.Select(r => new ExperimentAggregateDto(
            r.DatasetName, r.MethodName, r.LabelRatio, r.NoiseRate, r.NumSeeds,
            r.AccuracyMean, r.AccuracyStd, r.F1Mean, r.F1Std, r.AucPrMean, r.AucPrStd, r.AucRocMean, r.FprMean)).ToList());
    }

    [HttpPost("import")]
    [Authorize(Roles = Roles.Admin)]
    [RequestSizeLimit(50_000_000)]
    public async Task<ActionResult<ImportExperimentsResult>> Import(IFormFile file, CancellationToken ct)
    {
        if (file is null || file.Length == 0)
            return BadRequest(new { detail = "No file uploaded, or the file is empty" });

        List<Dictionary<string, string>> rows;
        try
        {
            await using var stream = file.OpenReadStream();
            using var reader = new StreamReader(stream);
            rows = await ParseCsvAsync(reader, ct);
        }
        catch (Exception ex)
        {
            return UnprocessableEntity(new { detail = $"Could not parse '{file.FileName}' as CSV: {ex.Message}" });
        }

        var missing = RequiredColumns.Where(c => rows.Count > 0 && !rows[0].ContainsKey(c)).ToList();
        if (missing.Count > 0)
            return UnprocessableEntity(new
            {
                detail = $"CSV is missing column(s): {string.Join(", ", missing)}. This endpoint expects " +
                          "run_experiments.py's raw_results.csv, not summary.csv or capr_history.csv."
            });

        int inserted = 0, skipped = 0;
        var culture = CultureInfo.InvariantCulture;
        foreach (var row in rows)
        {
            var run = new ExperimentRun
            {
                DatasetName = row["dataset"],
                MethodName = row["method"],
                LabelRatio = double.Parse(row["label_ratio"], culture),
                NoiseRate = double.Parse(row["noise_rate"], culture),
                Seed = int.Parse(row["seed"], culture),
                Accuracy = row.TryGetValue("accuracy", out var acc) && double.TryParse(acc, NumberStyles.Float, culture, out var accVal)
                    ? accVal : null,
                F1 = double.Parse(row["f1"], culture),
                AucRoc = double.Parse(row["auc_roc"], culture),
                AucPr = double.Parse(row["auc_pr"], culture),
                Precision_ = double.Parse(row["precision"], culture),
                Recall_ = double.Parse(row["recall"], culture),
                Fpr = double.Parse(row["fpr"], culture),
                Mcc = row.TryGetValue("mcc", out var mcc) && double.TryParse(mcc, NumberStyles.Float, culture, out var mccVal)
                    ? mccVal : null,
                FitTimeSeconds = row.TryGetValue("fit_time_s", out var fit) && double.TryParse(fit, NumberStyles.Float, culture, out var fitVal)
                    ? fitVal : null,
            };

            if (await _repo.ExistsAsync(run, ct))
            {
                skipped++;
                continue;
            }
            await _repo.CreateAsync(run, ct);
            inserted++;
        }

        return Ok(new ImportExperimentsResult(rows.Count, inserted, skipped));
    }

    private static async Task<List<Dictionary<string, string>>> ParseCsvAsync(StreamReader reader, CancellationToken ct)
    {
        var lines = new List<List<string>>();
        string? line;
        while ((line = await reader.ReadLineAsync(ct)) is not null)
        {
            if (line.Length == 0) continue;
            lines.Add(SplitCsvLine(line));
        }
        if (lines.Count == 0) return new();

        var header = lines[0].Select(h => h.Trim()).ToList();
        var result = new List<Dictionary<string, string>>();
        for (int i = 1; i < lines.Count; i++)
        {
            var dict = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (int c = 0; c < header.Count && c < lines[i].Count; c++)
                dict[header[c]] = lines[i][c];
            result.Add(dict);
        }
        return result;
    }

    private static List<string> SplitCsvLine(string line)
    {
        var fields = new List<string>();
        var current = new System.Text.StringBuilder();
        bool inQuotes = false;
        for (int i = 0; i < line.Length; i++)
        {
            var ch = line[i];
            if (inQuotes)
            {
                if (ch == '"' && i + 1 < line.Length && line[i + 1] == '"') { current.Append('"'); i++; }
                else if (ch == '"') inQuotes = false;
                else current.Append(ch);
            }
            else if (ch == '"') inQuotes = true;
            else if (ch == ',') { fields.Add(current.ToString()); current.Clear(); }
            else current.Append(ch);
        }
        fields.Add(current.ToString());
        return fields;
    }
}
