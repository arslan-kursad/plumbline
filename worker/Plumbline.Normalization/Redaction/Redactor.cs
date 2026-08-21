using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace Plumbline.Normalization.Redaction;

/// <summary>One redacted attribute key and the reason it is on the list.</summary>
public sealed class RedactionRule
{
    public string Key { get; set; } = "";

    /// <summary>Why this key is redacted. Required: a rule nobody can justify is a rule nobody can remove.</summary>
    public string Why { get; set; } = "";
}

/// <summary>A dialect's redaction rule set, as parsed from <c>normalization/redaction/v1/</c>.</summary>
public sealed class RedactionRuleSet
{
    public string Version { get; set; } = "";

    public string Dialect { get; set; } = "";

    public List<string> AppliesTo { get; set; } = new();

    public List<RedactionRule> Rules { get; set; } = new();

    public IReadOnlySet<string> Keys() => Rules.Select(r => r.Key).ToHashSet(StringComparer.Ordinal);
}

/// <summary>
/// Replaces personal data with a deterministic marker, between normalization and the
/// write.
/// </summary>
/// <remarks>
/// <para>
/// This stage implements ADR-0006, accepted at the F1 exit review on 2026-08-21. It stays
/// isolated — it runs on the finished rows, reads nothing but its own rule files, and no
/// other stage knows it exists — because the ADR's own argument is that moving the
/// boundary later should cost this class and its call site, and nothing else.
/// </para>
/// <para>
/// Architecture §2.1 is why the boundary is here at all: redaction is attribute
/// manipulation on deserialized content, which the collector is forbidden to do twice
/// over — by the boundary rule and by ADR-0001. The consequence, which ADR-0006 has to
/// argue rather than assume, is that unredacted personal data transits Pub/Sub and
/// persists in the DLQ until someone drains it.
/// </para>
/// <para>
/// The marker is <c>[REDACTED:sha256:xxxxxxxx]</c> — the first eight hex characters of
/// the SHA-256 of the original value. Deterministic, so counts and joins over redacted
/// keys still work and the same identifier on a span and on its event still matches.
/// Unkeyed, so an eight-hex prefix over a guessable value is reversible by anyone willing
/// to hash a candidate list; ADR-0006 states that limit.
/// </para>
/// </remarks>
public sealed class Redactor
{
    private const string ResourcePrefix = "Plumbline.Normalization.redaction.";

    private readonly Dictionary<string, IReadOnlySet<string>> keysByDialect;

    private Redactor(Dictionary<string, IReadOnlySet<string>> keysByDialect)
    {
        this.keysByDialect = keysByDialect;
    }

    public static Redactor Embedded { get; } = LoadEmbedded();

    public static IReadOnlyList<RedactionRuleSet> RuleSets { get; private set; } = Array.Empty<RedactionRuleSet>();

    /// <summary>Redacts every attribute bag of a row in place, per its dialect's rules.</summary>
    /// <returns>How many values were replaced, for the counter the worker logs.</returns>
    public int Redact(string dialect, JsonObject attributes, JsonArray events, JsonArray links)
    {
        if (!keysByDialect.TryGetValue(dialect, out var keys))
        {
            return 0;
        }

        var redacted = 0;

        foreach (var level in new[] { "resource", "span" })
        {
            if (attributes[level] is JsonObject bag)
            {
                redacted += RedactBag(bag, keys);
            }
        }

        if (attributes["scope"]?["attributes"] is JsonObject scopeAttributes)
        {
            redacted += RedactBag(scopeAttributes, keys);
        }

        foreach (var collection in new[] { events, links })
        {
            foreach (var item in collection)
            {
                if (item?["attributes"] is JsonObject bag)
                {
                    redacted += RedactBag(bag, keys);
                }
            }
        }

        return redacted;
    }

    private static int RedactBag(JsonObject bag, IReadOnlySet<string> keys)
    {
        var redacted = 0;

        foreach (var key in bag.Select(pair => pair.Key).Where(keys.Contains).ToList())
        {
            switch (bag[key])
            {
                case JsonArray array:
                    // Array-valued attributes — workspace.host_paths is the one this
                    // project expects — are redacted element by element, so the count of
                    // paths survives while no path does.
                    var replacement = new JsonArray();
                    foreach (var element in array)
                    {
                        replacement.Add(JsonValue.Create(Marker(Render(element))));
                        redacted++;
                    }

                    bag[key] = replacement;
                    break;

                case { } value:
                    bag[key] = Marker(Render(value));
                    redacted++;
                    break;
            }
        }

        return redacted;
    }

    /// <summary>The marker a value becomes. Public because the fixtures assert it.</summary>
    public static string Marker(string value)
    {
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes(value));
        return $"[REDACTED:sha256:{Convert.ToHexString(digest)[..8].ToLowerInvariant()}]";
    }

    private static string Render(JsonNode? node) => node switch
    {
        null => "",
        JsonValue value when value.TryGetValue<string>(out var text) => text,
        _ => node.ToJsonString(),
    };

    private static Redactor LoadEmbedded()
    {
        var deserializer = new DeserializerBuilder()
            .WithNamingConvention(UnderscoredNamingConvention.Instance)
            .IgnoreUnmatchedProperties()
            .Build();

        var assembly = Assembly.GetExecutingAssembly();
        var keysByDialect = new Dictionary<string, IReadOnlySet<string>>(StringComparer.Ordinal);
        var sets = new List<RedactionRuleSet>();

        foreach (var name in assembly.GetManifestResourceNames()
                     .Where(n => n.StartsWith(ResourcePrefix, StringComparison.Ordinal))
                     .OrderBy(n => n, StringComparer.Ordinal))
        {
            using var stream = assembly.GetManifestResourceStream(name)!;
            using var reader = new StreamReader(stream);

            var set = deserializer.Deserialize<RedactionRuleSet>(reader)
                      ?? throw new InvalidOperationException($"embedded redaction rules {name} are empty");

            sets.Add(set);
            keysByDialect[set.Dialect] = set.Keys();
        }

        RuleSets = sets;
        return new Redactor(keysByDialect);
    }
}
