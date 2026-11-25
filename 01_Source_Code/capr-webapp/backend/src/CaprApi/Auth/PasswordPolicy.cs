namespace CaprApi.Auth;

public static class PasswordPolicy
{
    public const string Description = "at least 8 characters, with at least one letter and one digit";

    public static bool IsValid(string? password) =>
        !string.IsNullOrEmpty(password) && password.Length >= 8 &&
        password.Any(char.IsLetter) && password.Any(char.IsDigit);
}
