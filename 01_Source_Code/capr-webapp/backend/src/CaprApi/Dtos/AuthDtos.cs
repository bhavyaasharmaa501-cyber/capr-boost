namespace CaprApi.Dtos;

public record LoginRequest(string Email, string Password);

public record LoginResponse(string Token, DateTimeOffset ExpiresAtUtc, UserSummary User);

public record UserSummary(int UserId, string Email, string DisplayName, string Role)
{
    public static UserSummary From(Models.User u) => new(u.UserId, u.Email, u.DisplayName, u.Role);
}

public record ForgotPasswordRequest(string Email);

public record ForgotPasswordResponse(string Message, bool EmailSent, string? DemoCode, int ExpiresInMinutes);

public record ResetPasswordRequest(string Email, string Code, string NewPassword);

public record ChangePasswordRequest(string CurrentPassword, string NewPassword);
