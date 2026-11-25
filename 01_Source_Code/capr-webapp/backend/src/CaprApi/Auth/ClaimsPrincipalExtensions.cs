using System.Security.Claims;

namespace CaprApi.Auth;

public static class ClaimsPrincipalExtensions
{
    public static int GetUserId(this ClaimsPrincipal user)
    {
        var raw = user.FindFirstValue(ClaimTypes.NameIdentifier);
        if (raw is null || !int.TryParse(raw, out var id))
            throw new InvalidOperationException("No valid NameIdentifier claim on the current principal");
        return id;
    }

    public static string GetEmail(this ClaimsPrincipal user) =>
        user.FindFirstValue(ClaimTypes.Email) ?? throw new InvalidOperationException("No Email claim");
}
