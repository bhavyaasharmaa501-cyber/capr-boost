using CaprApi.Dtos;

namespace CaprApi.Hubs;

public interface IAlertsClient
{
    Task NewAlert(AlertDto alert);
    Task UploadStatusChanged(UploadNotification notification);
    Task UploadCompleted(UploadNotification notification);
}
