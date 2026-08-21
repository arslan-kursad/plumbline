using Plumbline.Normalization.Mappings;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace Plumbline.Normalization.Tests;

/// <summary>
/// Conformance of the mappings to the pinned semantic conventions.
/// </summary>
/// <remarks>
/// This is the executable form of <c>docs/eval-plan.md</c> SC-1 row 1.4: every name a
/// mapping targets is either defined in the vendored gen-ai model YAMLs or recorded in
/// the external-attribute allowlist with its upstream provenance. It runs against the
/// vendored copy in <c>normalization/semconv/v1.41/</c> and never over the network — a
/// rule that resolves names by fetching them is not reproducible, and SC-1's
/// author-independence argument would then rest on a live request.
/// </remarks>
public class SemconvRegistryTests
{
    private static readonly SemconvRegistry Registry = SemconvRegistry.Load();

    [Fact]
    public void TheVendoredRegistryIsReadableAndNotEmpty()
    {
        // If this fails, every other test in this file passes vacuously — a reader that
        // returns an empty set makes "every name is defined" trivially true. The count is
        // pinned rather than bounded so that a truncated or half-parsed vendored file is a
        // failure here rather than a silently permissive check.
        Assert.Equal(50, Registry.Current.Count);
        Assert.Equal(10, Registry.Deprecated.Count);
        Assert.Contains("gen_ai.provider.name", Registry.Current);
        Assert.Contains("gen_ai.system", Registry.Deprecated);
        Assert.Contains("server.address", Registry.ExternalAllowlist);
    }

    [Fact]
    public void EveryMappedColumnTargetsAnAttributeThePinDefines()
    {
        foreach (var table in MappingCatalog.Embedded.Tables)
        {
            foreach (var column in table.Columns)
            {
                Assert.True(
                    Registry.Defines(column.Semconv),
                    $"{table.Dialect}: column {column.Column} targets '{column.Semconv}', which semconv v1.41 does " +
                    "not define and the external allowlist does not carry. Either the name is wrong, or the " +
                    "attribute belongs in normalization/semconv/v1.41/external-allowlist.yaml with its provenance.");
            }
        }
    }

    [Fact]
    public void EveryGenAiSourceAttributeIsCurrentOrDeprecatedRatherThanInvented()
    {
        foreach (var table in MappingCatalog.Embedded.Tables)
        {
            foreach (var column in table.Columns)
            {
                foreach (var source in column.Rules.Select(rule => rule.From).OfType<string>()
                             .Where(name => name.StartsWith("gen_ai.", StringComparison.Ordinal)))
                {
                    Assert.True(
                        Registry.Current.Contains(source) || Registry.Deprecated.Contains(source),
                        $"{table.Dialect}: column {column.Column} reads '{source}', which is neither a current " +
                        "v1.41 attribute nor a deprecated one. A source in the gen_ai namespace that upstream " +
                        "never defined is a typo wearing a semconv name.");
                }
            }
        }
    }

    [Fact]
    public void TheDeprecatedModelFilesAreLoadBearing()
    {
        // W1.2 vendored the deprecated files with a specific justification: claude-code
        // emits gen_ai.system, which v1.41 deprecates. If no mapping reads a deprecated
        // name any more, the justification has expired and the files should go — so this
        // test fails rather than letting a stale vendoring sit there unexamined.
        var deprecatedSources = MappingCatalog.Embedded.Tables
            .SelectMany(table => table.Columns)
            .SelectMany(column => column.Rules)
            .Select(rule => rule.From)
            .OfType<string>()
            .Where(Registry.Deprecated.Contains)
            .Distinct()
            .ToList();

        Assert.True(deprecatedSources.Count > 0,
            "no mapping reads a deprecated semconv attribute any more, so vendoring " +
            "normalization/semconv/v1.41/deprecated/ no longer earns its place (decision log W1.2)");
    }

    [Fact]
    public void EveryMappedColumnExistsInTheTableAndAgreesOnItsAttributeAndType()
    {
        foreach (var table in MappingCatalog.Embedded.Tables)
        {
            foreach (var column in table.Columns)
            {
                Assert.True(GenAiColumns.ByName.TryGetValue(column.Column, out var declared),
                    $"{table.Dialect}: column {column.Column} is not in the typed column set, so it would be " +
                    "mapped into nothing");

                Assert.Equal(declared!.Semconv, column.Semconv);
                Assert.Equal(declared.Type.ToString().ToLowerInvariant(), column.Type.ToLowerInvariant());
            }
        }
    }

