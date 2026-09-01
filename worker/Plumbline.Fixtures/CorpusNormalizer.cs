using System.Text.Json.Nodes;
using Plumbline.Normalization;
using Plumbline.Normalization.Rows;

namespace Plumbline.Fixtures;

/// <summary>
/// Normalizes a run-scoped corpus locally, so the cloud harness has something to diff
/// against that is not a second description of the same expectation.
/// </summary>
/// <remarks>
/// <para>
/// F2 completion directive v1.7, Decision 12: the golden diff compares cloud-normalized
/// rows against <b>the same corpus normalized locally</b>. The committed
/// <c>expected-rows.json</c> files cannot serve that purpose for a cloud run, because the
/// corpus carries a per-run identity and a per-run attribute (Decision 6, issue #102) and
/// a checked-in file cannot hold either.
/// </para>
/// <para>
/// This runs the same <see cref="Normalizer"/> the worker runs, not a reimplementation of
/// it. If the two ever diverge the diff stops meaning anything, so there is deliberately
/// no second code path here to keep in step.
/// </para>
/// <para>
/// The <c>api_key_id</c> is passed in rather than defaulted. It is the reason that column
/// is not on the volatile list: the cloud run's key id is handed to this path, so the two
/// sides agree by construction instead of by exclusion.
/// </para>
/// </remarks>
public static class CorpusNormalizer
{
    public static int Normalize(string corpusDir, string outputPath, string apiKeyId, TextWriter output)
    {
        if (!Directory.Exists(corpusDir))
        {
            output.WriteLine($"corpus directory does not exist: {corpusDir}");
            return 2;
        }

        var twins = Directory.EnumerateFiles(corpusDir, "*.otlp.json", SearchOption.AllDirectories)
            .OrderBy(path => path, StringComparer.Ordinal)
            .ToList();

        if (twins.Count == 0)
        {
            output.WriteLine($"no *.otlp.json payloads under {corpusDir}");
            return 2;
        }

        var rows = new List<JsonObject>();
        var notes = 0;

        foreach (var twin in twins)
        {
            var request = FixtureEncoder.Parse(File.ReadAllText(twin));

            // The dialect hint is left null on purpose: the cloud path carries whatever
            // the collector set, and detection is what the diff is partly testing. Pinning
            // a hint here would make both sides agree for a reason the pipeline does not.
            var result = Normalizer.Default.Normalize(request, new MessageEnvelope(apiKeyId, null));

            foreach (var note in result.Notes)
            {
                output.WriteLine($"  note  {Path.GetFileName(twin)}: {note.Kind} — {note.Detail}");
                notes++;
            }

            rows.AddRange(result.Rows.Select(row => row.ToJson()));
        }

        // Stable order, so a diff against the cloud rows is a diff about content. The
        // cloud side sorts the same way; what a query returns in which order is the
        // query's business (RowVerifier makes the same argument).
        var ordered = rows
            .OrderBy(row => row["trace_id"]!.ToString(), StringComparer.Ordinal)
            .ThenBy(row => row["span_id"]!.ToString(), StringComparer.Ordinal)
            .ToList();

        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath))!);
        using (var writer = new StreamWriter(outputPath))
        {
            foreach (var row in ordered)
            {
                foreach (var column in VolatileFields.Excluded.Keys)
                {
                    row.Remove(column);
                }

                writer.WriteLine(row.ToJsonString());
            }
        }

        output.WriteLine($"normalized {twins.Count} payload(s) into {ordered.Count} row(s) -> {outputPath}");
        output.WriteLine("columns not compared (directive Decision 12):");
        output.WriteLine(VolatileFields.Describe());
        if (notes > 0)
        {
            output.WriteLine($"{notes} normalization note(s); these are reported, not failures (ADR-0003)");
        }

        return 0;
    }
}
