using System.Text.Json.Nodes;

namespace Plumbline.Normalization.Rows;

/// <summary>
/// One normalized row of the BigQuery <c>spans</c> table (architecture §4.1), as the
/// normalizer produces it.
/// </summary>
/// <remarks>
/// <para>
/// The typed <c>gen_ai_*</c> set is scalars only. Array-valued GenAI attributes —
/// <c>gen_ai.response.finish_reasons</c> is the one this project's dialects actually
/// emit — stay in <see cref="Attributes"/>, which is lossless anyway. A repeated column
/// would buy grouping that the JSON column already supports and would cost a schema
/// shape the local BigQuery stand-in has to agree with.
/// </para>
/// <para>
/// There is no <c>ingest_time</c> here. Architecture §4.1 defines it as the worker's
/// write time, so it is stamped by the sink rather than produced by normalization; that
/// also keeps golden comparisons free of a clock without needing to exclude a column.
/// </para>
/// </remarks>
public sealed record SpanRow
{
    // OTLP structure.
    public required DateTimeOffset StartTime { get; init; }
    public required DateTimeOffset EndTime { get; init; }
    public required string TraceId { get; init; }
    public required string SpanId { get; init; }
    public string? ParentSpanId { get; init; }
    public required string Name { get; init; }
    public required string Kind { get; init; }
    public required string StatusCode { get; init; }
    public string? StatusMessage { get; init; }

    // Provenance.
    public string? ServiceName { get; init; }
    public required string SourceDialect { get; init; }
    public string? ApiKeyId { get; init; }
    public string? SchemaUrl { get; init; }
    public bool Synthetic { get; init; }

    // Normalized GenAI columns, semconv v1.41.
    public string? GenAiProviderName { get; init; }
    public string? GenAiOperationName { get; init; }
    public string? GenAiRequestModel { get; init; }
    public string? GenAiResponseModel { get; init; }
    public string? GenAiResponseId { get; init; }
    public string? GenAiConversationId { get; init; }
    public string? GenAiAgentName { get; init; }
    public string? GenAiToolName { get; init; }
    public string? GenAiToolCallId { get; init; }
    public long? GenAiUsageInputTokens { get; init; }
    public long? GenAiUsageOutputTokens { get; init; }
    public long? GenAiRequestMaxTokens { get; init; }
    public double? GenAiRequestTemperature { get; init; }
    public double? GenAiRequestTopP { get; init; }
    public string? GenAiOutputType { get; init; }

    /// <summary>
    /// Lossless remainder: every attribute the payload carried, at all three levels.
    /// </summary>
    /// <remarks>
    /// Architecture §4.1 names one <c>attributes</c> JSON column and calls it the
    /// lossless remainder without fixing its shape. The shape is
    /// <c>{ "resource": {...}, "scope": { "name", "version", "attributes" }, "span": {...} }</c>:
    /// flattening the three levels into one bag would lose which level a key came from
    /// and would let a resource attribute collide with a span attribute of the same name.
    /// Attributes promoted to typed columns stay here too — "lossless" means the column
    /// answers what the emitter sent, independently of what the mapping understood.
    /// </remarks>
    public required JsonObject Attributes { get; init; }

    public required JsonArray Events { get; init; }

    public required JsonArray Links { get; init; }

    /// <summary>Column names in their canonical order, which is also the table's.</summary>
    public static IReadOnlyList<string> Columns { get; } = new[]
    {
        "start_time", "end_time", "trace_id", "span_id", "parent_span_id", "name", "kind",
        "status_code", "status_message", "service_name", "source_dialect", "api_key_id",
        "schema_url", "synthetic",
        "gen_ai_provider_name", "gen_ai_operation_name", "gen_ai_request_model",
        "gen_ai_response_model", "gen_ai_response_id", "gen_ai_conversation_id",
        "gen_ai_agent_name", "gen_ai_tool_name", "gen_ai_tool_call_id",
        "gen_ai_usage_input_tokens", "gen_ai_usage_output_tokens",
        "gen_ai_request_max_tokens", "gen_ai_request_temperature",
        "gen_ai_request_top_p", "gen_ai_output_type",
        "attributes", "events", "links",
    };

    /// <summary>
    /// Renders the row as the JSON object the golden files hold: snake_case column
    /// names, canonical order, timestamps at BigQuery TIMESTAMP precision.
    /// </summary>
    public JsonObject ToJson() => new()
    {
        ["start_time"] = Timestamps.Format(StartTime),
        ["end_time"] = Timestamps.Format(EndTime),
        ["trace_id"] = TraceId,
        ["span_id"] = SpanId,
        ["parent_span_id"] = ParentSpanId,
        ["name"] = Name,
        ["kind"] = Kind,
        ["status_code"] = StatusCode,
        ["status_message"] = StatusMessage,
        ["service_name"] = ServiceName,
        ["source_dialect"] = SourceDialect,
        ["api_key_id"] = ApiKeyId,
        ["schema_url"] = SchemaUrl,
        ["synthetic"] = Synthetic,
        ["gen_ai_provider_name"] = GenAiProviderName,
        ["gen_ai_operation_name"] = GenAiOperationName,
        ["gen_ai_request_model"] = GenAiRequestModel,
        ["gen_ai_response_model"] = GenAiResponseModel,
        ["gen_ai_response_id"] = GenAiResponseId,
        ["gen_ai_conversation_id"] = GenAiConversationId,
        ["gen_ai_agent_name"] = GenAiAgentName,
        ["gen_ai_tool_name"] = GenAiToolName,
        ["gen_ai_tool_call_id"] = GenAiToolCallId,
        ["gen_ai_usage_input_tokens"] = GenAiUsageInputTokens,
        ["gen_ai_usage_output_tokens"] = GenAiUsageOutputTokens,
        ["gen_ai_request_max_tokens"] = GenAiRequestMaxTokens,
        ["gen_ai_request_temperature"] = GenAiRequestTemperature,
        ["gen_ai_request_top_p"] = GenAiRequestTopP,
        ["gen_ai_output_type"] = GenAiOutputType,
        ["attributes"] = Attributes.DeepClone(),
        ["events"] = Events.DeepClone(),
        ["links"] = Links.DeepClone(),
    };
}

/// <summary>
/// BigQuery <c>TIMESTAMP</c> holds microseconds; OTLP timestamps are nanoseconds.
/// </summary>
/// <remarks>
/// The remaining three digits are dropped, not rounded, and they are not preserved
/// anywhere else. This is a real and permanent loss at the storage boundary — ADR-0001's
/// losslessness claim is about *attributes*, not about timestamp precision — so it is
/// named here, in the mapping README, and made visible by a fixture whose span ends on a
/// sub-microsecond boundary rather than left for someone to discover in a query.
/// </remarks>
public static class Timestamps
{
    public const long NanosPerMicrosecond = 1_000;
    private const long TicksPerMicrosecond = 10;

    public static DateTimeOffset FromUnixNanos(ulong unixNanos)
    {
        var micros = (long)(unixNanos / NanosPerMicrosecond);
        return DateTimeOffset.UnixEpoch.AddTicks(micros * TicksPerMicrosecond);
    }

    public static string Format(DateTimeOffset value) =>
        value.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'", System.Globalization.CultureInfo.InvariantCulture);
}
