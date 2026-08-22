using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging.Abstractions;
using Plumbline.Worker;
using Plumbline.Worker.Push;
using Plumbline.Worker.Sinks;

namespace Plumbline.Worker.Tests;

/// <summary>
/// The two settings that decide what this process is: how push requests are
/// authenticated, and where rows go.
/// </summary>
/// <remarks>
/// Both have failure modes that look like success. A stub authenticator in the cloud
/// serves traffic happily while accepting anyone; a sink that quietly does nothing looks
/// exactly like a working pipeline with no traffic. These tests are about the guards
/// against those two, which is why they exist rather than because configuration parsing
/// is interesting.
/// </remarks>
public class WorkerOptionsTests
{
    private static WorkerOptions Options(string environmentName, params (string Key, string Value)[] settings)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(settings.Select(s => new KeyValuePair<string, string?>(s.Key, s.Value)))
            .Build();

        return WorkerOptions.FromConfiguration(configuration, new StubEnvironment(environmentName));
    }

    [Fact]
    public void UnauthenticatedPushIsRefusedOutsideDevelopment()
    {
        var options = Options(Environments.Production, ("PLUMBLINE_PUSH_AUTH", "none"));

        var error = Assert.Throws<InvalidOperationException>(() => options.CreateAuthenticator(NullLoggerFactory.Instance));
        Assert.Contains("outside a Development environment", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void UnauthenticatedPushIsAvailableInDevelopment()
    {
        var options = Options(Environments.Development, ("PLUMBLINE_PUSH_AUTH", "none"));

        Assert.IsType<AcceptAllPushAuthenticator>(options.CreateAuthenticator(NullLoggerFactory.Instance));
    }

    [Fact]
    public void TheDefaultIsOidcAndItNamesItsAudienceAndCaller()
    {
        var authenticator = Options(Environments.Production,
            ("PLUMBLINE_PUSH_OIDC_AUDIENCE", "plumbline-ingestion-worker"),
            ("PLUMBLINE_PUSH_OIDC_SERVICE_ACCOUNT", "pubsub-push@plumbline-prod.iam.gserviceaccount.com"))
            .CreateAuthenticator(NullLoggerFactory.Instance);

        Assert.IsType<OidcPushAuthenticator>(authenticator);

        // The description reaches the startup log and /healthz: which audience this
        // deployment expects and which identity it will accept are the two facts a
        // silently undelivered subscription gets debugged with.
        Assert.Contains("plumbline-ingestion-worker", authenticator.Description, StringComparison.Ordinal);
        Assert.Contains("pubsub-push@plumbline-prod.iam.gserviceaccount.com", authenticator.Description, StringComparison.Ordinal);
    }

    [Fact]
    public void OidcWithoutItsSettingsIsAStartupFailure()
    {
        // Fail at startup, not at the first push: a worker that boots and then refuses
        // every delivery looks healthy while the subscription exhausts its attempts.
        Assert.Throws<InvalidOperationException>(() => Options(Environments.Production,
                ("PLUMBLINE_PUSH_OIDC_SERVICE_ACCOUNT", "pubsub-push@plumbline-prod.iam.gserviceaccount.com"))
            .CreateAuthenticator(NullLoggerFactory.Instance));
        Assert.Throws<InvalidOperationException>(() => Options(Environments.Production,
                ("PLUMBLINE_PUSH_OIDC_AUDIENCE", "plumbline-ingestion-worker"))
            .CreateAuthenticator(NullLoggerFactory.Instance));
    }

    [Fact]
    public void TheRemovedStubMechanismNamesItsReplacement()
    {
        // A checkout or a runbook from F1 may still say stub; the error should say what
        // to use now rather than "unknown mechanism".
        var error = Assert.Throws<InvalidOperationException>(() =>
            Options(Environments.Development, ("PLUMBLINE_PUSH_AUTH", "stub")).CreateAuthenticator(NullLoggerFactory.Instance));
        Assert.Contains("removed in F2", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void AnUnknownMechanismIsAStartupFailure()
    {
        var options = Options(Environments.Development, ("PLUMBLINE_PUSH_AUTH", "basic"));

        Assert.Throws<InvalidOperationException>(() => options.CreateAuthenticator(NullLoggerFactory.Instance));
    }

    [Fact]
    public void TheBigQuerySinkNamesItsDestinationAndItsStream()
    {
        var sink = Options(Environments.Production, ("PLUMBLINE_SINK", "bigquery"),
            ("PLUMBLINE_BQ_PROJECT", "plumbline-prod")).CreateSink();

        Assert.IsType<BigQueryStorageWriteSink>(sink);

        // The description reaches the startup log and /healthz. It names the write path
        // because "which API is this worker using" is a cost invariant, not a detail.
        Assert.Equal("bigquery storage write api (plumbline-prod.plumbline.spans, default stream)", sink.Description);
    }

    [Fact]
    public void ASinkWithNoDestinationIsAStartupFailure()
    {
        Assert.Throws<InvalidOperationException>(() =>
            Options(Environments.Development, ("PLUMBLINE_SINK", "local")).CreateSink());
        Assert.Throws<InvalidOperationException>(() =>
            Options(Environments.Production, ("PLUMBLINE_SINK", "bigquery")).CreateSink());
    }

    private sealed class StubEnvironment : IHostEnvironment
    {
        public StubEnvironment(string environmentName)
        {
            EnvironmentName = environmentName;
        }

        public string EnvironmentName { get; set; }
        public string ApplicationName { get; set; } = "Plumbline.Worker.Tests";
        public string ContentRootPath { get; set; } = AppContext.BaseDirectory;
        public Microsoft.Extensions.FileProviders.IFileProvider ContentRootFileProvider { get; set; } =
            new Microsoft.Extensions.FileProviders.NullFileProvider();
    }
}
