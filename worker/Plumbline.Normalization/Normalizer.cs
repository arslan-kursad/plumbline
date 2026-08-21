using System.Globalization;
using System.Text.Json.Nodes;
using Google.Protobuf;
using Google.Protobuf.Collections;
using OpenTelemetry.Proto.Collector.Trace.V1;
using OpenTelemetry.Proto.Common.V1;
using OpenTelemetry.Proto.Resource.V1;
using OpenTelemetry.Proto.Trace.V1;
using Plumbline.Normalization.Detection;
using Plumbline.Normalization.Mappings;
using Plumbline.Normalization.Redaction;
using Plumbline.Normalization.Rows;

namespace Plumbline.Normalization;

/// <summary>What the message carried around the payload (Pub/Sub attributes, §3.2).</summary>
public sealed record MessageEnvelope(string ApiKeyId, string? SourceDialectHint);

/// <summary>
/// Something worth reporting that is not a failure: a hint that disagreed with detection,
/// an unknown dialect, a value that would not coerce.
/// </summary>
/// <remarks>
/// These are the reporting controls ADR-0003 §"Enforcement" names. They report and do not
/// prevent — but reporting means the worker logs them and a counter moves, not that they
/// are dropped on the floor, which is the difference between a known limitation and
/// silent degradation.
/// </remarks>
public sealed record NormalizationNote(string Kind, string Detail);

public sealed record NormalizationResult(IReadOnlyList<SpanRow> Rows, IReadOnlyList<NormalizationNote> Notes)
{
    public int RedactedValues { get; init; }
}

/// <summary>
/// OTLP export request in, <c>spans</c> rows out.
/// </summary>
/// <remarks>
/// The stages are detect → normalize → redact, in that order and separable on purpose:
/// redaction is a `Proposed` boundary (ADR-0006) and has to stay a stage that can be
/// moved, not logic spread through the mapping walk.
/// </remarks>
public sealed class Normalizer
{
    private readonly MappingCatalog catalog;
    private readonly DialectDetector detector;
    private readonly Redactor redactor;

    public Normalizer(MappingCatalog catalog, Redactor redactor)
    {
        this.catalog = catalog;
        this.redactor = redactor;
        detector = new DialectDetector(catalog);
    }

    public static Normalizer Default { get; } = new(MappingCatalog.Embedded, Redactor.Embedded);

    public NormalizationResult Normalize(ExportTraceServiceRequest request, MessageEnvelope envelope)
    {
        var rows = new List<SpanRow>();
        var notes = new List<NormalizationNote>();
        var redacted = 0;

        foreach (var resourceSpans in request.ResourceSpans)
        {
            var resource = resourceSpans.Resource;
            var resourceJson = AttributeValues.ToJson(ResourceAttributes(resource));
            var serviceName = AttributeValues.AsString(AttributeValues.Find(ResourceAttributes(resource), "service.name"));
            var synthetic = AttributeValues.Find(ResourceAttributes(resource), "synthetic") is { } flag
                            && flag.ValueCase == AnyValue.ValueOneofCase.BoolValue && flag.BoolValue;

            foreach (var scopeSpans in resourceSpans.ScopeSpans)
            {
                var detection = detector.Detect(resource, scopeSpans.Scope, envelope.SourceDialectHint);
                var table = catalog.Find(detection.Dialect) ?? MappingCatalog.Generic;

                if (detection.HintMismatch)
                {
                    notes.Add(new NormalizationNote("dialect_hint_mismatch",
                        $"collector hinted '{envelope.SourceDialectHint}', detection says '{detection.Dialect}' " +
                        $"by {detection.Basis}; the detected value wins"));
                }

                if (detection.Dialect == MappingCatalog.UnknownDialect)
                {
                    notes.Add(new NormalizationNote("unknown_dialect",
                        $"scope '{scopeSpans.Scope?.Name}' matches no registered dialect; " +
                        "normalized generically and kept"));
                }

                // schema_url: the scope level states which conventions the
                // instrumentation emitted, which is the narrower claim, so it wins over
                // the resource level (decision log W2.6).
                var schemaUrl = FirstNonEmpty(scopeSpans.SchemaUrl, resourceSpans.SchemaUrl);

                foreach (var span in scopeSpans.Spans)
                {
                    var attributes = new JsonObject
                    {
                        ["resource"] = resourceJson.DeepClone(),
                        ["scope"] = new JsonObject
                        {
                            ["name"] = scopeSpans.Scope?.Name ?? "",
                            ["version"] = scopeSpans.Scope?.Version ?? "",
                            ["attributes"] = AttributeValues.ToJson(scopeSpans.Scope?.Attributes ?? Empty),
                        },
                        ["span"] = AttributeValues.ToJson(span.Attributes),
                    };

                    var events = EventsJson(span);
                    var links = LinksJson(span);

                    var row = BuildRow(span, table, detection.Dialect, envelope, serviceName, schemaUrl,
                        synthetic, attributes, events, links, notes);

                    redacted += redactor.Redact(detection.Dialect, attributes, events, links);

                    rows.Add(row);
                }
            }
        }

        return new NormalizationResult(rows, notes) { RedactedValues = redacted };
    }

