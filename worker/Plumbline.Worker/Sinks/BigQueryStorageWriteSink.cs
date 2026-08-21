using Google.Cloud.BigQuery.Storage.V1;
using Google.Protobuf;
using Google.Protobuf.Reflection;
using Grpc.Core;
using Plumbline.Normalization.Rows;
using Plumbline.Normalization.Storage;

namespace Plumbline.Worker.Sinks;

/// <summary>
/// The permitted BigQuery write path: **Storage Write API**, default stream.
/// </summary>
/// <remarks>
/// <para>
/// The legacy streaming-insert surface is forbidden as a cost invariant (architecture
/// §2.3, §7) and is unreachable from this repository: Gate A fails the build if
/// `Google.Cloud.BigQuery.V2` appears in any project file, so the API cannot be called
/// whatever a future author intends. This class is the only writer.
/// </para>
/// <para>
/// The **default stream** rather than a committed one. It is at-least-once, which matches
/// the delivery semantics the whole pipeline already has (§3.3), and duplicates are
/// removed downstream by `spans_deduped` — a committed stream would buy exactly-once at
/// the price of stream lifecycle management for a property the views already provide.
/// </para>
/// <para>
/// Rows travel as serialized <see cref="SpanRowProto"/> plus its descriptor, which is
/// what the API takes. `proto/span_row.proto` is the wire twin of
/// `analytics/sql/001_spans_table.sql`, and a test compares the two rather than trusting
/// that they were kept in step.
/// </para>
/// </remarks>
public sealed class BigQueryStorageWriteSink : ISpanSink, IAsyncDisposable
{
    private readonly string tablePath;
    private readonly string destination;
    private readonly BigQueryWriteClient client;
    private readonly TimeProvider clock;

    private BigQueryWriteClient.AppendRowsStream? stream;
    private readonly SemaphoreSlim streamLock = new(1, 1);

    public BigQueryStorageWriteSink(string project, string dataset, string table, string? emulatorEndpoint,
        TimeProvider? clock = null)
    {
        this.clock = clock ?? TimeProvider.System;
        tablePath = $"projects/{project}/datasets/{dataset}/tables/{table}";
        destination = $"{project}.{dataset}.{table}";

        var builder = new BigQueryWriteClientBuilder();
        if (!string.IsNullOrEmpty(emulatorEndpoint))
        {
            // The local stand-in speaks plaintext gRPC and wants no credentials. This is
            // the only branch in the write path that knows about the emulator, and it is
            // configuration rather than a second implementation — the API calls below are
            // the same ones the cloud takes.
            builder.Endpoint = emulatorEndpoint;
            builder.ChannelCredentials = ChannelCredentials.Insecure;
            builder.GoogleCredential = null;
            builder.CredentialsPath = null;
        }

        client = builder.Build();
    }

    public string Description => $"bigquery storage write api ({destination}, default stream)";

    public async Task WriteAsync(IReadOnlyList<SpanRow> rows, CancellationToken cancellationToken)
    {
        if (rows.Count == 0)
        {
            return;
        }

        var ingestTime = ToMicroseconds(clock.GetUtcNow());
        var serialized = new ProtoRows();
        foreach (var row in rows)
        {
            serialized.SerializedRows.Add(ToProto(row, ingestTime).ToByteString());
        }

        var request = new AppendRowsRequest
        {
            WriteStreamAsWriteStreamName = WriteStreamName.FromProjectDatasetTableStream(
                ProjectOf(tablePath), DatasetOf(tablePath), TableOf(tablePath), "_default"),
            ProtoRows = new AppendRowsRequest.Types.ProtoData
            {
                WriterSchema = new ProtoSchema { ProtoDescriptor = WriterDescriptor },
                Rows = serialized,
            },
        };

        await streamLock.WaitAsync(cancellationToken);
        try
        {
            stream ??= client.AppendRows();
            await stream.WriteAsync(request);

            // Wait for the append to be acknowledged before the caller is told the write
            // succeeded. Returning early would let the worker ACK a Pub/Sub message whose
            // rows are still in flight, and a failure after that point has nothing left
            // to retry from.
            var responses = stream.GetResponseStream();
            if (!await responses.MoveNextAsync(cancellationToken))
            {
                throw new InvalidOperationException($"the append stream to {destination} closed without responding");
            }

            var response = responses.Current;
            if (response.Error is { Code: not 0 })
            {
                throw new InvalidOperationException(
                    $"append to {destination} failed: {response.Error.Code} {response.Error.Message}");
            }
        }
        catch
        {
            // A broken stream stays broken; drop it so the next write reconnects rather
            // than replaying the same failure forever.
            var broken = stream;
            stream = null;
            if (broken is not null)
            {
                try
                {
                    await broken.WriteCompleteAsync();
                }
                catch
                {
                    // The stream is already failing; its shutdown error is not the one
                    // worth reporting.
                }
            }

            throw;
        }
        finally
        {
            streamLock.Release();
        }
    }

