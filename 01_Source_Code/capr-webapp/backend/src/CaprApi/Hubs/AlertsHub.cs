using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.SignalR;

namespace CaprApi.Hubs;

[Authorize]
public class AlertsHub : Hub<IAlertsClient>
{
}
