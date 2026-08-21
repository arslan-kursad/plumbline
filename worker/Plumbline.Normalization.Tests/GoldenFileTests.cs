using System.Text.Json.Nodes;
using OpenTelemetry.Proto.Collector.Trace.V1;
using Plumbline.Normalization;
using Plumbline.Normalization.Mappings;
using Plumbline.Normalization.Rows;

namespace Plumbline.Normalization.Tests;

/// <summary>
/// The golden-file suite: raw <c>ExportTraceServiceRequest</c> in, the rows in
/// <c>expected-rows.json</c> out.
/// </summary>
/// <remarks>
/// These are the enforcement mechanism of ADR-0001 §3.1, not a testing habit. The project
/// does not store raw protobuf, so the fidelity of raw → normalized is a tested property
/// and this is the test. The expected rows were written before the normalizer existed
/// (F1 W2), which is what keeps them a contract rather than a transcript.
/// </remarks>
public class GoldenFileTests
{
    private static readonly MessageEnvelope Envelope = new("local-test", SourceDialectHint: null);

    [Theory]
    [MemberData(nameof(FixtureCorpus.CasesWithExpectedRows), MemberType = typeof(FixtureCorpus))]
    public void NormalizedRowsMatchTheGoldenFile(FixtureCase fixture)
    {
        var actual = Normalize(fixture, Envelope);
        var diffs = RowDiff.Compare(fixture.ExpectedRows(), actual);

        Assert.True(diffs.Count == 0, RowDiff.Describe(fixture.ToString(), diffs));
    }

    [Fact]
    public void AnUnregisteredScopeIsNormalizedGenericallyAndNeverDropped()
    {
        var fixture = FixtureCorpus.All().Single(f => f.Dialect == "unknown" && f.Case == "happy-path");

        var result = Normalizer.Default.Normalize(Parse(fixture), Envelope);

        Assert.Single(result.Rows);
        Assert.Equal(MappingCatalog.UnknownDialect, result.Rows[0].SourceDialect);
        Assert.Contains(result.Notes, note => note.Kind == "unknown_dialect");

        // The payload's span names carry the `claude_code.` prefix and a `span.type`
        // attribute. A detector keyed on span names would call this claude-code; keyed on
        // the scope, it does not. This is the case evidence §6.3 asks for by name.
        Assert.DoesNotContain(result.Notes, note => note.Detail.Contains("claude-code", StringComparison.Ordinal));

        // Generic still means normalized: the payload states v1.41 names, so the typed
        // columns are filled from them rather than left null out of caution.
        Assert.Equal("chat", result.Rows[0].GenAiOperationName);
        Assert.Equal(42, result.Rows[0].GenAiUsageInputTokens);
    }

    [Theory]
    [InlineData("claude-code", "com.anthropic.claude_code.tracing")]
    [InlineData("dotnet-agent", "Experimental.Microsoft.Extensions.AI")]
    [InlineData("langgraph-python", "openinference.instrumentation.langchain")]
    public void DetectionIgnoresAWrongHintAndReportsIt(string dialect, string scopeName)
    {
        var fixture = FixtureCorpus.All().Single(f => f.Dialect == dialect && f.Case == "happy-path");

        var result = Normalizer.Default.Normalize(
            Parse(fixture), new MessageEnvelope("local-test", SourceDialectHint: "dotnet-agent"));

        Assert.All(result.Rows, row => Assert.Equal(dialect, row.SourceDialect));

        if (dialect == "dotnet-agent")
        {
            Assert.DoesNotContain(result.Notes, note => note.Kind == "dialect_hint_mismatch");
            return;
        }

        var note = Assert.Single(result.Notes, note => note.Kind == "dialect_hint_mismatch");
        Assert.Contains(scopeName, string.Join(" ", result.Rows.Select(r => r.Attributes["scope"]!["name"]!.ToString())),
            StringComparison.Ordinal);
        Assert.Contains("the detected value wins", note.Detail, StringComparison.Ordinal);
    }

    [Fact]
    public void EveryAttributeSurvivesInTheLosslessColumn()
    {
        foreach (var fixture in FixtureCorpus.All().Where(f => f.Case == "unmapped-attributes"))
        {
            var request = Parse(fixture);
            var result = Normalizer.Default.Normalize(request, Envelope);

            var sent = request.ResourceSpans
                .SelectMany(rs => rs.ScopeSpans)
                .SelectMany(ss => ss.Spans)
                .SelectMany(span => span.Attributes)
                .Select(attribute => attribute.Key)
                .ToHashSet(StringComparer.Ordinal);

            var stored = ((JsonObject)result.Rows[0].Attributes["span"]!)
                .Select(pair => pair.Key)
                .ToHashSet(StringComparer.Ordinal);

            Assert.True(sent.SetEquals(stored),
                $"{fixture}: the lossless column does not hold exactly what was sent.\n" +
                $"  dropped: {string.Join(", ", sent.Except(stored))}\n" +
                $"  added:   {string.Join(", ", stored.Except(sent))}");
        }
    }

    [Fact]
    public void RedactionReplacesValuesWithoutRemovingKeys()
    {
        var fixture = FixtureCorpus.All().Single(f => f.Dialect == "claude-code" && f.Case == "happy-path");
        var result = Normalizer.Default.Normalize(Parse(fixture), Envelope);

        var span = (JsonObject)result.Rows[1].Attributes["span"]!;

        Assert.True(span.ContainsKey("user.email"), "redaction removed the key rather than the value");
        Assert.StartsWith("[REDACTED:sha256:", span["user.email"]!.ToString(), StringComparison.Ordinal);

        // Determinism is the property joins depend on: the same client_request_id on the
        // span and on its event has to produce the same marker.
        var onSpan = span["client_request_id"]!.ToString();
        var onEvent = result.Rows[1].Events[0]!["attributes"]!["client_request_id"]!.ToString();
        Assert.Equal(onSpan, onEvent);

        Assert.True(result.RedactedValues > 0);
    }

    [Fact]
    public void RedactionLeavesOtherDialectsAlone()
    {
        var fixture = FixtureCorpus.All().Single(f => f.Dialect == "langgraph-python" && f.Case == "happy-path");
        var result = Normalizer.Default.Normalize(Parse(fixture), Envelope);

        Assert.Equal(0, result.RedactedValues);
        Assert.Equal("adj-session-0f21", result.Rows[0].Attributes["span"]!["session.id"]!.ToString());
    }

    private static ExportTraceServiceRequest Parse(FixtureCase fixture) =>
        ExportTraceServiceRequest.Parser.ParseFrom(fixture.Payload());

    private static JsonArray Normalize(FixtureCase fixture, MessageEnvelope envelope)
    {
        var rows = Normalizer.Default.Normalize(Parse(fixture), envelope).Rows;
        return new JsonArray(rows.Select(row => (JsonNode?)row.ToJson()).ToArray());
    }
}
