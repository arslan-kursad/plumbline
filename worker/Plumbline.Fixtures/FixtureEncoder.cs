using System.Text.Json;
using System.Text.Json.Nodes;
using Google.Protobuf;
using OpenTelemetry.Proto.Collector.Trace.V1;

namespace Plumbline.Fixtures;

/// <summary>
/// Turns the human-readable OTLP/JSON twin of a fixture into the protobuf bytes the
/// pipeline actually carries.
/// </summary>
public static class FixtureEncoder
{
    private static readonly string[] IdFields =
    {
        "traceId", "spanId", "parentSpanId", "trace_id", "span_id", "parent_span_id",
    };

    /// <summary>Parses an OTLP/JSON twin and returns its protobuf encoding.</summary>
    /// <remarks>
    /// OTLP/JSON encodes trace and span ids as lowercase hex, while canonical protobuf
    /// JSON — which <see cref="JsonParser"/> implements — encodes every <c>bytes</c>
    /// field as base64. The twins are written in the OTLP form, because that is what an
    /// OTLP/HTTP JSON exporter puts on the wire and what a reader recognises; the id
    /// fields are re-encoded here rather than base64 being pushed onto the author.
    /// Unknown fields are rejected, so a mistyped key fails the fixture instead of
    /// vanishing from the payload.
    /// </remarks>
    public static byte[] Encode(string twinJson) => Parse(twinJson).ToByteArray();

    /// <summary>The same parse, stopping at the request rather than its bytes.</summary>
    /// <remarks>
    /// Split out so the cloud harness can normalize a corpus locally
    /// (<see cref="CorpusNormalizer"/>, directive v1.7 Decision 12) without a second copy
    /// of the id-rewriting rule above. One parse, two callers.
    /// </remarks>
    public static ExportTraceServiceRequest Parse(string twinJson)
    {
        var node = JsonNode.Parse(twinJson, documentOptions: new JsonDocumentOptions { CommentHandling = JsonCommentHandling.Skip })
                   ?? throw new InvalidDataException("twin is empty");
        RewriteIds(node);

        return ExportTraceServiceRequest.Parser
            .WithDiscardUnknownFields(false)
            .ParseJson(node.ToJsonString());
    }

    private static void RewriteIds(JsonNode node)
    {
        switch (node)
        {
            case JsonObject obj:
                foreach (var name in IdFields)
                {
                    if (obj[name] is JsonValue value && value.TryGetValue<string>(out var hex) && hex.Length > 0)
                    {
                        obj[name] = Convert.ToBase64String(Convert.FromHexString(hex));
                    }
                }

                foreach (var child in obj.ToList())
                {
                    if (child.Value is not null)
                    {
                        RewriteIds(child.Value);
                    }
                }

                break;

            case JsonArray array:
                foreach (var item in array)
                {
                    if (item is not null)
                    {
                        RewriteIds(item);
                    }
                }

                break;
        }
    }
}
