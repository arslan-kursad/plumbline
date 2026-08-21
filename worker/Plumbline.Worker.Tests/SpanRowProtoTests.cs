using System.Text.RegularExpressions;
using Plumbline.Normalization.Rows;
using Plumbline.Normalization.Storage;
using Plumbline.Worker.Sinks;
using System.Text.Json.Nodes;

namespace Plumbline.Worker.Tests;

/// <summary>
/// The proto twin of the <c>spans</c> table.
/// </summary>
/// <remarks>
/// The Storage Write API takes rows as serialized protobuf plus a descriptor, so the
/// table exists twice: once as SQL in <c>analytics/sql/001_spans_table.sql</c> and once
/// as <c>proto/span_row.proto</c>. Two definitions of one schema drift, and the drift is
/// invisible until an append fails in production against a column nobody renamed here.
/// These tests are the check that keeps them in step.
/// </remarks>
public class SpanRowProtoTests
{
    [Fact]
    public void TheProtoCarriesExactlyTheColumnsTheTableDeclares()
    {
        var sql = File.ReadAllText(Path.Combine(
            IngestionEndpointTests.FindRepositoryRoot(), "analytics", "sql", "001_spans_table.sql"));

        var columns = Regex.Matches(sql, @"^\s{2}([a-z][a-z0-9_]*)\s+(TIMESTAMP|STRING|BOOL|INT64|FLOAT64|JSON)",
                RegexOptions.Multiline)
            .Select(match => match.Groups[1].Value)
            .ToList();

        Assert.NotEmpty(columns);

        var fields = SpanRowProto.Descriptor.Fields.InFieldNumberOrder()
            .Select(field => field.Name)
            .ToList();

        Assert.True(columns.SequenceEqual(fields),
            "the table and its proto twin disagree.\n" +
            $"  in SQL only:   {string.Join(", ", columns.Except(fields))}\n" +
            $"  in proto only: {string.Join(", ", fields.Except(columns))}\n" +
            "  (order matters here too: the proto's field order is the row's wire order)");
    }

    [Fact]
    public void EveryColumnTheTableAllowsToBeNullIsOptionalInTheProto()
    {
        // BigQuery stores an unset optional as NULL. A field that is not optional would
        // arrive as 0 or "" instead, turning "this dialect emits no token counts" — a
        // measured property — into a claim that it emitted zero.
        foreach (var field in SpanRowProto.Descriptor.Fields.InFieldNumberOrder())
        {
            Assert.True(field.HasPresence, $"{field.Name} cannot express NULL");
        }
    }

    [Fact]
    public void NullColumnsStayUnsetRatherThanBecomingZero()
    {
        var row = new SpanRow
        {
            StartTime = DateTimeOffset.UnixEpoch,
            EndTime = DateTimeOffset.UnixEpoch,
            TraceId = "aa",
            SpanId = "bb",
            Name = "claude_code.interaction",
            Kind = "SPAN_KIND_INTERNAL",
            StatusCode = "STATUS_CODE_UNSET",
            SourceDialect = "claude-code",
            Attributes = new JsonObject(),
            Events = new JsonArray(),
            Links = new JsonArray(),
        };

        var proto = BigQueryStorageWriteSink.ToProto(row, ingestTimeMicroseconds: 0);

        Assert.False(proto.HasGenAiUsageInputTokens);
        Assert.False(proto.HasGenAiRequestTemperature);
        Assert.False(proto.HasParentSpanId);
        Assert.False(proto.HasSchemaUrl);
        Assert.True(proto.HasTraceId);
    }

    [Fact]
    public void TimestampsBecomeMicrosecondsSinceTheEpoch()
    {
        var row = new SpanRow
        {
            StartTime = DateTimeOffset.Parse("2026-08-19T10:00:01.612345Z"),
            EndTime = DateTimeOffset.Parse("2026-08-19T10:00:01.612345Z"),
            TraceId = "aa",
            SpanId = "bb",
            Name = "n",
            Kind = "SPAN_KIND_INTERNAL",
            StatusCode = "STATUS_CODE_UNSET",
            SourceDialect = "unknown",
            Attributes = new JsonObject(),
            Events = new JsonArray(),
            Links = new JsonArray(),
        };

        var proto = BigQueryStorageWriteSink.ToProto(row, ingestTimeMicroseconds: 7);

        Assert.Equal(1787133601612345L, proto.StartTime);
        Assert.Equal(7L, proto.IngestTime);
    }
}

/// <summary>
/// The descriptor actually sent to the Storage Write API.
/// </summary>
/// <remarks>
/// This is a regression test with a specific history: the first end-to-end run failed
/// with `failed to create file descriptor: … under proto3 optional semantics must be
/// specified in the proto3 syntax`, because a `DescriptorProto` carries no file-level
/// syntax and is therefore read with proto2 semantics, where protoc's proto3-optional
/// markers are invalid.
/// </remarks>
public class WriterDescriptorTests
{
    [Fact]
    public void TheDescriptorSentToBigQueryCarriesNoProto3OptionalMarkers()
    {
        var descriptor = Plumbline.Worker.Sinks.BigQueryStorageWriteSink.WriterDescriptor;

        Assert.Empty(descriptor.OneofDecl);
        Assert.All(descriptor.Field, field =>
        {
            Assert.False(field.HasProto3Optional, $"{field.Name} still declares proto3_optional");
            Assert.False(field.HasOneofIndex, $"{field.Name} still belongs to a synthetic one-of");
        });
    }

    [Fact]
    public void EveryColumnSurvivesTheConversionAsAnOptionalField()
    {
        var descriptor = Plumbline.Worker.Sinks.BigQueryStorageWriteSink.WriterDescriptor;

        Assert.Equal(SpanRowProto.Descriptor.Fields.InFieldNumberOrder().Count, descriptor.Field.Count);
        Assert.All(descriptor.Field, field =>
            Assert.Equal(Google.Protobuf.Reflection.FieldDescriptorProto.Types.Label.Optional, field.Label));
    }
}