    /// <summary>
    /// The row descriptor as the Storage Write API wants it.
    /// </summary>
    /// <remarks>
    /// <para>
    /// The API takes a <c>DescriptorProto</c>, which carries no file-level <c>syntax</c>,
    /// so the server reads it with proto2 semantics. C# only generates proto3, and proto3
    /// spells explicit presence as `optional` — which protoc implements with a
    /// `proto3_optional` flag and a synthetic one-of per field. Handed to a proto2 reader
    /// those markers are invalid, and the server rejects the whole append:
    /// </para>
    /// <code>
    /// failed to create file descriptor: proto: message field "SpanRowProto.start_time"
    /// under proto3 optional semantics must be specified in the proto3 syntax
    /// </code>
    /// <para>
    /// Stripping the two markers turns the descriptor into the proto2 form the API
    /// expects: every field stays `LABEL_OPTIONAL`, which is what carries presence there.
    /// The serialized rows are untouched — a proto3 optional field and a proto2 optional
    /// field have identical wire encodings, so this changes what the schema *says* and
    /// not a single byte of what is written.
    /// </para>
    /// </remarks>
    internal static DescriptorProto WriterDescriptor { get; } = ProtoTwoStyle(SpanRowProto.Descriptor.ToProto());

    private static DescriptorProto ProtoTwoStyle(DescriptorProto descriptor)
    {
        foreach (var field in descriptor.Field)
        {
            field.ClearProto3Optional();
            field.ClearOneofIndex();
        }

        descriptor.OneofDecl.Clear();
        return descriptor;
    }

    internal static SpanRowProto ToProto(SpanRow row, long ingestTimeMicroseconds)
    {
        var proto = new SpanRowProto
        {
            StartTime = ToMicroseconds(row.StartTime),
            EndTime = ToMicroseconds(row.EndTime),
            TraceId = row.TraceId,
            SpanId = row.SpanId,
            Name = row.Name,
            Kind = row.Kind,
            StatusCode = row.StatusCode,
            SourceDialect = row.SourceDialect,
            Synthetic = row.Synthetic,
            Attributes = row.Attributes.ToJsonString(),
            Events = row.Events.ToJsonString(),
            Links = row.Links.ToJsonString(),
            IngestTime = ingestTimeMicroseconds,
        };

        // Optional fields are left unset rather than set to a default: BigQuery stores an
        // unset optional as NULL, and NULL is what "this dialect does not emit token
        // counts" means. Writing 0 would turn a measurement into a claim.
        Set(row.ParentSpanId, value => proto.ParentSpanId = value);
        Set(row.StatusMessage, value => proto.StatusMessage = value);
        Set(row.ServiceName, value => proto.ServiceName = value);
        Set(row.ApiKeyId, value => proto.ApiKeyId = value);
        Set(row.SchemaUrl, value => proto.SchemaUrl = value);
        Set(row.GenAiProviderName, value => proto.GenAiProviderName = value);
        Set(row.GenAiOperationName, value => proto.GenAiOperationName = value);
        Set(row.GenAiRequestModel, value => proto.GenAiRequestModel = value);
        Set(row.GenAiResponseModel, value => proto.GenAiResponseModel = value);
        Set(row.GenAiResponseId, value => proto.GenAiResponseId = value);
        Set(row.GenAiConversationId, value => proto.GenAiConversationId = value);
        Set(row.GenAiAgentName, value => proto.GenAiAgentName = value);
        Set(row.GenAiToolName, value => proto.GenAiToolName = value);
        Set(row.GenAiToolCallId, value => proto.GenAiToolCallId = value);
        Set(row.GenAiOutputType, value => proto.GenAiOutputType = value);
        Set(row.GenAiUsageInputTokens, value => proto.GenAiUsageInputTokens = value);
        Set(row.GenAiUsageOutputTokens, value => proto.GenAiUsageOutputTokens = value);
        Set(row.GenAiRequestMaxTokens, value => proto.GenAiRequestMaxTokens = value);
        Set(row.GenAiRequestTemperature, value => proto.GenAiRequestTemperature = value);
        Set(row.GenAiRequestTopP, value => proto.GenAiRequestTopP = value);

        return proto;
    }

    private static void Set<T>(T? value, Action<T> assign) where T : class
    {
        if (value is not null)
        {
            assign(value);
        }
    }

    private static void Set<T>(T? value, Action<T> assign) where T : struct
    {
        if (value.HasValue)
        {
            assign(value.Value);
        }
    }

    internal static long ToMicroseconds(DateTimeOffset value) =>
        (value.UtcDateTime - DateTime.UnixEpoch).Ticks / TimeSpan.TicksPerMicrosecond;

    private static string ProjectOf(string path) => path.Split('/')[1];

    private static string DatasetOf(string path) => path.Split('/')[3];

    private static string TableOf(string path) => path.Split('/')[5];

    public async ValueTask DisposeAsync()
    {
        if (stream is not null)
        {
            try
            {
                await stream.WriteCompleteAsync();
            }
            catch
            {
                // Shutdown of an already-failed stream is not worth surfacing.
            }
        }

        streamLock.Dispose();
    }
}
