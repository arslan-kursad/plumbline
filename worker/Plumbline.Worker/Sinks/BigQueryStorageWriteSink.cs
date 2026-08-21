using Plumbline.Normalization.Rows;

namespace Plumbline.Worker.Sinks;

/// <summary>
/// The cloud write path: BigQuery **Storage Write API**, default stream.
/// </summary>
/// <remarks>
/// <para>
/// Wiring only in F1. The phase is local-first and creates no GCP resource, so this class
/// carries the destination it would write to and the shape of the call, and refuses to
/// run rather than pretending to. It exists in F1 because the F1 directive (D4) asks for
/// the real client to be behind the sink interface before F2 deploys it, and because the
/// alternative — introducing the write path in the phase that also introduces the cloud —
/// puts two untested things in one deployment.
/// </para>
/// <para>
/// Two constraints fix the choice and are stated here because the class is where an
/// implementer will look. The write path is the Storage Write API and nothing else: the
/// legacy streaming-insert surface is forbidden by architecture §2.3 as a cost invariant,
/// and Gate A enforces it by refusing the package that exposes it, so the API cannot be
/// reached from this repository whatever a future author intends. The stream is the
/// **default stream**, which is at-least-once and matches §3.3; duplicates are removed
/// downstream by the `spans_deduped` view, not by an exactly-once committed stream.
/// </para>
/// </remarks>
public sealed class BigQueryStorageWriteSink : ISpanSink
{
    private readonly string project;
    private readonly string dataset;
    private readonly string table;

    public BigQueryStorageWriteSink(string project, string dataset, string table)
    {
        this.project = project;
        this.dataset = dataset;
        this.table = table;
    }

    public string Description => $"bigquery storage write api ({project}.{dataset}.{table}, default stream)";

    public Task WriteAsync(IReadOnlyList<SpanRow> rows, CancellationToken cancellationToken) =>
        throw new NotSupportedException(
            $"the BigQuery sink for {project}.{dataset}.{table} is wiring only in F1, which is local-first and " +
            "creates no GCP resource (F1 spec §4). It is implemented in F2, against a dataset Terraform owns. " +
            "Selecting it now is a configuration error, and failing here is deliberate: a sink that silently " +
            "dropped rows would look exactly like a working pipeline with no traffic.");
}
