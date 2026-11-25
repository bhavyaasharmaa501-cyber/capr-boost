using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using CaprApi.Dtos.MlService;

namespace CaprApi.Services;

public class MlServiceClient
{
    private static readonly JsonSerializerOptions JsonOpts = new(JsonSerializerDefaults.Web);

    private readonly HttpClient _http;
    private readonly ILogger<MlServiceClient> _log;

    public MlServiceClient(HttpClient http, ILogger<MlServiceClient> log)
    {
        _http = http;
        _log = log;
    }

    public async Task<MlHealthResponse> GetHealthAsync(CancellationToken ct = default)
    {
        var resp = await _http.GetAsync("/health", ct);
        resp.EnsureSuccessStatusCode();
        return (await resp.Content.ReadFromJsonAsync<MlHealthResponse>(JsonOpts, ct))!;
    }

    public async Task<List<MlModelInfo>> GetModelsAsync(CancellationToken ct = default)
    {
        var resp = await _http.GetAsync("/models", ct);
        resp.EnsureSuccessStatusCode();
        return (await resp.Content.ReadFromJsonAsync<List<MlModelInfo>>(JsonOpts, ct))!;
    }

    public async Task<MlPredictResponse> PredictAsync(MlPredictRequest request, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync("/predict", request, JsonOpts, ct);
        await ThrowIfNotSuccessAsync(resp, ct);
        return (await resp.Content.ReadFromJsonAsync<MlPredictResponse>(JsonOpts, ct))!;
    }

    public async Task<MlPredictResponse> PredictCsvAsync(
        string dataset, Stream csvStream, string fileName, bool mcUncertainty = false,
        CancellationToken ct = default)
    {
        using var form = new MultipartFormDataContent
        {
            { new StringContent(dataset), "dataset" },
            { new StringContent(mcUncertainty ? "true" : "false"), "mc_uncertainty" },
        };
        var fileContent = new StreamContent(csvStream);
        fileContent.Headers.ContentType = new MediaTypeHeaderValue("text/csv");
        form.Add(fileContent, "file", fileName);

        var resp = await _http.PostAsync("/predict/csv", form, ct);
        await ThrowIfNotSuccessAsync(resp, ct);
        return (await resp.Content.ReadFromJsonAsync<MlPredictResponse>(JsonOpts, ct))!;
    }

    public async Task<MlPredictResponse> PredictPcapAsync(
        string dataset, Stream pcapStream, string fileName, bool mcUncertainty = false,
        CancellationToken ct = default)
    {
        using var form = new MultipartFormDataContent
        {
            { new StringContent(dataset), "dataset" },
            { new StringContent(mcUncertainty ? "true" : "false"), "mc_uncertainty" },
        };
        var fileContent = new StreamContent(pcapStream);
        fileContent.Headers.ContentType = new MediaTypeHeaderValue("application/vnd.tcpdump.pcap");
        form.Add(fileContent, "file", fileName);

        var resp = await _http.PostAsync("/predict/pcap", form, ct);
        await ThrowIfNotSuccessAsync(resp, ct);
        return (await resp.Content.ReadFromJsonAsync<MlPredictResponse>(JsonOpts, ct))!;
    }

    public async Task<MlExplainResponse> ExplainAsync(MlExplainRequest request, CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync("/explain", request, JsonOpts, ct);
        await ThrowIfNotSuccessAsync(resp, ct);
        return (await resp.Content.ReadFromJsonAsync<MlExplainResponse>(JsonOpts, ct))!;
    }

    private async Task ThrowIfNotSuccessAsync(HttpResponseMessage resp, CancellationToken ct)
    {
        if (resp.IsSuccessStatusCode) return;
        var body = await resp.Content.ReadAsStringAsync(ct);
        _log.LogWarning("ml-service returned {Status} for {Method} {Uri}: {Body}",
            (int)resp.StatusCode, resp.RequestMessage?.Method, resp.RequestMessage?.RequestUri, body);
        throw new MlServiceException((int)resp.StatusCode, body);
    }
}

public class MlServiceException : Exception
{
    public int StatusCode { get; }
    public string ResponseBody { get; }

    public MlServiceException(int statusCode, string responseBody)
        : base($"ml-service returned HTTP {statusCode}: {responseBody}")
    {
        StatusCode = statusCode;
        ResponseBody = responseBody;
    }

    public string? ExtractDetail()
    {
        try
        {
            using var doc = JsonDocument.Parse(ResponseBody);
            return doc.RootElement.TryGetProperty("detail", out var d) ? d.ToString() : null;
        }
        catch
        {
            return null;
        }
    }
}
