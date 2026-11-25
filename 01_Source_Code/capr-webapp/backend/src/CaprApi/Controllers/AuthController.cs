using Microsoft.AspNetCore.RateLimiting;
using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CaprApi.Auth;
using CaprApi.Data.Repositories;
using CaprApi.Dtos;
using CaprApi.Services;

namespace CaprApi.Controllers;

[ApiController]
[Route("api/auth")]
[EnableRateLimiting("auth")]
public class AuthController : ControllerBase
{
    private const int CodeLifetimeMinutes = 15;
    private const int MaxAttempts = 5;
    private const int MaxRequestsPerWindow = 3;

    private readonly IUserRepository _users;
    private readonly IPasswordResetRepository _resets;
    private readonly IAuditRepository _audit;
    private readonly PasswordService _passwords;
    private readonly TokenService _tokens;
    private readonly EmailService _email;
    private readonly IConfiguration _config;
    private readonly ILogger<AuthController> _log;

    public AuthController(IUserRepository users, IPasswordResetRepository resets, IAuditRepository audit,
        PasswordService passwords, TokenService tokens, EmailService email, IConfiguration config,
        ILogger<AuthController> log)
    {
        _users = users;
        _resets = resets;
        _audit = audit;
        _passwords = passwords;
        _tokens = tokens;
        _email = email;
        _config = config;
        _log = log;
    }

    private string? ClientIp => HttpContext.Connection.RemoteIpAddress?.ToString();

    [HttpPost("login")]
    [AllowAnonymous]
    public async Task<ActionResult<LoginResponse>> Login(LoginRequest request, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password))
            return BadRequest(new { detail = "Email and password are required" });

        var user = await _users.GetByEmailAsync(request.Email.Trim().ToLowerInvariant(), ct);
        if (user is null || !user.IsActive || !_passwords.Verify(user, request.Password))
        {
            await _audit.LogAsync(user?.UserId, "LoginFailed", request.Email.Trim(), ClientIp, ct);
            return Unauthorized(new { detail = "Invalid email or password" });
        }

        var (token, expiresAtUtc) = _tokens.CreateToken(user);
        await _users.UpdateLastLoginAsync(user.UserId, ct);
        await _audit.LogAsync(user.UserId, "Login", null, ClientIp, ct);
        return Ok(new LoginResponse(token, expiresAtUtc, UserSummary.From(user)));
    }

    [HttpGet("me")]
    [Authorize]
    public async Task<ActionResult<UserDto>> Me(CancellationToken ct)
    {
        var user = await _users.GetByIdAsync(User.GetUserId(), ct);
        if (user is null)
            return Unauthorized(new { detail = "User no longer exists" });
        return Ok(UserDto.From(user));
    }

    [HttpPost("forgot-password")]
    [AllowAnonymous]
    public async Task<ActionResult<ForgotPasswordResponse>> ForgotPassword(ForgotPasswordRequest request, CancellationToken ct)
    {
        const string generic = "If an account exists for this email, a 6-digit reset code has been issued.";
        if (string.IsNullOrWhiteSpace(request.Email))
            return BadRequest(new { detail = "Email is required" });

        var email = request.Email.Trim().ToLowerInvariant();
        var user = await _users.GetByEmailAsync(email, ct);
        if (user is null || !user.IsActive)
            return Ok(new ForgotPasswordResponse(generic, false, null, CodeLifetimeMinutes));

        if (await _resets.CountRecentAsync(user.UserId, TimeSpan.FromMinutes(CodeLifetimeMinutes), ct) >= MaxRequestsPerWindow)
            return StatusCode(429, new { detail = "Too many reset requests. Please wait 15 minutes and try again." });

        var code = RandomNumberGenerator.GetInt32(0, 1_000_000).ToString("D6");
        await _resets.CreateAsync(user.UserId, HashCode(user.UserId, code),
            DateTime.UtcNow.AddMinutes(CodeLifetimeMinutes), ClientIp, ct);
        await _audit.LogAsync(user.UserId, "PasswordResetRequested", null, ClientIp, ct);

        var body = $"Hello {user.DisplayName},\n\nYour CAPR-Net password reset code is {code}.\n" +
                   $"It expires in {CodeLifetimeMinutes} minutes. If you did not request this, ignore this email.";
        var sent = await _email.SendAsync(user.Email, "CAPR-Net password reset code", body, ct);

        string? demoCode = null;
        if (!sent && _config.GetValue("Auth:ShowResetCodeWithoutSmtp", false))
        {
            demoCode = code;
            _log.LogWarning("SMTP not configured: reset code for {Email} is {Code}", user.Email, code);
        }
        return Ok(new ForgotPasswordResponse(generic, sent, demoCode, CodeLifetimeMinutes));
    }

    [HttpPost("reset-password")]
    [AllowAnonymous]
    public async Task<IActionResult> ResetPassword(ResetPasswordRequest request, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Code))
            return BadRequest(new { detail = "Email and reset code are required" });
        if (!PasswordPolicy.IsValid(request.NewPassword))
            return BadRequest(new { detail = $"Password must be {PasswordPolicy.Description}" });

        var user = await _users.GetByEmailAsync(request.Email.Trim().ToLowerInvariant(), ct);
        var token = user is null ? null : await _resets.GetLatestActiveAsync(user.UserId, ct);
        if (user is null || token is null || token.Attempts >= MaxAttempts)
            return BadRequest(new { detail = "The reset code is invalid or has expired. Request a new one." });

        var expected = Convert.FromHexString(token.CodeHash);
        var actual = Convert.FromHexString(HashCode(user.UserId, request.Code.Trim()));
        if (!CryptographicOperations.FixedTimeEquals(expected, actual))
        {
            await _resets.IncrementAttemptsAsync(token.ResetTokenId, ct);
            var left = MaxAttempts - token.Attempts - 1;
            return BadRequest(new { detail = left > 0
                ? $"Incorrect code. {left} attempt(s) left."
                : "Too many incorrect attempts. Request a new code." });
        }

        await _users.UpdatePasswordHashAsync(user.UserId, _passwords.Hash(user, request.NewPassword), ct);
        await _resets.MarkUsedAsync(user.UserId, ct);
        await _audit.LogAsync(user.UserId, "PasswordReset", null, ClientIp, ct);
        return Ok(new { message = "Password updated. You can now sign in with the new password." });
    }

    [HttpPost("change-password")]
    [Authorize]
    public async Task<IActionResult> ChangePassword(ChangePasswordRequest request, CancellationToken ct)
    {
        var user = await _users.GetByIdAsync(User.GetUserId(), ct);
        if (user is null)
            return Unauthorized(new { detail = "User no longer exists" });
        if (!_passwords.Verify(user, request.CurrentPassword ?? ""))
            return BadRequest(new { detail = "Current password is incorrect" });
        if (!PasswordPolicy.IsValid(request.NewPassword))
            return BadRequest(new { detail = $"Password must be {PasswordPolicy.Description}" });

        await _users.UpdatePasswordHashAsync(user.UserId, _passwords.Hash(user, request.NewPassword), ct);
        await _audit.LogAsync(user.UserId, "PasswordChanged", null, ClientIp, ct);
        return Ok(new { message = "Password changed successfully." });
    }

    private static string HashCode(int userId, string code) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes($"{userId}:{code}")));
}