    [Fact]
    public void ScopeNamesAreUniqueAcrossDialects()
    {
        // Detection returns one answer per scope name by construction rather than by
        // tie-breaking, and this is the construction.
        var duplicates = MappingCatalog.Embedded.Tables
            .SelectMany(table => table.Detection.ScopeNames.Select(name => (name, table.Dialect)))
            .GroupBy(pair => pair.name, StringComparer.Ordinal)
            .Where(group => group.Count() > 1)
            .Select(group => $"{group.Key} claimed by {string.Join(" and ", group.Select(p => p.Dialect))}")
            .ToList();

        Assert.True(duplicates.Count == 0, string.Join("\n", duplicates));
    }

    [Fact]
    public void EveryFixtureDialectHasAMappingAndEveryMappingHasFixtures()
    {
        var mapped = MappingCatalog.Embedded.Dialects.ToHashSet(StringComparer.Ordinal);
        var fixtures = FixtureCorpus.Dialects().Where(d => d != MappingCatalog.UnknownDialect).ToHashSet(StringComparer.Ordinal);

        Assert.True(mapped.SetEquals(fixtures),
            $"mapped but never tested: {string.Join(", ", mapped.Except(fixtures))}\n" +
            $"fixtures with no mapping: {string.Join(", ", fixtures.Except(mapped))}");
    }

    [Fact]
    public void EveryRedactionRuleStatesWhy()
    {
        foreach (var set in Plumbline.Normalization.Redaction.Redactor.RuleSets)
        {
            Assert.NotEmpty(set.Rules);
            foreach (var rule in set.Rules)
            {
                Assert.False(string.IsNullOrWhiteSpace(rule.Why),
                    $"{set.Dialect}: redaction rule for '{rule.Key}' has no reason. A rule nobody can justify " +
                    "is a rule nobody can safely remove, and this list decides what leaves the pipeline.");
            }
        }
    }
}

/// <summary>Reads the vendored semconv model YAMLs and the external allowlist.</summary>
internal sealed class SemconvRegistry
{
    public required IReadOnlySet<string> Current { get; init; }

    public required IReadOnlySet<string> Deprecated { get; init; }

    public required IReadOnlySet<string> ExternalAllowlist { get; init; }

    public bool Defines(string attribute) =>
        Current.Contains(attribute) || ExternalAllowlist.Contains(attribute);

    public static SemconvRegistry Load()
    {
        var root = Locate();
        var deserializer = new DeserializerBuilder().WithNamingConvention(NullNamingConvention.Instance).Build();

        return new SemconvRegistry
        {
            Current = Attributes(deserializer, Path.Combine(root, "registry.yaml")),
            Deprecated = Attributes(deserializer, Path.Combine(root, "deprecated", "registry-deprecated.yaml")),
            ExternalAllowlist = AllowlistNames(deserializer, Path.Combine(root, "external-allowlist.yaml")),
        };
    }

    /// <summary>
    /// Collects `groups[*].attributes[*].id`.
    /// </summary>
    /// <remarks>
    /// Not a recursive walk of every `id` in the file: enum members are also `id`, and
    /// counting `openai` or `chat` as attribute names would make this check accept
    /// anything. The nesting the upstream model actually uses is one level.
    /// </remarks>
    private static IReadOnlySet<string> Attributes(IDeserializer deserializer, string path)
    {
        var document = deserializer.Deserialize<Dictionary<string, object>>(File.ReadAllText(path));
        var names = new HashSet<string>(StringComparer.Ordinal);

        if (document.GetValueOrDefault("groups") is not List<object> groups)
        {
            return names;
        }

        foreach (var group in groups.OfType<Dictionary<object, object>>())
        {
            if (group.GetValueOrDefault("attributes") is not List<object> attributes)
            {
                continue;
            }

            foreach (var attribute in attributes.OfType<Dictionary<object, object>>())
            {
                if (attribute.GetValueOrDefault("id") is string id)
                {
                    names.Add(id);
                }
            }
        }

        return names;
    }

    private static IReadOnlySet<string> AllowlistNames(IDeserializer deserializer, string path)
    {
        var document = deserializer.Deserialize<Dictionary<string, object>>(File.ReadAllText(path));
        var names = new HashSet<string>(StringComparer.Ordinal);

        if (document.GetValueOrDefault("attributes") is List<object> attributes)
        {
            foreach (var attribute in attributes.OfType<Dictionary<object, object>>())
            {
                if (attribute.GetValueOrDefault("name") is string name)
                {
                    names.Add(name);
                }
            }
        }

        return names;
    }

    private static string Locate()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "normalization", "semconv", "v1.41");
            if (Directory.Exists(candidate))
            {
                return candidate;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("normalization/semconv/v1.41 not found");
    }
}
