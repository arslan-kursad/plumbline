using YamlDotNet.Serialization;

namespace Plumbline.Normalization.Mappings;

/// <summary>
/// One dialect's mapping, as parsed from <c>normalization/mappings/v1.41/&lt;dialect&gt;.yaml</c>.
/// </summary>
/// <remarks>
/// The file is the artefact; this is a reader for it. ADR-0003 §1 embeds the YAML into
/// the binary at build time and forbids a runtime configuration store, so a mapping
/// change is a code change with golden tests in the same commit — and the version that
/// produced any given row is answerable from a commit hash.
/// </remarks>
public sealed class MappingTable
{
    public string Dialect { get; set; } = "";

    public string SemconvVersion { get; set; } = "";

    public DetectionRules Detection { get; set; } = new();

    public List<ColumnMapping> Columns { get; set; } = new();
}

/// <summary>
/// What identifies this dialect in a payload.
/// </summary>
/// <remarks>
/// Two tiers, and the difference matters. A scope name is set by the instrumentation
/// itself and is the primary key. A resource marker can be overridden by an operator
/// through <c>OTEL_RESOURCE_ATTRIBUTES</c>, so it corroborates and never decides alone
/// (evidence §6).
/// </remarks>
public sealed class DetectionRules
{
    public List<string> ScopeNames { get; set; } = new();

    public Dictionary<string, List<string>> ResourceMarkers { get; set; } = new();
}

/// <summary>One typed column and the ordered rules that may fill it.</summary>
public sealed class ColumnMapping
{
    public string Column { get; set; } = "";

    /// <summary>The v1.41 attribute this column stands for. Validated against the vendored registry.</summary>
    public string Semconv { get; set; } = "";

    public string Type { get; set; } = "string";

    /// <summary>
    /// Rules in precedence order: the first that yields a value wins, and the rest are
    /// not consulted. Order in the file is the precedence, which is why a mapping puts
    /// the current semconv name above a deprecated fallback.
    /// </summary>
    public List<MappingRule> Rules { get; set; } = new();
}

/// <summary>One way of filling a column.</summary>
public sealed class MappingRule
{
    /// <summary>Source attribute name, read from the span's attributes.</summary>
    public string? From { get; set; }

    /// <summary>
    /// Optional translation of the source value. A value absent from the map yields
    /// nothing, so an emitter value nobody has mapped produces a null column rather than
    /// a passed-through value that looks like a v1.41 enum member and is not one.
    /// </summary>
    public Dictionary<string, string>? Map { get; set; }

    /// <summary>
    /// Constant keyed by the span's name, for dialects that state a span's role in the
    /// name and nowhere else.
    /// </summary>
    [YamlMember(Alias = "from_span_name")]
    public Dictionary<string, string>? FromSpanName { get; set; }
}
