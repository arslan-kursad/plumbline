using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
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
    public void TheStubAuthenticatorIsRefusedOutsideDevelopment()
    {
        var options = Options(Environments.Production, ("PLUMBLINE_PUSH_AUTH", "stub"));

        var error = Assert.Throws<InvalidOperationException>(() => options.CreateAuthenticator());
        Assert.Contains("outside a Development environment", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void TheStubAuthenticatorIsAvailableInDevelopment()
    {
        var options = Options(Environments.Development, ("PLUMBLINE_PUSH_AUTH", "stub"));

        Assert.IsType<StubPushAuthenticator>(options.CreateAuthenticator());
    }

    [Fact]
    public void TheDefaultIsOidcAndOidcCurrentlyRefusesEverything()
    {
        // OIDC validation is F2 work. Until it exists the endpoint fails closed rather
        // than falling back to something permissive, so an incomplete deployment is
        // visibly broken instead of quietly open (architecture §6.1).
        var authenticator = Options(Environments.Production).CreateAuthenticator();

        Assert.IsType<UnimplementedOidcAuthenticator>(authenticator);
        Assert.Contains("not implemented", authenticator.Description, StringComparison.Ordinal);
    }

    [Fact]
    public void AnUnknownMechanismIsAStartupFailure()
    {
        var options = Options(Environments.Development, ("PLUMBLINE_PUSH_AUTH", "none"));

        Assert.Throws<InvalidOperationException>(() => options.CreateAuthenticator());
    }

    [Fact]
    public async Task TheBigQuerySinkIsWiringOnlyAndSaysSoLoudly()
    {
        var sink = Options(Environments.Production, ("PLUMBLINE_SINK", "bigquery"),
            ("PLUMBLINE_BQ_PROJECT", "plumbline-prod")).CreateSink();

        Assert.IsType<BigQueryStorageWriteSink>(sink);
        Assert.Contains("storage write api", sink.Description, StringComparison.Ordinal);

        var error = await Assert.ThrowsAsync<NotSupportedException>(() =>
            sink.WriteAsync(Array.Empty<Normalization.Rows.SpanRow>(), CancellationToken.None));
        Assert.Contains("wiring only in F1", error.Message, StringComparison.Ordinal);
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
