using System.IO.Compression;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Hosting;

namespace Plumbline.Worker.Tests;

/// <summary>
/// The push endpoint, driven through the real host.
/// </summary>
/// <remarks>
/// The status code is the acknowledgement — Pub/Sub ACKs on 2xx and NACKs on anything
/// else — so these tests are about one question: does this message deserve to be
/// forgotten or redelivered? Getting that wrong in the generous direction is how a poison
/// message never reaches the dead-letter topic and no alert ever fires.
/// </remarks>
public class IngestionEndpointTests : IClassFixture<WorkerFixture>
{
    private readonly WorkerFixture worker;

    public IngestionEndpointTests(WorkerFixture worker)
    {
        this.worker = worker;
    }

    [Theory]
    [InlineData("claude-code", 3)]
    [InlineData("dotnet-agent", 3)]
    [InlineData("langgraph-python", 3)]
    [InlineData("unknown", 1)]
    public async Task AWellFormedMessageIsAcknowledgedAndItsRowsAreWritten(string dialect, int expectedRows)
    {
        using var run = worker.NewRun();

        var response = await run.Client.PostAsJsonAsync("/push", Envelope(Fixture(dialect, "happy-path")));

        Assert.Equal(HttpStatusCode.NoContent, response.StatusCode);
        Assert.Equal(expectedRows, run.WrittenRows().Count);
    }

    [Theory]
    [InlineData("claude-code")]
    [InlineData("dotnet-agent")]
    [InlineData("langgraph-python")]
    public async Task APoisonMessageIsRefusedSoPubSubCanDeadLetterIt(string dialect)
    {
        using var run = worker.NewRun();

        var response = await run.Client.PostAsJsonAsync("/push", Envelope(Fixture(dialect, "poison")));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Empty(run.WrittenRows());
    }

    [Fact]
    public async Task APoisonMessageDoesNotAffectTheMessagesAroundIt()
    {
        // The property under test is "no silent degradation", and its other half is that
        // one bad message must not take good ones with it.
        using var run = worker.NewRun();

        Assert.Equal(HttpStatusCode.NoContent,
            (await run.Client.PostAsJsonAsync("/push", Envelope(Fixture("claude-code", "happy-path")))).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest,
            (await run.Client.PostAsJsonAsync("/push", Envelope(Fixture("claude-code", "poison")))).StatusCode);
        Assert.Equal(HttpStatusCode.NoContent,
            (await run.Client.PostAsJsonAsync("/push", Envelope(Fixture("dotnet-agent", "happy-path")))).StatusCode);

        Assert.Equal(6, run.WrittenRows().Count);
    }

    [Fact]
    public async Task AMalformedEnvelopeIsRefusedRatherThanIgnored()
    {
        using var run = worker.NewRun();

        foreach (var body in new[] { "{", "{\"message\":{}}", "{\"message\":{\"data\":\"not-base64!!\"}}" })
        {
            var response = await run.Client.PostAsync("/push",
                new StringContent(body, System.Text.Encoding.UTF8, "application/json"));

            Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        }

        Assert.Empty(run.WrittenRows());
    }

    [Fact]
    public async Task TheEnvelopeAttributesReachTheRow()
    {
        using var run = worker.NewRun();

        await run.Client.PostAsJsonAsync("/push", Envelope(Fixture("dotnet-agent", "happy-path"),
            apiKeyId: "local-dotnet", hint: "dotnet-agent"));

        var row = run.WrittenRows()[0];
        Assert.Equal("local-dotnet", row.GetProperty("api_key_id").GetString());
        Assert.Equal("dotnet-agent", row.GetProperty("source_dialect").GetString());

        // Stamped by the sink, not by normalization (architecture §4.1).
        Assert.False(string.IsNullOrEmpty(row.GetProperty("ingest_time").GetString()));
    }

    [Fact]
    public async Task DetectionOverridesAWrongHintRatherThanTrustingIt()
    {
        using var run = worker.NewRun();

        await run.Client.PostAsJsonAsync("/push", Envelope(Fixture("langgraph-python", "happy-path"),
            apiKeyId: "local-misregistered", hint: "claude-code"));

        Assert.All(run.WrittenRows(),
            row => Assert.Equal("langgraph-python", row.GetProperty("source_dialect").GetString()));
    }

