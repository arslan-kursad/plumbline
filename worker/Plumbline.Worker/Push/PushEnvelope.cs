using System.Text.Json.Serialization;

namespace Plumbline.Worker.Push;

/// <summary>The Pub/Sub push envelope, as delivered to the endpoint.</summary>
/// <remarks>
/// Only the fields this worker uses are modelled. `data` is the base64-encoded message
/// payload — for this pipeline, one gzipped OTLP <c>ExportTraceServiceRequest</c> — and
/// `attributes` is the message attribute set fixed by architecture §3.2.
/// </remarks>
public sealed class PushEnvelope
{
    [JsonPropertyName("message")]
    public PushMessage? Message { get; set; }

    [JsonPropertyName("subscription")]
    public string? Subscription { get; set; }
}

public sealed class PushMessage
{
    [JsonPropertyName("data")]
    public string? Data { get; set; }

    [JsonPropertyName("attributes")]
    public Dictionary<string, string>? Attributes { get; set; }

    [JsonPropertyName("messageId")]
    public string? MessageId { get; set; }

    [JsonPropertyName("publishTime")]
    public string? PublishTime { get; set; }

    /// <summary>
    /// How many times Pub/Sub has attempted delivery, when the subscription is configured
    /// with a dead-letter policy.
    /// </summary>
    /// <remarks>
    /// Logged rather than acted on. The worker does not decide when a message has failed
    /// enough times — the subscription's `max_delivery_attempts` does, and it routes to
    /// `traces-dlq` on its own (§3.4). A worker that started giving up at its own count
    /// would ACK a poison message and the DLQ would stay empty, which is the exact
    /// silent-degradation this design refuses.
    /// </remarks>
    [JsonPropertyName("deliveryAttempt")]
    public int? DeliveryAttempt { get; set; }
}
