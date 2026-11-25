SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF DB_ID('CaprDb') IS NULL
BEGIN
    PRINT 'Creating database CaprDb ...';
    CREATE DATABASE CaprDb;
END
GO
USE CaprDb;
GO

IF OBJECT_ID('dbo.Users', 'U') IS NULL
CREATE TABLE dbo.Users (
    UserId          INT IDENTITY(1,1) PRIMARY KEY,
    Email           NVARCHAR(256)   NOT NULL,
    DisplayName     NVARCHAR(200)   NOT NULL,
    PasswordHash    NVARCHAR(500)   NOT NULL,
    Role            NVARCHAR(50)    NOT NULL DEFAULT 'Analyst',
    IsActive        BIT             NOT NULL DEFAULT 1,
    CreatedAtUtc    DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    LastLoginUtc    DATETIME2       NULL,
    PasswordChangedAtUtc DATETIME2  NULL,
    CONSTRAINT UQ_Users_Email UNIQUE (Email)
);
GO

IF OBJECT_ID('dbo.ModelVersions', 'U') IS NULL
CREATE TABLE dbo.ModelVersions (
    ModelVersionId  INT IDENTITY(1,1) PRIMARY KEY,
    DatasetName     NVARCHAR(100)   NOT NULL,
    MethodName      NVARCHAR(100)   NOT NULL,
    LabelRatio      FLOAT           NOT NULL,
    ArtifactPath    NVARCHAR(500)   NOT NULL,
    FeatureNamesJson NVARCHAR(MAX)  NOT NULL,
    TestF1          FLOAT           NULL,
    TestAucPr       FLOAT           NULL,
    TestAucRoc      FLOAT           NULL,
    TestFpr         FLOAT           NULL,
    TestAccuracy    FLOAT           NULL,
    TestPrecision   FLOAT           NULL,
    TestRecall      FLOAT           NULL,
    EnsembleSize    INT             NOT NULL DEFAULT 1,
    IsActive        BIT             NOT NULL DEFAULT 0,
    RegisteredAtUtc DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    Notes           NVARCHAR(1000)  NULL
);
GO

