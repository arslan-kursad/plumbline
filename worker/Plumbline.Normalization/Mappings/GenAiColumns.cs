namespace Plumbline.Normalization.Mappings;

/// <summary>The value type a typed column holds, and therefore how a source is coerced.</summary>
public enum ColumnType
{
    String,
    Int,
    Double,
}

/// <summary>One typed <c>gen_ai_*</c> column and the v1.41 attribute it stands for.</summary>
public sealed record GenAiColumn(string Column, string Semconv, ColumnType Type);

/// <summary>
/// The typed GenAI column set, and the semconv attribute each column carries.
/// </summary>
/// <remarks>
/// <para>
/// Architecture §4.1 delegates the exact list to the mapping table. This is that list,
/// in one place, for three reasons: every dialect mapping must agree with it — a YAML
/// naming a column that does not exist here fails a test rather than writing to nothing;
/// the unknown-dialect path is generated from it, so the generic mapping is not a second
/// implementation that can drift; and the semconv conformance check has a list of names
/// to validate against the vendored registry.
/// </para>
/// <para>
/// Scalars only. Array-valued GenAI attributes stay in the lossless attributes column
/// (decision log W2.4).
/// </para>
/// </remarks>
public static class GenAiColumns
{
    public static IReadOnlyList<GenAiColumn> All { get; } = new GenAiColumn[]
    {
        new("gen_ai_provider_name", "gen_ai.provider.name", ColumnType.String),
        new("gen_ai_operation_name", "gen_ai.operation.name", ColumnType.String),
        new("gen_ai_request_model", "gen_ai.request.model", ColumnType.String),
        new("gen_ai_response_model", "gen_ai.response.model", ColumnType.String),
        new("gen_ai_response_id", "gen_ai.response.id", ColumnType.String),
        new("gen_ai_conversation_id", "gen_ai.conversation.id", ColumnType.String),
        new("gen_ai_agent_name", "gen_ai.agent.name", ColumnType.String),
        new("gen_ai_tool_name", "gen_ai.tool.name", ColumnType.String),
        new("gen_ai_tool_call_id", "gen_ai.tool.call.id", ColumnType.String),
        new("gen_ai_usage_input_tokens", "gen_ai.usage.input_tokens", ColumnType.Int),
        new("gen_ai_usage_output_tokens", "gen_ai.usage.output_tokens", ColumnType.Int),
        new("gen_ai_request_max_tokens", "gen_ai.request.max_tokens", ColumnType.Int),
        new("gen_ai_request_temperature", "gen_ai.request.temperature", ColumnType.Double),
        new("gen_ai_request_top_p", "gen_ai.request.top_p", ColumnType.Double),
        new("gen_ai_output_type", "gen_ai.output.type", ColumnType.String),
    };

    public static IReadOnlyDictionary<string, GenAiColumn> ByName { get; } =
        All.ToDictionary(c => c.Column, StringComparer.Ordinal);
}
