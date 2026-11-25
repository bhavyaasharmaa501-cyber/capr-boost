using System.Net;
using System.Net.Mail;

namespace CaprApi.Services;

public class EmailService
{
    private readonly IConfiguration _config;
    private readonly ILogger<EmailService> _log;

    public EmailService(IConfiguration config, ILogger<EmailService> log)
    {
        _config = config;
        _log = log;
    }

    public bool IsConfigured => !string.IsNullOrWhiteSpace(_config["Smtp:Host"]);

    public async Task<bool> SendAsync(string to, string subject, string body, CancellationToken ct = default)
    {
        if (!IsConfigured)
            return false;
        try
        {
            using var client = new SmtpClient(_config["Smtp:Host"], _config.GetValue("Smtp:Port", 587))
            {
                EnableSsl = _config.GetValue("Smtp:EnableSsl", true),
                Credentials = new NetworkCredential(_config["Smtp:User"], _config["Smtp:Password"]),
            };
            var from = _config["Smtp:From"] ?? _config["Smtp:User"] ?? "no-reply@capr.local";
            using var msg = new MailMessage(from, to, subject, body);
            await client.SendMailAsync(msg, ct);
            return true;
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Failed to send email to {To}", to);
            return false;
        }
    }
}
