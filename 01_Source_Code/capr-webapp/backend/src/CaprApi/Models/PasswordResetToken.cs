namespace CaprApi.Models;

public class PasswordResetToken
{
    public int ResetTokenId { get; set; }
    public int UserId { get; set; }
    public string CodeHash { get; set; } = "";
    public DateTime ExpiresAtUtc { get; set; }
    public DateTime? UsedAtUtc { get; set; }
    public int Attempts { get; set; }
    public DateTime CreatedAtUtc { get; set; }
}
