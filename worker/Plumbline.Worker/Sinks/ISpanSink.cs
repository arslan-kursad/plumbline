using Plumbline.Normalization.Rows;

namespace Plumbline.Worker.Sinks;

/// <summary>Where normalized rows go.</summary>
/// <remarks>
/// <para>
/// The abstraction exists for one reason and it is not testability: F1 is local-first and
/// must not touch BigQuery, while the write path it is building has exactly one permitted
/// implementation in the cloud (Storage Write API, architecture §2.3). An interface with
/// a local implementation lets the pipeline be exercised end to end without a cloud
/// resource, and lets the real client be wired and reviewed before F2 deploys it.
/// </para>
/// <para>
/// What the interface does **not** do is soften the cost invariant. There is no
/// implementation over the legacy streaming-insert path in either branch, and there
/// cannot be: Gate A fails the build if `Google.Cloud.BigQuery.V2` appears in any
/// project file, so the surface is unreachable rather than merely unused.
/// </para>
/// </remarks>
public interface ISpanSink
{
    /// <summary>Name of the sink, for the startup log.</summary>
    string Description { get; }

    /// <summary>
    /// Writes rows, stamping each with the ingest time.
    /// </summary>
    /// <remarks>
    /// `ingest_time` is the worker's write time (architecture §4.1) and so belongs to the
    /// sink rather than to normalization — which also keeps golden comparisons free of a
    /// clock without anyone having to exclude a column.
    /// </remarks>
    Task WriteAsync(IReadOnlyList<SpanRow> rows, CancellationToken cancellationToken);
}
