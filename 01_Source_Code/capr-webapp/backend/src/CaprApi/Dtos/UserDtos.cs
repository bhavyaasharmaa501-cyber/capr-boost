namespace CaprApi.Dtos;

public record CreateUserRequest(string Email, string DisplayName, string Password, string Role);

public record UserDto(int UserId, string Email, string DisplayName, string Role, bool IsActive,
                       DateTime CreatedAtUtc, DateTime? LastLoginUtc)
{
    public static UserDto From(Models.User u) =>
        new(u.UserId, u.Email, u.DisplayName, u.Role, u.IsActive, u.CreatedAtUtc, u.LastLoginUtc);
}
