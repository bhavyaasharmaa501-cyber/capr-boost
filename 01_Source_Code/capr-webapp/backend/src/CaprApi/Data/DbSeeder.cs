using System.Security.Cryptography;
using System.Text;
using CaprApi.Auth;
using CaprApi.Data.Repositories;

namespace CaprApi.Data;

public class DbSeeder
{
    private const string SentinelHash = "__SET_BY_API_ON_FIRST_RUN__";

    private readonly IUserRepository _users;
    private readonly PasswordService _passwords;
    private readonly IConfiguration _config;
    private readonly ILogger<DbSeeder> _log;

    public DbSeeder(IUserRepository users, PasswordService passwords, IConfiguration config, ILogger<DbSeeder> log)
    {
        _users = users;
        _passwords = passwords;
        _config = config;
        _log = log;
    }

    public async Task SeedAsync(CancellationToken ct = default)
    {
        var email = _config["AdminSeed:Email"] ?? "admin@capr.local";
        Models.User? admin;
        try
        {
            admin = await _users.GetByEmailAsync(email, ct);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex,
                "Could not reach dbo.Users during startup seeding. Has database/schema.sql been " +
                "run against the database in ConnectionStrings:CaprDb yet? The API will still " +
                "start, but every DB-backed endpoint will fail until the schema exists.");
            return;
        }

        if (admin is null)
        {
            _log.LogWarning(
                "No user found for {Email} (the schema.sql seed row) -- run database/schema.sql " +
                "against the target database, then restart the API.", email);
            return;
        }

        if (admin.PasswordHash != SentinelHash)
            return;

        var configuredPassword = _config["AdminSeed:Password"];
        var generated = string.IsNullOrWhiteSpace(configuredPassword);
        var password = generated ? GenerateRandomPassword() : configuredPassword!;

        var hash = _passwords.Hash(admin, password);
        await _users.UpdatePasswordHashAsync(admin.UserId, hash, ct);

        if (generated)
        {
            _log.LogWarning(
                "First run: generated a password for the seeded admin account. " +
                "Email: {Email}  Password: {Password}  " +
                "Log in once and change it, or set AdminSeed:Password before first run next time " +
                "to choose your own instead of a generated one.", email, password);
        }
        else
        {
            _log.LogInformation("Set the seeded admin's password from AdminSeed:Password config for {Email}.", email);
        }
    }

    private static string GenerateRandomPassword(int length = 20)
    {
        const string alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
        var bytes = RandomNumberGenerator.GetBytes(length);
        var sb = new StringBuilder(length);
        foreach (var b in bytes)
            sb.Append(alphabet[b % alphabet.Length]);
        return sb.ToString();
    }
}
