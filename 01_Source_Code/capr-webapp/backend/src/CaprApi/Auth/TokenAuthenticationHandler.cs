using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;

namespace CaprApi.Auth;

public static class TokenAuthDefaults
{
    public const string SchemeName = "Token";
}

public class TokenAuthenticationHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    private readonly TokenService _tokenService;

    public TokenAuthenticationHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger,
        UrlEncoder encoder, TokenService tokenService)
        : base(options, logger, encoder)
    {
        _tokenService = tokenService;
    }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var token = ExtractToken();
        if (token is null)
            return Task.FromResult(AuthenticateResult.NoResult());
        if (token.Length == 0)
            return Task.FromResult(AuthenticateResult.Fail("Empty bearer token"));

        var payload = _tokenService.ValidateToken(token);
        if (payload is null)
            return Task.FromResult(AuthenticateResult.Fail("Invalid or expired token"));

        var claims = new[]
        {
            new Claim(ClaimTypes.NameIdentifier, payload.UserId.ToString()),
            new Claim(ClaimTypes.Email, payload.Email),
            new Claim(ClaimTypes.Role, payload.Role),
        };
        var identity = new ClaimsIdentity(claims, Scheme.Name);
        var principal = new ClaimsPrincipal(identity);
        var ticket = new AuthenticationTicket(principal, Scheme.Name);
        return Task.FromResult(AuthenticateResult.Success(ticket));
    }

    private string? ExtractToken()
    {
        if (Request.Headers.TryGetValue("Authorization", out var headerValues))
        {
            var header = headerValues.ToString();
            if (!string.IsNullOrWhiteSpace(header) &&
                header.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
                return header["Bearer ".Length..].Trim();
        }

        if (Request.Query.TryGetValue("access_token", out var queryToken) && queryToken.Count > 0)
            return queryToken.ToString();

        return null;
    }
}