    private static SpanRow BuildRow(
        Span span, MappingTable table, string dialect, MessageEnvelope envelope,
        string? serviceName, string? schemaUrl, bool synthetic,
        JsonObject attributes, JsonArray events, JsonArray links, List<NormalizationNote> notes)
    {
        var typed = new Dictionary<string, object?>(StringComparer.Ordinal);
        foreach (var column in table.Columns)
        {
            typed[column.Column] = Evaluate(column, span, notes);
        }

        return new SpanRow
        {
            StartTime = Timestamps.FromUnixNanos(span.StartTimeUnixNano),
            EndTime = Timestamps.FromUnixNanos(span.EndTimeUnixNano),
            TraceId = Hex(span.TraceId),
            SpanId = Hex(span.SpanId),
            ParentSpanId = span.ParentSpanId.IsEmpty ? null : Hex(span.ParentSpanId),
            Name = span.Name,
            Kind = span.Kind.ToString().ToUpperUnderscored("SPAN_KIND"),
            StatusCode = (span.Status?.Code ?? Status.Types.StatusCode.Unset).ToString().ToUpperUnderscored("STATUS_CODE"),
            StatusMessage = string.IsNullOrEmpty(span.Status?.Message) ? null : span.Status.Message,
            ServiceName = serviceName,
            SourceDialect = dialect,
            ApiKeyId = envelope.ApiKeyId,
            SchemaUrl = schemaUrl,
            Synthetic = synthetic,
            GenAiProviderName = (string?)typed.GetValueOrDefault("gen_ai_provider_name"),
            GenAiOperationName = (string?)typed.GetValueOrDefault("gen_ai_operation_name"),
            GenAiRequestModel = (string?)typed.GetValueOrDefault("gen_ai_request_model"),
            GenAiResponseModel = (string?)typed.GetValueOrDefault("gen_ai_response_model"),
            GenAiResponseId = (string?)typed.GetValueOrDefault("gen_ai_response_id"),
            GenAiConversationId = (string?)typed.GetValueOrDefault("gen_ai_conversation_id"),
            GenAiAgentName = (string?)typed.GetValueOrDefault("gen_ai_agent_name"),
            GenAiToolName = (string?)typed.GetValueOrDefault("gen_ai_tool_name"),
            GenAiToolCallId = (string?)typed.GetValueOrDefault("gen_ai_tool_call_id"),
            GenAiUsageInputTokens = (long?)typed.GetValueOrDefault("gen_ai_usage_input_tokens"),
            GenAiUsageOutputTokens = (long?)typed.GetValueOrDefault("gen_ai_usage_output_tokens"),
            GenAiRequestMaxTokens = (long?)typed.GetValueOrDefault("gen_ai_request_max_tokens"),
            GenAiRequestTemperature = (double?)typed.GetValueOrDefault("gen_ai_request_temperature"),
            GenAiRequestTopP = (double?)typed.GetValueOrDefault("gen_ai_request_top_p"),
            GenAiOutputType = (string?)typed.GetValueOrDefault("gen_ai_output_type"),
            Attributes = attributes,
            Events = events,
            Links = links,
        };
    }

    /// <summary>
    /// Applies a column's rules in order and returns the first value produced.
    /// </summary>
    /// <remarks>
    /// Order in the YAML is the precedence, which is what lets a mapping put the current
    /// semconv name above a deprecated fallback and stop rewriting the moment the emitter
    /// upgrades. A rule that produces nothing falls through; a value that will not coerce
    /// produces a note rather than a crash or a silent null.
    /// </remarks>
    private static object? Evaluate(ColumnMapping column, Span span, List<NormalizationNote> notes)
    {
        var type = Enum.TryParse<ColumnType>(column.Type, ignoreCase: true, out var parsed)
            ? parsed
            : ColumnType.String;

