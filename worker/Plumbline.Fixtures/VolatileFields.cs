namespace Plumbline.Fixtures;

/// <summary>
/// The one list of columns a row comparison is allowed to ignore, with the reason each
/// one is on it.
/// </summary>
/// <remarks>
/// <para>
/// F2 completion directive v1.7, Decision 12. Both comparisons use this list: the local
/// end-to-end verify (<see cref="RowVerifier"/>) and the cloud harness's golden diff. Two
/// lists would drift, and the one that drifted would be the one nobody was reading at the
/// moment a real difference went through it.
/// </para>
/// <para>
/// The list exists so that excluding a column costs a commit. An exclusion written inline
/// at the comparison site is a place where a real difference gets waved through at 2am;
/// this is a place where waving it through leaves a diff with a name on it.
/// </para>
/// <para>
/// <c>api_key_id</c> is deliberately <b>not</b> here. It differs between the two paths only
/// if they are told different key ids, and the harness passes the cloud run's key id to the
/// local normalization for exactly that reason. Decision 12 admits it "if and only if the
/// two paths legitimately differ", and they do not.
/// </para>
/// </remarks>
public static class VolatileFields
{
    /// <summary>Column name to the reason it cannot be compared.</summary>
    public static IReadOnlyDictionary<string, string> Excluded { get; } =
        new Dictionary<string, string>(StringComparer.Ordinal)
        {
            // Stamped by the sink at write time. Asserting a value would be asserting a clock.
            ["ingest_time"] = "written by the sink; comparing it would compare two clocks",
        };

    /// <summary>Renders the list for a run's evidence, so the archive says what was not compared.</summary>
    public static string Describe() =>
        string.Join("\n", Excluded.Select(pair => $"  {pair.Key}: {pair.Value}"));
}
