using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using CaprApi.Auth;
using CaprApi.Data.Repositories;
using CaprApi.Dtos;
using CaprApi.Models;

namespace CaprApi.Controllers;

[ApiController]
[Route("api/users")]
[Authorize(Roles = Roles.Admin)]
public class UsersController : ControllerBase
{
    private static readonly string[] ValidRoles = { Roles.Admin, Roles.Analyst, Roles.Viewer };

    private readonly IUserRepository _users;
    private readonly PasswordService _passwords;

    public UsersController(IUserRepository users, PasswordService passwords)
    {
        _users = users;
        _passwords = passwords;
    }

    [HttpGet]
    public async Task<ActionResult<List<UserDto>>> GetAll(CancellationToken ct)
    {
        var users = await _users.GetAllAsync(ct);
        return Ok(users.Select(UserDto.From).ToList());
    }

    [HttpPost]
    public async Task<ActionResult<UserDto>> Create(CreateUserRequest request, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.DisplayName) ||
            string.IsNullOrWhiteSpace(request.Password))
            return BadRequest(new { detail = "Email, displayName and password are all required" });
        if (request.Password.Length < 8)
            return BadRequest(new { detail = "Password must be at least 8 characters" });
        if (!ValidRoles.Contains(request.Role))
            return BadRequest(new { detail = $"Role must be one of: {string.Join(", ", ValidRoles)}" });

        var email = request.Email.Trim().ToLowerInvariant();
        if (await _users.GetByEmailAsync(email, ct) is not null)
            return Conflict(new { detail = $"A user with email '{email}' already exists" });

        var user = new User { Email = email, DisplayName = request.DisplayName.Trim(), Role = request.Role };
        user.PasswordHash = _passwords.Hash(user, request.Password);
        user.UserId = await _users.CreateAsync(user, ct);

        return CreatedAtAction(nameof(GetAll), UserDto.From(user));
    }
}
