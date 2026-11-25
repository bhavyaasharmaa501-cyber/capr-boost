# Backend API (ASP.NET Core 8)

```bash
cd src/CaprApi
dotnet run
```

Configuration (appsettings.json or environment variables):

| Key | Meaning |
|---|---|
| `ConnectionStrings:CaprDb` | SQL Server connection string |
| `MlService:BaseUrl`, `MlService:ApiKey` | location and shared key of the ML service |
| `AdminSeed:Email`, `AdminSeed:Password` | first admin account |
| `Smtp:*` | mail server used for password-reset codes |
| `Auth:ShowResetCodeWithoutSmtp` | show the reset code on screen when SMTP is not configured |

Main endpoints: `/api/auth/login`, `/api/auth/forgot-password`, `/api/auth/reset-password`,
`/api/auth/change-password`, `/api/uploads/csv`, `/api/uploads/pcap`, `/api/alerts`,
`/api/models`, `/api/experiments`, `/api/dashboard/summary`, `/api/users`; SignalR hub `/hubs/alerts`.
