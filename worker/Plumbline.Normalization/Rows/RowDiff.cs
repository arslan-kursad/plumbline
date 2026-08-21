using System.Globalization;
using System.Text;
using System.Text.Json.Nodes;

namespace Plumbline.Normalization.Rows;

/// <summary>One difference between an expected row and an actual one, located by path.</summary>
public sealed record RowDifference(string Path, string Kind, string? Expected, string? Actual)
{
    public override string ToString() => Kind switch
    {
        "missing" => $"{Path}: missing — expected {Expected}",
        "unexpected" => $"{Path}: unexpected — actual {Actual}",
        _ => $"{Path}: expected {Expected}, actual {Actual}",
    };
}

/// <summary>
/// Field-level comparison of normalized rows.
/// </summary>
/// <remarks>
/// Golden-file tests are the enforcement mechanism for ADR-0001 §3.1, which makes their
/// failure output part of the deliverable rather than a convenience: a test that reports
/// "expected 4.2 kB of JSON, got 4.2 kB of JSON" tells the reader that something broke
/// and nothing about what, and the practical response to it is to overwrite the golden
/// file. So every difference is reported with the path that reaches it —
/// <c>rows[1].attributes.span.llm.model_name</c> — and all differences are reported, not
/// just the first, because mapping regressions arrive in groups.
/// </remarks>
public static class RowDiff
{
    /// <summary>Compares two row arrays and returns every difference found.</summary>
    public static IReadOnlyList<RowDifference> Compare(JsonArray expected, JsonArray actual)
    {
        var diffs = new List<RowDifference>();
        var shared = Math.Min(expected.Count, actual.Count);

        for (var i = 0; i < shared; i++)
        {
            CompareNode($"rows[{i}]", expected[i], actual[i], diffs);
        }

        for (var i = shared; i < expected.Count; i++)
        {
            diffs.Add(new RowDifference($"rows[{i}]", "missing", Describe(expected[i]), null));
        }

        for (var i = shared; i < actual.Count; i++)
        {
            diffs.Add(new RowDifference($"rows[{i}]", "unexpected", null, Describe(actual[i])));
        }

        return diffs;
    }

    /// <summary>
    /// Renders differences for a test failure message: the count first, so the reader
    /// knows whether this is one wrong field or a shape change, then one line each.
    /// </summary>
    public static string Describe(string label, IReadOnlyList<RowDifference> diffs)
    {
        if (diffs.Count == 0)
        {
            return $"{label}: no differences";
        }

        var text = new StringBuilder();
        text.Append(label).Append(": ").Append(diffs.Count).Append(diffs.Count == 1 ? " difference" : " differences");
        text.AppendLine();

        foreach (var diff in diffs)
        {
            text.Append("  ").AppendLine(diff.ToString());
        }

        return text.ToString();
    }

    private static void CompareNode(string path, JsonNode? expected, JsonNode? actual, List<RowDifference> diffs)
    {
        if (expected is null || actual is null)
        {
            if (!(expected is null && actual is null))
            {
                diffs.Add(new RowDifference(path, "value", Describe(expected), Describe(actual)));
            }

            return;
        }

        switch (expected)
        {
            case JsonObject expectedObject when actual is JsonObject actualObject:
                CompareObjects(path, expectedObject, actualObject, diffs);
                return;

            case JsonArray expectedArray when actual is JsonArray actualArray:
                CompareArrays(path, expectedArray, actualArray, diffs);
                return;

            case JsonObject or JsonArray:
            case JsonValue when actual is JsonObject or JsonArray:
                diffs.Add(new RowDifference(path, "type", Describe(expected), Describe(actual)));
                return;
        }

        var left = Describe(expected);
        var right = Describe(actual);
        if (!string.Equals(left, right, StringComparison.Ordinal))
        {
            diffs.Add(new RowDifference(path, "value", left, right));
        }
    }

    private static void CompareObjects(string path, JsonObject expected, JsonObject actual, List<RowDifference> diffs)
    {
        foreach (var (key, value) in expected)
        {
            if (actual.TryGetPropertyValue(key, out var actualValue))
            {
                CompareNode(Join(path, key), value, actualValue, diffs);
            }
            else
            {
                diffs.Add(new RowDifference(Join(path, key), "missing", Describe(value), null));
            }
        }

        foreach (var (key, value) in actual)
        {
            if (!expected.ContainsKey(key))
            {
                diffs.Add(new RowDifference(Join(path, key), "unexpected", null, Describe(value)));
            }
        }
    }

    private static void CompareArrays(string path, JsonArray expected, JsonArray actual, List<RowDifference> diffs)
    {
        var shared = Math.Min(expected.Count, actual.Count);
        for (var i = 0; i < shared; i++)
        {
            CompareNode($"{path}[{i}]", expected[i], actual[i], diffs);
        }

        for (var i = shared; i < expected.Count; i++)
        {
            diffs.Add(new RowDifference($"{path}[{i}]", "missing", Describe(expected[i]), null));
        }

        for (var i = shared; i < actual.Count; i++)
        {
            diffs.Add(new RowDifference($"{path}[{i}]", "unexpected", null, Describe(actual[i])));
        }
    }

    /// <summary>
    /// Attribute keys contain dots, so a path is bracketed whenever the segment is not a
    /// plain identifier — otherwise <c>attributes.span.llm.model_name</c> would read as
    /// four levels of nesting when it is two levels and one dotted key.
    /// </summary>
    private static string Join(string path, string key) =>
        key.All(c => char.IsLetterOrDigit(c) || c == '_') ? $"{path}.{key}" : $"{path}[\"{key}\"]";

    private static string? Describe(JsonNode? node) => node switch
    {
        null => "null",
        JsonObject obj => $"object with {obj.Count} field(s)",
        JsonArray arr => $"array of {arr.Count}",
        JsonValue value when value.TryGetValue<string>(out var s) => $"\"{s}\"",
        JsonValue value when value.TryGetValue<bool>(out var b) => b ? "true" : "false",
        JsonValue value when value.TryGetValue<double>(out var d) => d.ToString("R", CultureInfo.InvariantCulture),
        _ => node.ToJsonString(),
    };
}