IF OBJECT_ID('dbo.PcapUploads', 'U') IS NULL
CREATE TABLE dbo.PcapUploads (
    PcapUploadId    INT IDENTITY(1,1) PRIMARY KEY,
    UserId          INT             NOT NULL REFERENCES dbo.Users(UserId),
    OriginalFileName NVARCHAR(400)  NOT NULL,
    StoredPath      NVARCHAR(500)   NOT NULL,
    FileSizeBytes   BIGINT          NOT NULL,
    Status          NVARCHAR(30)    NOT NULL DEFAULT 'Pending',
    ErrorMessage    NVARCHAR(2000)  NULL,
    ModelVersionId  INT             NULL REFERENCES dbo.ModelVersions(ModelVersionId),
    FlowCount       INT             NULL,
    AnomalyCount    INT             NULL,
    UploadedAtUtc   DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CompletedAtUtc  DATETIME2       NULL
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_PcapUploads_User')
CREATE INDEX IX_PcapUploads_User ON dbo.PcapUploads(UserId, UploadedAtUtc DESC);
GO

IF OBJECT_ID('dbo.Flows', 'U') IS NULL
CREATE TABLE dbo.Flows (
    FlowId          BIGINT IDENTITY(1,1) PRIMARY KEY,
    PcapUploadId    INT             NULL REFERENCES dbo.PcapUploads(PcapUploadId),
    SrcIp           VARCHAR(45)     NULL,
    DstIp           VARCHAR(45)     NULL,
    SrcPort         INT             NULL,
    DstPort         INT             NULL,
    Protocol        TINYINT         NULL,
    FlowStartUtc    DATETIME2       NULL,
    DurationMs      FLOAT           NULL,
    FeaturesJson    NVARCHAR(MAX)   NOT NULL,
    CreatedAtUtc    DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Flows_Upload')
CREATE INDEX IX_Flows_Upload ON dbo.Flows(PcapUploadId);
GO

IF OBJECT_ID('dbo.Predictions', 'U') IS NULL
CREATE TABLE dbo.Predictions (
    PredictionId    BIGINT IDENTITY(1,1) PRIMARY KEY,
    FlowId          BIGINT          NOT NULL REFERENCES dbo.Flows(FlowId),
    ModelVersionId  INT             NOT NULL REFERENCES dbo.ModelVersions(ModelVersionId),
    AnomalyProbability FLOAT        NOT NULL,
    Uncertainty     FLOAT           NULL,
    IsAnomaly       BIT             NOT NULL,
    Threshold       FLOAT           NOT NULL DEFAULT 0.5,
    TopFeaturesJson NVARCHAR(MAX)   NULL,
    ScoredAtUtc     DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    InferenceMs     FLOAT           NULL
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Predictions_Flow')
CREATE INDEX IX_Predictions_Flow ON dbo.Predictions(FlowId);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Predictions_Anomaly')
CREATE INDEX IX_Predictions_Anomaly ON dbo.Predictions(IsAnomaly, ScoredAtUtc DESC) INCLUDE (AnomalyProbability);
GO

IF OBJECT_ID('dbo.Alerts', 'U') IS NULL
CREATE TABLE dbo.Alerts (
    AlertId         BIGINT IDENTITY(1,1) PRIMARY KEY,
    PredictionId    BIGINT          NOT NULL REFERENCES dbo.Predictions(PredictionId),
    Severity        NVARCHAR(20)    NOT NULL,
    Title           NVARCHAR(300)   NOT NULL,
    Description     NVARCHAR(2000)  NULL,
    Status          NVARCHAR(20)    NOT NULL DEFAULT 'Open',
    AcknowledgedBy  INT             NULL REFERENCES dbo.Users(UserId),
    AcknowledgedAtUtc DATETIME2     NULL,
    CreatedAtUtc    DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Alerts_Status')
CREATE INDEX IX_Alerts_Status ON dbo.Alerts(Status, CreatedAtUtc DESC);
GO

IF OBJECT_ID('dbo.ExperimentRuns', 'U') IS NULL
CREATE TABLE dbo.ExperimentRuns (
    ExperimentRunId INT IDENTITY(1,1) PRIMARY KEY,
    DatasetName     NVARCHAR(100)   NOT NULL,
    MethodName      NVARCHAR(100)   NOT NULL,
    LabelRatio      FLOAT           NOT NULL,
    NoiseRate       FLOAT           NOT NULL,
    Seed            INT             NOT NULL,
    Accuracy        FLOAT           NULL,
    F1              FLOAT           NOT NULL,
    AucRoc          FLOAT           NOT NULL,
    AucPr           FLOAT           NOT NULL,
    Precision_      FLOAT           NOT NULL,
    Recall_         FLOAT           NOT NULL,
    Fpr             FLOAT           NOT NULL,
    Mcc             FLOAT           NULL,
    FitTimeSeconds  FLOAT           NULL,
    ImportedAtUtc   DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_ExperimentRuns UNIQUE (DatasetName, MethodName, LabelRatio, NoiseRate, Seed)
);
GO

IF OBJECT_ID('dbo.PasswordResetTokens', 'U') IS NULL
CREATE TABLE dbo.PasswordResetTokens (
    ResetTokenId    INT IDENTITY(1,1) PRIMARY KEY,
    UserId          INT             NOT NULL REFERENCES dbo.Users(UserId),
    CodeHash        NVARCHAR(128)   NOT NULL,
    ExpiresAtUtc    DATETIME2       NOT NULL,
    UsedAtUtc       DATETIME2       NULL,
    Attempts        INT             NOT NULL DEFAULT 0,
    RequestIp       NVARCHAR(64)    NULL,
    CreatedAtUtc    DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_PasswordResetTokens_User')
CREATE INDEX IX_PasswordResetTokens_User ON dbo.PasswordResetTokens(UserId, CreatedAtUtc DESC);
GO

IF OBJECT_ID('dbo.AuditEvents', 'U') IS NULL
CREATE TABLE dbo.AuditEvents (
    AuditEventId    BIGINT IDENTITY(1,1) PRIMARY KEY,
    UserId          INT             NULL REFERENCES dbo.Users(UserId),
    EventType       NVARCHAR(50)    NOT NULL,
    Details         NVARCHAR(1000)  NULL,
    IpAddress       NVARCHAR(64)    NULL,
    CreatedAtUtc    DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_AuditEvents_Created')
CREATE INDEX IX_AuditEvents_Created ON dbo.AuditEvents(CreatedAtUtc DESC);
GO

IF COL_LENGTH('dbo.Users', 'PasswordChangedAtUtc') IS NULL
    ALTER TABLE dbo.Users ADD PasswordChangedAtUtc DATETIME2 NULL;
IF COL_LENGTH('dbo.ModelVersions', 'TestAccuracy') IS NULL
    ALTER TABLE dbo.ModelVersions ADD TestAccuracy FLOAT NULL, TestPrecision FLOAT NULL,
        TestRecall FLOAT NULL, EnsembleSize INT NOT NULL CONSTRAINT DF_ModelVersions_Ensemble DEFAULT 1;
IF COL_LENGTH('dbo.ExperimentRuns', 'Accuracy') IS NULL
    ALTER TABLE dbo.ExperimentRuns ADD Accuracy FLOAT NULL;
GO

CREATE OR ALTER VIEW dbo.vw_ModelLeaderboard AS
SELECT DatasetName, MethodName, LabelRatio, NoiseRate, COUNT(*) AS NumSeeds,
       AVG(Accuracy) AS AccuracyMean, AVG(F1) AS F1Mean, STDEV(F1) AS F1Std,
       AVG(AucRoc) AS AucRocMean, AVG(Fpr) AS FprMean
FROM dbo.ExperimentRuns
GROUP BY DatasetName, MethodName, LabelRatio, NoiseRate;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Users)
INSERT INTO dbo.Users (Email, DisplayName, PasswordHash, Role)
VALUES ('admin@capr.local', 'Admin', '__SET_BY_API_ON_FIRST_RUN__', 'Admin');
GO

PRINT 'CaprDb schema created/verified successfully.';
GO
