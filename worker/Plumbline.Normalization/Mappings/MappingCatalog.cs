using System.Reflection;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace Plumbline.Normalization.Mappings;

/// <summary>
/// The mapping tables, embedded in the binary at build time.
/// </summary>
/// <remarks>
/// <para>
/// ADR-0003 §1: the YAML is embedded, not read from a store or a mounted file. What that
/// buys is stated in the ADR and is worth restating where the code is: every stored row
/// is attributable to a commit, because the image tag fixes the binary and the binary
/// fixes the mapping. A file read at startup would make "which mapping produced this row"
/// an operational question instead of a build fact.
/// </para>
/// <para>
/// The mechanism is <c>EmbeddedResource</c> rather than a source generator. A generator
/// would turn the YAML into C# at build time, which is faster to load and much harder to
/// review: the artefact ADR-0003 §"Consequences" wants publishable is the YAML, and a
/// generator adds a translation step between the file and what runs.
/// </para>
/// </remarks>
public sealed class MappingCatalog
{
    private const string ResourcePrefix = "Plumbline.Normalization.mappings.";

    private readonly Dictionary<string, MappingTable> byDialect;

    private MappingCatalog(Dictionary<string, MappingTable> byDialect)
    {
        this.byDialect = byDialect;
    }

    /// <summary>The dialect name used when detection finds nothing (architecture §5).</summary>
    public const string UnknownDialect = "unknown";

    public static MappingCatalog Embedded { get; } = LoadEmbedded();

    public IReadOnlyCollection<MappingTable> Tables => byDialect.Values;

    public IEnumerable<string> Dialects => byDialect.Keys.OrderBy(d => d, StringComparer.Ordinal);

    public MappingTable? Find(string dialect) =>
        byDialect.TryGetValue(dialect, out var table) ? table : null;

    /// <summary>
    /// The generic mapping used for an unrecognised dialect: every typed column filled
    /// from the v1.41 attribute name it stands for.
    /// </summary>
    /// <remarks>
    /// Generated from <see cref="GenAiColumns"/> rather than written as a fourth YAML
    /// file, so it cannot drift from the column set it is generic over. Architecture §5
    /// says an unknown dialect is normalized generically — "normalized columns filled
    /// where OTLP fields map directly" — and an attribute already carrying its exact
    /// v1.41 name maps directly by any reading (decision log W2.8).
    /// </remarks>
    public static MappingTable Generic { get; } = new()
    {
        Dialect = UnknownDialect,
        SemconvVersion = "1.41.0",
        Columns = GenAiColumns.All.Select(column => new ColumnMapping
        {
            Column = column.Column,
            Semconv = column.Semconv,
            Type = column.Type.ToString().ToLowerInvariant(),
            Rules = new List<MappingRule> { new() { From = column.Semconv } },
        }).ToList(),
    };

    private static MappingCatalog LoadEmbedded()
    {
        var deserializer = new DeserializerBuilder()
            .WithNamingConvention(UnderscoredNamingConvention.Instance)
            .IgnoreUnmatchedProperties()
            .Build();

        var assembly = Assembly.GetExecutingAssembly();
        var tables = new Dictionary<string, MappingTable>(StringComparer.Ordinal);

        foreach (var name in assembly.GetManifestResourceNames()
                     .Where(n => n.StartsWith(ResourcePrefix, StringComparison.Ordinal))
                     .OrderBy(n => n, StringComparer.Ordinal))
        {
            using var stream = assembly.GetManifestResourceStream(name)
                               ?? throw new InvalidOperationException($"embedded mapping {name} could not be opened");
            using var reader = new StreamReader(stream);

            var table = deserializer.Deserialize<MappingTable>(reader)
                        ?? throw new InvalidOperationException($"embedded mapping {name} is empty");

            if (string.IsNullOrWhiteSpace(table.Dialect))
            {
                throw new InvalidOperationException($"embedded mapping {name} declares no dialect");
            }

            if (!tables.TryAdd(table.Dialect, table))
            {
                throw new InvalidOperationException($"two embedded mappings declare the dialect {table.Dialect}");
            }
        }

        if (tables.Count == 0)
        {
            throw new InvalidOperationException(
                "no mapping tables are embedded in this binary. The worker would detect every payload as " +
                "unknown and normalize it generically, which is a silent and total loss of dialect handling — " +
                "so it is a startup failure instead.");
        }

        return new MappingCatalog(tables);
    }
}
