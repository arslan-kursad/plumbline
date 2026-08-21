using Plumbline.Worker.Push;
using Plumbline.Worker.Sinks;

namespace Plumbline.Worker;

/// <summary>Configuration, read from the environment.</summary>
/// <remarks>
/// The two settings that decide what this process is — how push requests are
/// authenticated and where rows go — are explicit and have no accidental default. A
/// worker that silently picked the stub authenticator or a sink that swallows rows would
/// look identical to a working one.
/// </remarks>
public sealed record WorkerOptions
{
    public required string PushPath { get; init; }

    public required string PushAuthentication { get; init; }

    public required string Sink { get; init; }

    public string? LocalSinkDirectory { get; init; }

    public string? BigQueryProject { get; init; }

    public string? BigQueryDataset { get; init; }

    public string? BigQueryTable { get; init; }

    /// <summary>
    /// Host:port of a local BigQuery stand-in's gRPC endpoint, or null for the real
    /// service. The only place in the write path that knows a stand-in can exist.
    /// </summary>
    public string? BigQueryEmulatorEndpoint { get; init; }

    public required bool AllowStubAuthentication { get; init; }

    public static WorkerOptions FromConfiguration(IConfiguration configuration, IHostEnvironment environment)
    {
        return new WorkerOptions
        {
            PushPath = configuration["PLUMBLINE_PUSH_PATH"] ?? "/push",
            PushAuthentication = configuration["PLUMBLINE_PUSH_AUTH"] ?? "oidc",
            Sink = configuration["PLUMBLINE_SINK"] ?? "bigquery",
            LocalSinkDirectory = configuration["PLUMBLINE_LOCAL_SINK_DIR"],
            BigQueryProject = configuration["PLUMBLINE_BQ_PROJECT"],
            BigQueryDataset = configuration["PLUMBLINE_BQ_DATASET"],
            BigQueryTable = configuration["PLUMBLINE_BQ_TABLE"],
            BigQueryEmulatorEndpoint = configuration["PLUMBLINE_BQ_EMULATOR"],

            // The stub is available only where a human has said the environment is
            // development. Cloud Run sets no ASPNETCORE_ENVIRONMENT, so the default is
            // Production and the guard bites by default rather than by configuration.
            AllowStubAuthentication = environment.IsDevelopment(),
        };
    }

    public IPushAuthenticator CreateAuthenticator() => PushAuthentication.ToLowerInvariant() switch
    {
        "stub" when AllowStubAuthentication => new StubPushAuthenticator(),
        "stub" => throw new InvalidOperationException(
            "PLUMBLINE_PUSH_AUTH=stub outside a Development environment. The stub accepts every request, and " +
            "the push endpoint's only protection is the caller's identity (architecture §6.1). Set " +
            "ASPNETCORE_ENVIRONMENT=Development for local runs, or implement OIDC validation (F2)."),
        "oidc" => new UnimplementedOidcAuthenticator(),
        var other => throw new InvalidOperationException($"PLUMBLINE_PUSH_AUTH={other} is not a known mechanism"),
    };

    public ISpanSink CreateSink() => Sink.ToLowerInvariant() switch
    {
        "local" => new LocalJsonSink(LocalSinkDirectory
                                     ?? throw new InvalidOperationException("PLUMBLINE_SINK=local needs PLUMBLINE_LOCAL_SINK_DIR")),
        "bigquery" => new BigQueryStorageWriteSink(
            BigQueryProject ?? throw new InvalidOperationException("PLUMBLINE_SINK=bigquery needs PLUMBLINE_BQ_PROJECT"),
            BigQueryDataset ?? "plumbline",
            BigQueryTable ?? "spans",
            BigQueryEmulatorEndpoint),
        var other => throw new InvalidOperationException($"PLUMBLINE_SINK={other} is not a known sink"),
    };
}
