using System.Text.Json;
using System.Text.Json.Nodes;

namespace Plumbline.Normalization.Tests;

/// <summary>One fixture case: a dialect directory plus one case directory inside it.</summary>
public sealed record FixtureCase(string Dialect, string Case, string Directory)
{
    public string TwinPath => Path.Combine(Directory, "request.otlp.json");
    public string BinaryPath => Path.Combine(Directory, "request.pb");
    public string ExpectedRowsPath => Path.Combine(Directory, "expected-rows.json");

    public bool HasTwin => File.Exists(TwinPath);
    public bool HasExpectedRows => File.Exists(ExpectedRowsPath);

    public byte[] Payload() => File.ReadAllBytes(BinaryPath);

    public JsonArray ExpectedRows() =>
        JsonNode.Parse(File.ReadAllText(ExpectedRowsPath)) as JsonArray
        ?? throw new InvalidDataException($"{ExpectedRowsPath} is not a JSON array");

    public override string ToString() => $"{Dialect}/{Case}";
}

/// <summary>
/// Locates <c>testdata/fixtures/</c> and enumerates it.
/// </summary>
/// <remarks>
/// The corpus is discovered from the filesystem rather than listed in code: a fixture
/// that exists but is not enumerated is a fixture nothing tests, and that failure is
/// silent. Adding a directory is enough to put it under test.
/// </remarks>
public static class FixtureCorpus
{
    public static string Root { get; } = Locate();

    public static IEnumerable<FixtureCase> All() =>
        Directory.EnumerateDirectories(Root)
            .OrderBy(d => d, StringComparer.Ordinal)
            .SelectMany(dialectDir => Directory.EnumerateDirectories(dialectDir)
                .OrderBy(d => d, StringComparer.Ordinal)
                .Select(caseDir => new FixtureCase(
                    Path.GetFileName(dialectDir)!,
                    Path.GetFileName(caseDir)!,
                    caseDir)));

    public static IEnumerable<string> Dialects() =>
        Directory.EnumerateDirectories(Root).Select(d => Path.GetFileName(d)!).OrderBy(d => d, StringComparer.Ordinal);

    public static string ManifestPath(string dialect) => Path.Combine(Root, dialect, "manifest.yaml");

    /// <summary>xUnit theory data: every case, as a one-element object array.</summary>
    public static TheoryData<FixtureCase> Cases()
    {
        var data = new TheoryData<FixtureCase>();
        foreach (var fixture in All())
        {
            data.Add(fixture);
        }

        return data;
    }

    public static TheoryData<FixtureCase> CasesWithExpectedRows()
    {
        var data = new TheoryData<FixtureCase>();
        foreach (var fixture in All().Where(f => f.HasExpectedRows))
        {
            data.Add(fixture);
        }

        return data;
    }

    private static string Locate()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "testdata", "fixtures");
            if (Directory.Exists(candidate))
            {
                return candidate;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException(
            $"testdata/fixtures not found above {AppContext.BaseDirectory}");
    }
}
