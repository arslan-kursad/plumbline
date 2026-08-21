using System.Text.Json.Nodes;
using Plumbline.Normalization.Rows;

namespace Plumbline.Fixtures;

/// <summary>
/// Compares rows observed at the end of the pipeline against the fixtures that produced
/// them.
/// </summary>
/// <remarks>
/// <para>
/// The end-to-end run's assertion is not "some rows arrived" but "these rows arrived",
/// and the expectation it compares against is the same <c>expected-rows.json</c> the
/// golden tests use — so the local pipeline and the unit-level normalizer are held to one
/// contract rather than two that drift.
/// </para>
/// <para>
/// Rows are matched to fixtures by <c>trace_id</c>, which every fixture gives a distinct
/// value. That also makes the check order-independent: what a query returns in which
/// order is the query's business.
/// </para>
/// </remarks>
public static class RowVerifier
{
    /// <summary>Columns the comparison ignores, and why each one has to be ignored.</summary>
    private static readonly Dictionary<string, string> Ignored = new(StringComparer.Ordinal)
    {
        // Stamped by the sink at write time. Asserting a value would be asserting a clock.
        ["ingest_time"] = "worker write time",
    };

    public static int Verify(string fixtureRoot, string observedPath, TextWriter output)
    {
        var expectedByTrace = LoadExpected(fixtureRoot);
        var observedByTrace = LoadObserved(observedPath);

        var failures = 0;

        foreach (var (label, expected) in expectedByTrace.OrderBy(pair => pair.Key.Label, StringComparer.Ordinal)
                     .Select(pair => (pair.Key.Label, pair.Value)))
        {
            var traceId = expected[0]!["trace_id"]!.ToString();

            if (!observedByTrace.TryGetValue(traceId, out var observed))
            {
                output.WriteLine($"{label}: no rows reached the pipeline (trace {traceId})");
                failures++;
                continue;
            }

            var diffs = RowDiff.Compare(expected, observed);
            if (diffs.Count > 0)
            {
                output.WriteLine(RowDiff.Describe(label, diffs));
                failures++;
                continue;
            }

            output.WriteLine($"  ok    {label}: {expected.Count} row(s) match the golden file");
        }

        var expectedTraces = expectedByTrace.Values
            .Select(rows => rows[0]!["trace_id"]!.ToString())
            .ToHashSet(StringComparer.Ordinal);

        foreach (var traceId in observedByTrace.Keys.Where(id => !expectedTraces.Contains(id)))
        {
            output.WriteLine($"unexpected trace in the pipeline output: {traceId}");
            failures++;
        }

        return failures;
    }

    private static Dictionary<(string Label, string Path), JsonArray> LoadExpected(string fixtureRoot)
    {
        var expected = new Dictionary<(string, string), JsonArray>();

        foreach (var path in Directory.EnumerateFiles(fixtureRoot, "expected-rows.json", SearchOption.AllDirectories))
        {
            var caseDir = Path.GetDirectoryName(path)!;
            var label = $"{Path.GetFileName(Path.GetDirectoryName(caseDir))}/{Path.GetFileName(caseDir)}";

            var rows = JsonNode.Parse(File.ReadAllText(path)) as JsonArray
                       ?? throw new InvalidDataException($"{path} is not a JSON array");

            expected[(label, path)] = rows;
        }

        return expected;
    }

    private static Dictionary<string, JsonArray> LoadObserved(string path)
    {
        var byTrace = new Dictionary<string, JsonArray>(StringComparer.Ordinal);

        foreach (var line in File.ReadAllLines(path).Where(line => line.Length > 0))
        {
            var row = JsonNode.Parse(line) as JsonObject
                      ?? throw new InvalidDataException($"{path}: a line is not a JSON object");

            foreach (var column in Ignored.Keys)
            {
                row.Remove(column);
            }

            // Column order is a property of the golden files, not of a query result.
            var ordered = new JsonObject();
            foreach (var column in SpanRow.Columns)
            {
                ordered[column] = row.TryGetPropertyValue(column, out var value) ? value?.DeepClone() : null;
            }

            var traceId = ordered["trace_id"]!.ToString();
            if (!byTrace.TryGetValue(traceId, out var rows))
            {
                rows = new JsonArray();
                byTrace[traceId] = rows;
            }

            rows.Add(ordered);
        }

        // Within a trace, order by span id so the comparison does not depend on the
        // order a query happened to return.
        foreach (var (traceId, rows) in byTrace.ToList())
        {
            var sorted = new JsonArray(rows
                .OrderBy(row => row!["span_id"]!.ToString(), StringComparer.Ordinal)
                .Select(row => row!.DeepClone())
                .ToArray());
            byTrace[traceId] = sorted;
        }

        return byTrace;
    }
}
