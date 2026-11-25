using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.DataProtection;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Data.SqlClient;
using CaprApi.Auth;
using CaprApi.Data;
using CaprApi.Data.Repositories;
using CaprApi.Hubs;
using CaprApi.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers().AddJsonOptions(o =>
{
    o.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter());
});

builder.Services.AddSignalR();

var keysPath = Path.Combine(builder.Environment.ContentRootPath,
    builder.Configuration["Storage:DataProtectionKeysPath"] ?? "App_Data/keys");
Directory.CreateDirectory(keysPath);
builder.Services.AddDataProtection()
    .SetApplicationName("CaprApi")
    .PersistKeysToFileSystem(new DirectoryInfo(keysPath));

builder.Services.AddSingleton<TokenService>();
builder.Services.AddSingleton<PasswordService>();
builder.Services
    .AddAuthentication(TokenAuthDefaults.SchemeName)
    .AddScheme<AuthenticationSchemeOptions, TokenAuthenticationHandler>(TokenAuthDefaults.SchemeName, _ => { });
builder.Services.AddAuthorization();

builder.Services.AddSingleton<IDbConnectionFactory, SqlConnectionFactory>();
builder.Services.AddScoped<IUserRepository, UserRepository>();
builder.Services.AddScoped<IModelVersionRepository, ModelVersionRepository>();
builder.Services.AddScoped<IPcapUploadRepository, PcapUploadRepository>();
builder.Services.AddScoped<IFlowRepository, FlowRepository>();
builder.Services.AddScoped<IPredictionRepository, PredictionRepository>();
builder.Services.AddScoped<IAlertRepository, AlertRepository>();
builder.Services.AddScoped<IExperimentRunRepository, ExperimentRunRepository>();
builder.Services.AddScoped<IPasswordResetRepository, PasswordResetRepository>();
builder.Services.AddScoped<IAuditRepository, AuditRepository>();

builder.Services.AddHttpClient<MlServiceClient>(client =>
{
    var baseUrl = builder.Configuration["MlService:BaseUrl"] ?? "http://localhost:8000";
    client.BaseAddress = new Uri(baseUrl);
    client.Timeout = TimeSpan.FromSeconds(builder.Configuration.GetValue("MlService:TimeoutSeconds", 60));
    var apiKey = builder.Configuration["MlService:ApiKey"];
    if (!string.IsNullOrEmpty(apiKey))
        client.DefaultRequestHeaders.Add("X-API-Key", apiKey);
});

builder.Services.AddScoped<AlertRulesService>();
builder.Services.AddScoped<ModelSyncService>();
builder.Services.AddScoped<UploadProcessingService>();
builder.Services.AddScoped<DbSeeder>();
builder.Services.AddSingleton<EmailService>();

var allowedOrigins = builder.Configuration.GetSection("Cors:AllowedOrigins").Get<string[]>()
    ?? new[] { "http://localhost:4200" };
builder.Services.AddCors(options =>
{
    options.AddPolicy("AngularClient", policy => policy
        .WithOrigins(allowedOrigins)
        .AllowAnyHeader()
        .AllowAnyMethod()
        .AllowCredentials());
});

builder.Services.Configure<ForwardedHeadersOptions>(o =>
{
    o.ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto;
    o.KnownNetworks.Clear();
    o.KnownProxies.Clear();
});

builder.Services.AddRateLimiter(o =>
{
    o.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    o.AddPolicy("auth", ctx => RateLimitPartition.GetFixedWindowLimiter(
        ctx.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = builder.Configuration.GetValue("RateLimit:AuthPerMinute", 30),
            Window = TimeSpan.FromMinutes(1),
            QueueLimit = 0,
        }));
});

builder.Services.Configure<FormOptions>(o => o.MultipartBodyLengthLimit = 200_000_000);
builder.WebHost.ConfigureKestrel(o => o.Limits.MaxRequestBodySize = 200_000_000);

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var seeder = scope.ServiceProvider.GetRequiredService<DbSeeder>();
    await seeder.SeedAsync();

    var modelSync = scope.ServiceProvider.GetRequiredService<ModelSyncService>();
    await modelSync.TrySyncAtStartupAsync();
}

app.UseForwardedHeaders();
app.UseRateLimiter();
app.UseCors("AngularClient");
app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();
app.MapHub<AlertsHub>("/hubs/alerts");
app.MapGet("/", () => Results.Ok(new { service = "capr-api", docs = "see backend/README.md" }));
app.MapGet("/health", async (IConfiguration config) =>
{
    try
    {
        await using var conn = new SqlConnection(config.GetConnectionString("CaprDb"));
        await conn.OpenAsync();
        return Results.Ok(new { status = "ok", database = "ok" });
    }
    catch (Exception ex)
    {
        return Results.Json(new { status = "unhealthy", database = ex.GetType().Name }, statusCode: 503);
    }
});

app.Run();
