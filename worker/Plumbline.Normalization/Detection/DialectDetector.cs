using OpenTelemetry.Proto.Common.V1;
using OpenTelemetry.Proto.Resource.V1;
using Plumbline.Normalization.Mappings;

namespace Plumbline.Normalization.Detection;

/// <summary>How a dialect was arrived at. Reported so that a weak verdict is visible.</summary>
public enum DetectionBasis
{
    /// <summary>Instrumentation scope name matched — the primary key.</summary>
    ScopeName,

    /// <summary>No scope matched; resource markers identified exactly one dialect.</summary>
    ResourceMarker,

    /// <summary>Resource markers matched several dialects and the collector's hint chose among them.</summary>
    HintTiebreak,

    /// <summary>Nothing matched. Generic normalization, `source_dialect='unknown'`.</summary>
    Unrecognised,
}

/// <param name="Dialect">The authoritative dialect for these spans.</param>
/// <param name="Basis">What decided it.</param>
/// <param name="HintMismatch">
/// True when the collector's registration hint named a different dialect. The detected
/// value wins; the mismatch is reported so it can be logged (architecture §5).
/// </param>
public sealed record DetectionResult(string Dialect, DetectionBasis Basis, bool HintMismatch);

/// <summary>
/// Decides which dialect a scope's spans belong to.
/// </summary>
/// <remarks>
/// <para>
/// Deterministic and payload-driven, in the order architecture §5 and ADR-0003 §5 fix:
/// </para>
/// <list type="number">
///   <item>Instrumentation scope name. Set by the instrumentation itself, so it is the
///   marker an operator cannot move. Scope names are unique across mappings — a test
///   asserts it — so this step never returns two answers.</item>
///   <item>Resource markers, when no scope matched. Weaker: `service.name` and friends
///   are settable through <c>OTEL_RESOURCE_ATTRIBUTES</c>.</item>
///   <item>The collector's hint, and only to break a tie among several dialects whose
///   resource markers all matched. It never introduces a dialect the payload gave no
///   evidence for — that would make detection a function of key registration.</item>
///   <item>Otherwise unknown, normalized generically, never dropped.</item>
/// </list>
/// <para>
/// Detection runs per <c>ScopeSpans</c> rather than per payload: one export request can
/// legitimately carry two instrumentations, and `source_dialect` is a column on a row,
/// not on a message.
/// </para>
/// </remarks>
public sealed class DialectDetector
{
    private readonly MappingCatalog catalog;

    public DialectDetector(MappingCatalog catalog)
    {
        this.catalog = catalog;
    }

    public DetectionResult Detect(Resource? resource, InstrumentationScope? scope, string? hint)
    {
        var scopeName = scope?.Name ?? "";

        foreach (var table in catalog.Tables.OrderBy(t => t.Dialect, StringComparer.Ordinal))
        {
            if (table.Detection.ScopeNames.Any(name => string.Equals(name, scopeName, StringComparison.Ordinal)))
            {
                return new DetectionResult(table.Dialect, DetectionBasis.ScopeName, Mismatch(table.Dialect, hint));
            }
        }

        var byMarker = catalog.Tables
            .Where(table => MarkersMatch(table, resource))
            .Select(table => table.Dialect)
            .OrderBy(dialect => dialect, StringComparer.Ordinal)
            .ToList();

        switch (byMarker.Count)
        {
            case 1:
                return new DetectionResult(byMarker[0], DetectionBasis.ResourceMarker, Mismatch(byMarker[0], hint));

            case > 1 when hint is not null && byMarker.Contains(hint):
                return new DetectionResult(hint, DetectionBasis.HintTiebreak, false);
        }

        return new DetectionResult(MappingCatalog.UnknownDialect, DetectionBasis.Unrecognised,
            !string.IsNullOrEmpty(hint));
    }

    private static bool MarkersMatch(MappingTable table, Resource? resource)
    {
        if (table.Detection.ResourceMarkers.Count == 0 || resource is null)
        {
            return false;
        }

        // Every declared marker must match. A dialect claimed on one attribute out of
        // three would make the resource tier as strong as the scope tier, which is
        // exactly the confusion the two tiers exist to avoid.
        foreach (var (key, accepted) in table.Detection.ResourceMarkers)
        {
            var value = AttributeValues.AsString(AttributeValues.Find(resource.Attributes, key));
            if (value is null || !accepted.Contains(value, StringComparer.Ordinal))
            {
                return false;
            }
        }

        return true;
    }

    private static bool Mismatch(string detected, string? hint) =>
        !string.IsNullOrEmpty(hint) && !string.Equals(detected, hint, StringComparison.Ordinal);
}