        foreach (var rule in column.Rules)
        {
            if (rule.FromSpanName is { } byName)
            {
                if (byName.TryGetValue(span.Name, out var constant))
                {
                    return Coerce(column, constant, type, notes);
                }

                continue;
            }

            if (rule.From is null)
            {
                continue;
            }

            var raw = AttributeValues.Find(span.Attributes, rule.From);
            if (raw is null)
            {
                continue;
            }

            if (rule.Map is { } map)
            {
                var key = AttributeValues.AsString(raw);
                // A value absent from the map yields nothing: passing an unmapped emitter
                // value through would put a string that is not a v1.41 enum member into a
                // column the eval engine reads as one.
                if (key is null || !map.TryGetValue(key, out var mapped))
                {
                    notes.Add(new NormalizationNote("unmapped_value",
                        $"{column.Column}: '{rule.From}' = '{key}' is not in the rule's value map"));
                    continue;
                }

                return Coerce(column, mapped, type, notes);
            }

            var value = CoerceAny(column, raw, type, notes);
            if (value is not null)
            {
                return value;
            }
        }

        return null;
    }

    private static object? Coerce(ColumnMapping column, string value, ColumnType type, List<NormalizationNote> notes) =>
        type switch
        {
            ColumnType.String => value,
            ColumnType.Int when long.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i) => i,
            ColumnType.Double when double.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out var d) => d,
            _ => Note(column, value, type, notes),
        };

    private static object? CoerceAny(ColumnMapping column, AnyValue raw, ColumnType type, List<NormalizationNote> notes)
    {
        switch (type)
        {
            case ColumnType.Int when raw.ValueCase == AnyValue.ValueOneofCase.IntValue:
                return raw.IntValue;
            case ColumnType.Double when raw.ValueCase == AnyValue.ValueOneofCase.DoubleValue:
                return raw.DoubleValue;
            case ColumnType.Double when raw.ValueCase == AnyValue.ValueOneofCase.IntValue:
                // An emitter sending a whole-number temperature as an int is not an error.
                return (double)raw.IntValue;
        }

        var text = AttributeValues.AsString(raw);
        return text is null ? Note(column, raw.ValueCase.ToString(), type, notes) : Coerce(column, text, type, notes);
    }

    private static object? Note(ColumnMapping column, string value, ColumnType type, List<NormalizationNote> notes)
    {
        notes.Add(new NormalizationNote("coercion_failed",
            $"{column.Column}: '{value}' is not a {type.ToString().ToLowerInvariant()}; column left null and " +
            "the original value kept in the lossless attributes"));
        return null;
    }

    private static readonly RepeatedField<KeyValue> Empty = new();

    private static RepeatedField<KeyValue> ResourceAttributes(Resource? resource) =>
        resource?.Attributes ?? Empty;

    private static JsonArray EventsJson(Span span)
    {
        var events = new JsonArray();
        foreach (var e in span.Events)
        {
            events.Add(new JsonObject
            {
                ["time"] = Timestamps.Format(Timestamps.FromUnixNanos(e.TimeUnixNano)),
                ["name"] = e.Name,
                ["attributes"] = AttributeValues.ToJson(e.Attributes),
                ["dropped_attributes_count"] = e.DroppedAttributesCount,
            });
        }

        return events;
    }

    private static JsonArray LinksJson(Span span)
    {
        var links = new JsonArray();
        foreach (var link in span.Links)
        {
            links.Add(new JsonObject
            {
                ["trace_id"] = Hex(link.TraceId),
                ["span_id"] = Hex(link.SpanId),
                ["trace_state"] = link.TraceState,
                ["attributes"] = AttributeValues.ToJson(link.Attributes),
            });
        }

        return links;
    }

    private static string? FirstNonEmpty(params string?[] candidates) =>
        candidates.FirstOrDefault(c => !string.IsNullOrEmpty(c));

    private static string Hex(ByteString bytes) => Convert.ToHexString(bytes.Span).ToLowerInvariant();
}

internal static class EnumNames
{
    /// <summary>
    /// Renders a protobuf enum member as its wire name: <c>Internal</c> → <c>SPAN_KIND_INTERNAL</c>.
    /// </summary>
    /// <remarks>
    /// The C# generator strips the prefix and camel-cases what remains, so the name in
    /// code is not the name in the proto. Architecture §4.1 stores "OTLP enum name", and
    /// a dashboard grouping on `kind` should see what OTLP calls it, not what C# does.
    /// </remarks>
    public static string ToUpperUnderscored(this string memberName, string prefix)
    {
        var text = new System.Text.StringBuilder(prefix);
        foreach (var c in memberName)
        {
            if (char.IsUpper(c) && text.Length > prefix.Length)
            {
                text.Append('_');
            }
            else if (text.Length == prefix.Length)
            {
                text.Append('_');
            }

            text.Append(char.ToUpperInvariant(c));
        }

        return text.ToString();
    }
}
