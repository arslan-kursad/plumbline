using System.IO.Compression;
using System.Text.Json;
using Google.Protobuf;
using OpenTelemetry.Proto.Collector.Trace.V1;
using Plumbline.Normalization;
using Plumbline.Worker.Push;
using Plumbline.Worker.Sinks;

namespace Plumbline.Worker;

/// <summary>
/// The push endpoint: gunzip → deserialize → detect → normalize → redact → write.
/// </summary>
/// <remarks>
/// <para>
/// The status code is the acknowledgement. Pub/Sub ACKs a message on 2xx and NACKs it on
/// anything else, redelivering until the subscription's `max_delivery_attempts` routes it
/// to `traces-dlq` (§3.4). So the only decision this endpoint makes about a message is
/// which of those two it deserves, and it must never answer 2xx for a message it did not
/// store — a poison message ACKed is a poison message that reaches no dead-letter topic
/// and raises no alert.
/// </para>
/// <para>
/// Deduplication is deliberately absent. Delivery is at-least-once and duplicates are
/// removed downstream on `(trace_id, span_id)` by the `spans_deduped` view (§3.3). A
/// worker-side cache would be a second, weaker implementation of the same rule, correct
/// only for as long as one instance's memory outlives the redelivery window.
/// </para>
/// </remarks>
public sealed class IngestionEndpoint
{
    private readonly Normalizer normalizer;
    private readonly ISpanSink sink;
    private readonly IPushAuthenticator authenticator;
    private readonly ILogger<IngestionEndpoint> log;

    public IngestionEndpoint(Normalizer normalizer, ISpanSink sink, IPushAuthenticator authenticator,
        ILogger<IngestionEndpoint> log)
    {
        this.normalizer = normalizer;
        this.sink = sink;
        this.authenticator = authenticator;
        this.log = log;
    }

    public async Task<IResult> HandleAsync(HttpContext context, CancellationToken cancellationToken)
    {
        if (!authenticator.IsAuthentic(context.Request))
        {
            log.LogWarning("push request refused by {Auth}", authenticator.Description);
            return Results.StatusCode(StatusCodes.Status401Unauthorized);
        }

        PushEnvelope? envelope;
        try
        {
            envelope = await JsonSerializer.DeserializeAsync<PushEnvelope>(
                context.Request.Body, cancellationToken: cancellationToken);
        }
        catch (JsonException error)
        {
            // Not the payload — the envelope itself. Nothing will make this message
            // parseable, so it is refused and Pub/Sub carries it to the DLQ.
            log.LogError(error, "push envelope is not valid JSON");
            return Results.BadRequest("push envelope is not valid JSON");
        }

        var message = envelope?.Message;
        if (message?.Data is null)
        {
            log.LogError("push envelope carries no message data");
            return Results.BadRequest("push envelope carries no message data");
        }

        var attributes = message.Attributes ?? new Dictionary<string, string>();
        var apiKeyId = attributes.GetValueOrDefault("api_key_id", "");
        var hint = attributes.GetValueOrDefault("source_dialect");
        var contentEncoding = attributes.GetValueOrDefault("content_encoding", "gzip");

        ExportTraceServiceRequest request;
        try
        {
            var payload = Convert.FromBase64String(message.Data);
            var decompressed = contentEncoding == "gzip" ? Gunzip(payload) : payload;
            request = ExportTraceServiceRequest.Parser.ParseFrom(decompressed);
        }
        catch (Exception error) when (error is FormatException or InvalidDataException or InvalidProtocolBufferException)
        {
            // A poison message. Refusing it is the whole point: it will be redelivered,
            // exhaust its attempts, and land in traces-dlq where the depth alert can see
            // it. Swallowing it with a 200 would be silent degradation with a clean
            // dashboard.
            log.LogError(error, "poison message {MessageId} (attempt {Attempt}) refused: {Reason}",
                message.MessageId, message.DeliveryAttempt, error.Message);
            return Results.BadRequest($"payload could not be read: {error.Message}");
        }

        var result = normalizer.Normalize(request, new MessageEnvelope(apiKeyId, hint));

        foreach (var note in result.Notes)
        {
            // Reporting controls, not decorations (ADR-0003 "Enforcement"): an unknown
            // dialect and a hint mismatch are exactly the conditions that make a missing
            // or wrong mapping visible instead of invisible.
            log.LogWarning("normalization note [{Kind}] {Detail}", note.Kind, note.Detail);
        }

        try
        {
            await sink.WriteAsync(result.Rows, cancellationToken);
        }
        catch (Exception error)
        {
            // A write failure is transient until proven otherwise, and a NACK is how a
            // transient failure is retried. Answering 2xx here would drop the rows.
            log.LogError(error, "sink write failed for message {MessageId}", message.MessageId);
            return Results.StatusCode(StatusCodes.Status503ServiceUnavailable);
        }

        log.LogInformation(
            "ingested message {MessageId}: {Rows} row(s), api_key_id={ApiKeyId}, redacted={Redacted}",
            message.MessageId, result.Rows.Count, apiKeyId, result.RedactedValues);

        return Results.NoContent();
    }

    private static byte[] Gunzip(byte[] payload)
    {
        using var source = new MemoryStream(payload);
        using var gzip = new GZipStream(source, CompressionMode.Decompress);
        using var target = new MemoryStream();
        gzip.CopyTo(target);
        return target.ToArray();
    }
}
