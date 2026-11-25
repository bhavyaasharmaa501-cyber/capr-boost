using System.Text.Json;
using Microsoft.AspNetCore.DataProtection;
using CaprApi.Models;

namespace CaprApi.Auth;

public record TokenPayload(int UserId, string Email, string Role, DateTimeOffset ExpiresAtUtc);

public class TokenService
{
    private const string Purpose = "CaprApi.AuthToken.v1";
    private readonly IDataProtector _protector;
    private readonly TimeSpan _lifetime;

    public TokenService(IDataProtectionProvider provider, IConfiguration config)
    {
        _protector = provider.CreateProtector(Purpose);
        _lifetime = TimeSpan.FromHours(config.GetValue("Auth:TokenLifetimeHours", 12.0));
    }

    public (string Token, DateTimeOffset ExpiresAtUtc) CreateToken(User user)
    {
        var expires = DateTimeOffset.UtcNow.Add(_lifetime);
        var payload = new TokenPayload(user.UserId, user.Email, user.Role, expires);
        var json = JsonSerializer.Serialize(payload);
        return (_protector.Protect(json), expires);
    }

    public TokenPayload? ValidateToken(string token)
    {
        try
        {
            var json = _protector.Unprotect(token);
            var payload = JsonSerializer.Deserialize<TokenPayload>(json);
            if (payload is null || payload.ExpiresAtUtc < DateTimeOffset.UtcNow)
                return null;
            return payload;
        }
        catch
        {
            return null;
        }
    }
}
