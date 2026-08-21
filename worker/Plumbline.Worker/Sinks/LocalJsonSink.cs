using System.Text.Json;
using System.Text.Json.Nodes;
using Plumbline.Normalization.Rows;

namespace Plumbline.Worker.Sinks;

/// <summary>
/// Writes rows as newline-delimited JSON to a directory, for the local end-to-end path.
/// </summary>
/// <remarks>
/// One file per write, named by write time and a counter, so a run's output is a
/// directory the end-to-end check can load and diff against the golden expectations. The
/// format is the same JSON the golden files hold, which is what makes that comparison
/// meaningful rather than an approximation of it.
/// </remarks>
public sealed class LocalJsonSink : ISpanSink
{
    private readonly string directory;
    private readonly TimeProvider clock;
    private int sequence;

    public LocalJsonSink(string directory, TimeProvider? clock = null)
    {
        this.directory = directory;
        this.clock = clock ?? TimeProvider.System;
        Directory.CreateDirectory(directory);
    }

    public string Description => $"local json ({directory})";

    public async Task WriteAsync(IReadOnlyList<SpanRow> rows, CancellationToken cancellationToken)
    {
        if (rows.Count == 0)
        {
            return;
        }

        var ingestTime = Timestamps.Format(clock.GetUtcNow());
        var lines = new List<string>(rows.Count);

        foreach (var row in rows)
        {
            var json = row.ToJson();
            json["ingest_time"] = ingestTime;
            lines.Add(json.ToJsonString(new JsonSerializerOptions { WriteIndented = false }));
        }

        var name = $"{clock.GetUtcNow():yyyyMMdd'T'HHmmss'.'fff}-{Interlocked.Increment(ref sequence):D6}.ndjson";
        await File.WriteAllLinesAsync(Path.Combine(directory, name), lines, cancellationToken);
    }
}
