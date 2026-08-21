using System.Text.Json.Nodes;
using Google.Protobuf;
using OpenTelemetry.Proto.Common.V1;

namespace Plumbline.Normalization;

/// <summary>
/// Converts OTLP <c>AnyValue</c> into JSON, for the lossless attributes column.
/// </summary>
/// <remarks>
/// Every OTLP value case is handled, including the nested ones. "Lossless" is the whole
/// claim of the <c>attributes</c> column (ADR-0001 §2), so a value case that silently
/// became null here would break it in the one place nothing else would notice.
/// </remarks>
public static class AttributeValues
{
    public static JsonNode? ToJson(AnyValue? value) => value?.ValueCase switch
    {
        AnyValue.ValueOneofCase.StringValue => JsonValue.Create(value.StringValue),
        AnyValue.ValueOneofCase.BoolValue => JsonValue.Create(value.BoolValue),
        AnyValue.ValueOneofCase.IntValue => JsonValue.Create(value.IntValue),
        AnyValue.ValueOneofCase.DoubleValue => JsonValue.Create(value.DoubleValue),
        AnyValue.ValueOneofCase.ArrayValue => new JsonArray(
            value.ArrayValue.Values.Select(ToJson).ToArray()),
        AnyValue.ValueOneofCase.KvlistValue => ToJson(value.KvlistValue.Values),
        // Bytes have no JSON representation; base64 is what protobuf's own JSON mapping
        // uses, so a reader who meets one knows how to decode it.
        AnyValue.ValueOneofCase.BytesValue => JsonValue.Create(value.BytesValue.ToBase64()),
        _ => null,
    };

    public static JsonObject ToJson(IEnumerable<KeyValue> attributes)
    {
        var json = new JsonObject();
        foreach (var attribute in attributes)
        {
            // Last write wins on a duplicate key. OTLP does not forbid one, JSON has no
            // way to hold both, and dropping the later value would be the more
            // surprising of the two losses.
            json[attribute.Key] = ToJson(attribute.Value);
        }

        return json;
    }

    /// <summary>Reads one attribute's raw value, for the typed columns and for detection.</summary>
    public static AnyValue? Find(IEnumerable<KeyValue> attributes, string key)
    {
        foreach (var attribute in attributes)
        {
            if (string.Equals(attribute.Key, key, StringComparison.Ordinal))
            {
                return attribute.Value;
            }
        }

        return null;
    }

    /// <summary>Renders a value as a string for comparison and for string columns.</summary>
    public static string? AsString(AnyValue? value) => value?.ValueCase switch
    {
        AnyValue.ValueOneofCase.StringValue => value.StringValue,
        AnyValue.ValueOneofCase.BoolValue => value.BoolValue ? "true" : "false",
        AnyValue.ValueOneofCase.IntValue => value.IntValue.ToString(System.Globalization.CultureInfo.InvariantCulture),
        AnyValue.ValueOneofCase.DoubleValue => value.DoubleValue.ToString("R", System.Globalization.CultureInfo.InvariantCulture),
        _ => null,
    };
}
