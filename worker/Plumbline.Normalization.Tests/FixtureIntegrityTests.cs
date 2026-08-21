using System.Text.Json.Nodes;
using Google.Protobuf;
using OpenTelemetry.Proto.Collector.Trace.V1;
using Plumbline.Fixtures;
using Plumbline.Normalization.Rows;
using YamlDotNet.Serialization;

namespace Plumbline.Normalization.Tests;

/// <summary>
/// Properties of the fixture corpus itself, checked before anything is normalized.
/// </summary>
/// <remarks>
/// A golden-file suite is only as trustworthy as its inputs. These tests answer the
/// questions that would otherwise be answered by "it looked right when it was written":
/// does the committed binary still correspond to the readable twin, does the poison
/// payload actually fail to parse, and does every fixture carry the provenance the
/// manifest contract requires.
/// </remarks>
public class FixtureIntegrityTests
{
    [Theory]
    [MemberData(nameof(FixtureCorpus.Cases), MemberType = typeof(FixtureCorpus))]
    public void EveryBinaryPayloadMatchesItsTwin(FixtureCase fixture)
    {
        if (!fixture.HasTwin)
        {
            // Poison fixtures are byte edits, not encodable documents; they are covered
            // by PoisonPayloadsFailToParse instead.
            Assert.False(File.Exists(fixture.TwinPath));
            return;
        }

        var expected = FixtureEncoder.Encode(File.ReadAllText(fixture.TwinPath));
        var committed = fixture.Payload();

        Assert.True(
            expected.AsSpan().SequenceEqual(committed),
            $"{fixture}: request.pb is {committed.Length} bytes but its twin encodes to " +
            $"{expected.Length}. Regenerate with: dotnet run --project worker/Plumbline.Fixtures");
    }

    [Theory]
    [MemberData(nameof(FixtureCorpus.Cases), MemberType = typeof(FixtureCorpus))]
    public void EveryPayloadParsesUnlessItIsPoison(FixtureCase fixture)
    {
        var payload = fixture.Payload();

        if (fixture.Case == "poison")
        {
            var parsed = TryParse(payload);
            Assert.False(
                parsed,
                $"{fixture}: the poison payload parsed successfully. Truncation that lands on a " +
                "field boundary yields a valid shorter message, which would test nothing — " +
                "adjust PoisonPrefixBytes in Plumbline.Fixtures until it does not parse.");
            return;
        }

        Assert.True(TryParse(payload), $"{fixture}: payload does not parse as ExportTraceServiceRequest");
    }

    [Theory]
    [MemberData(nameof(FixtureCorpus.CasesWithExpectedRows), MemberType = typeof(FixtureCorpus))]
    public void ExpectedRowsCarryExactlyTheTableColumns(FixtureCase fixture)
    {
        var rows = fixture.ExpectedRows();
        Assert.NotEmpty(rows);

        for (var i = 0; i < rows.Count; i++)
        {
            var row = Assert.IsType<JsonObject>(rows[i]);
            var actual = row.Select(p => p.Key).ToList();

            Assert.True(
                actual.SequenceEqual(SpanRow.Columns),
                $"{fixture} rows[{i}]: column set or order differs from SpanRow.Columns.\n" +
                $"  missing:    {string.Join(", ", SpanRow.Columns.Except(actual))}\n" +
                $"  unexpected: {string.Join(", ", actual.Except(SpanRow.Columns))}");
        }
    }

    [Theory]
    [MemberData(nameof(FixtureCorpus.CasesWithExpectedRows), MemberType = typeof(FixtureCorpus))]
    public void ExpectedRowCountMatchesTheSpansInThePayload(FixtureCase fixture)
    {
        var request = ExportTraceServiceRequest.Parser.ParseFrom(fixture.Payload());
        var spans = request.ResourceSpans.Sum(rs => rs.ScopeSpans.Sum(ss => ss.Spans.Count));

        Assert.Equal(spans, fixture.ExpectedRows().Count);
    }

    [Fact]
    public void EveryDialectCarriesAManifestWithProvenance()
    {
        var required = new[]
        {
            "dialect", "provenance", "construction_basis", "emitter", "emitter_version",
            "instrumentation_scope", "semconv_version_emitted", "schema_url_emitted",
            "otel_semconv_stability_opt_in", "redacted_fields", "validation_status", "cases",
        };

        var deserializer = new DeserializerBuilder().Build();

        foreach (var dialect in FixtureCorpus.Dialects())
        {
            var path = FixtureCorpus.ManifestPath(dialect);
            Assert.True(File.Exists(path), $"{dialect}: no manifest.yaml");

            var manifest = deserializer.Deserialize<Dictionary<string, object>>(File.ReadAllText(path));
            var missing = required.Where(key => !manifest.ContainsKey(key)).ToList();

            Assert.True(
                missing.Count == 0,
                $"{dialect}/manifest.yaml is missing: {string.Join(", ", missing)}. " +
                "A fixture without provenance, emitter version, the semconv version actually " +
                "emitted and the stability opt-in value is not evidence (eval plan SC-1 row 1.2).");

            Assert.Equal(dialect, manifest["dialect"]?.ToString());
        }
    }

    [Fact]
    public void EveryDialectExceptTheUnknownFallbackHasAPoisonCase()
    {
        foreach (var dialect in FixtureCorpus.Dialects().Where(d => d != "unknown"))
        {
            Assert.True(
                File.Exists(Path.Combine(FixtureCorpus.Root, dialect, "poison", "request.pb")),
                $"{dialect}: no poison case. The NACK → redelivery → DLQ path is asserted per " +
                "dialect because a payload that fails to parse is the only input that proves it.");
        }
    }

    private static bool TryParse(byte[] payload)
    {
        try
        {
            var request = ExportTraceServiceRequest.Parser.WithDiscardUnknownFields(false).ParseFrom(payload);

            // A truncation landing on a field boundary parses into a message with no
            // spans. That is still a poison payload for our purposes — nothing to write —
            // but it does not exercise the deserialization failure path, so it does not
            // count as parsed here.
            return request.ResourceSpans.Sum(rs => rs.ScopeSpans.Sum(ss => ss.Spans.Count)) > 0;
        }
        catch (InvalidProtocolBufferException)
        {
            return false;
        }
    }
}