    [Fact]
    public async Task AnUncompressedPayloadIsReadWhenTheAttributeSaysSo()
    {
        using var run = worker.NewRun();

        var envelope = new
        {
            message = new
            {
                data = Convert.ToBase64String(Fixture("claude-code", "unmapped-attributes")),
                attributes = new Dictionary<string, string> { ["content_encoding"] = "identity" },
                messageId = "1",
            },
        };

        Assert.Equal(HttpStatusCode.NoContent, (await run.Client.PostAsJsonAsync("/push", envelope)).StatusCode);
        Assert.Single(run.WrittenRows());
    }

    [Fact]
    public async Task TheHealthEndpointNamesTheMechanismSoAcceptAllCannotShipQuietly()
    {
        using var run = worker.NewRun();

        var health = await run.Client.GetFromJsonAsync<JsonElement>("/healthz");

        Assert.Equal("ok", health.GetProperty("status").GetString());
        Assert.Contains("none", health.GetProperty("push_authentication").GetString()!, StringComparison.Ordinal);
    }

    private static byte[] Fixture(string dialect, string kind)
    {
        var root = FindRepositoryRoot();
        return File.ReadAllBytes(Path.Combine(root, "testdata", "fixtures", dialect, kind, "request.pb"));
    }

    internal static string FindRepositoryRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, "testdata", "fixtures")))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("testdata/fixtures not found");
    }

    private static object Envelope(byte[] payload, string apiKeyId = "local-test", string? hint = null)
    {
        using var compressed = new MemoryStream();
        using (var gzip = new GZipStream(compressed, CompressionLevel.Optimal, leaveOpen: true))
        {
            gzip.Write(payload);
        }

        var attributes = new Dictionary<string, string>
        {
            ["api_key_id"] = apiKeyId,
            ["content_encoding"] = "gzip",
        };
        if (hint is not null)
        {
            attributes["source_dialect"] = hint;
        }

        return new
        {
            message = new
            {
                data = Convert.ToBase64String(compressed.ToArray()),
                attributes,
                messageId = Guid.NewGuid().ToString("n"),
            },
            subscription = "projects/plumbline-local/subscriptions/traces-push",
        };
    }
}

/// <summary>Hosts the worker with the local sink, one output directory per test run.</summary>
public sealed class WorkerFixture : WebApplicationFactory<Program>
{
    public WorkerRun NewRun()
    {
        var directory = Path.Combine(Path.GetTempPath(), "plumbline-worker-tests", Guid.NewGuid().ToString("n"));

        var factory = WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment(Environments.Development);
            builder.UseSetting("PLUMBLINE_PUSH_AUTH", "none");
            builder.UseSetting("PLUMBLINE_SINK", "local");
            builder.UseSetting("PLUMBLINE_LOCAL_SINK_DIR", directory);
        });

        return new WorkerRun(factory, directory);
    }
}

public sealed class WorkerRun : IDisposable
{
    private readonly WebApplicationFactory<Program> factory;
    private readonly string directory;

    public WorkerRun(WebApplicationFactory<Program> factory, string directory)
    {
        this.factory = factory;
        this.directory = directory;
        Client = factory.CreateClient();
    }

    public HttpClient Client { get; }

    public IReadOnlyList<JsonElement> WrittenRows()
    {
        if (!Directory.Exists(directory))
        {
            return Array.Empty<JsonElement>();
        }

        return Directory.EnumerateFiles(directory, "*.ndjson")
            .OrderBy(path => path, StringComparer.Ordinal)
            .SelectMany(File.ReadAllLines)
            .Where(line => line.Length > 0)
            .Select(line => JsonDocument.Parse(line).RootElement.Clone())
            .ToList();
    }

    public void Dispose()
    {
        Client.Dispose();
        factory.Dispose();
        if (Directory.Exists(directory))
        {
            Directory.Delete(directory, recursive: true);
        }
    }
}
