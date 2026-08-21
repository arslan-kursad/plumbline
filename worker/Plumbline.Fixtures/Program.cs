namespace Plumbline.Fixtures;

/// <summary>
/// Fixture tooling: turns the human-readable OTLP/JSON twin of each fixture into the
/// binary <c>ExportTraceServiceRequest</c> the pipeline actually carries, and verifies
/// that the committed binary still matches its twin.
///
/// The twin is the source of truth and the binary is derived, which is the only ordering
/// that keeps a fixture reviewable: a diff on <c>request.pb</c> says nothing, a diff on
/// <c>request.otlp.json</c> says what changed.
/// </summary>
public static class Program
{
    private const string TwinName = "request.otlp.json";
    private const string BinaryName = "request.pb";

    /// <summary>
    /// Bytes kept from the happy-path payload when building a poison fixture. Chosen to
    /// land inside a length-delimited field so the truncation is unrecoverable rather
    /// than a payload that happens to parse into fewer spans.
    /// </summary>
    private const int PoisonPrefixBytes = 96;

    public static int Main(string[] args)
    {
        var check = args.Contains("--check");
        var root = FindFixtureRoot();

        var verifyIndex = Array.IndexOf(args, "--verify");
        if (verifyIndex >= 0)
        {
            if (root is null)
            {
                Console.Error.WriteLine("could not locate testdata/fixtures from the current directory");
                return 2;
            }

            if (verifyIndex + 1 >= args.Length)
            {
                Console.Error.WriteLine("--verify needs the path of the observed rows (newline-delimited JSON)");
                return 2;
            }

            var failures = RowVerifier.Verify(root, args[verifyIndex + 1], Console.Out);
            if (failures > 0)
            {
                Console.Error.WriteLine($"{failures} fixture(s) did not match what the pipeline produced");
                return 1;
            }

            Console.WriteLine("pipeline output matches every golden file");
            return 0;
        }

        if (root is null)
        {
            Console.Error.WriteLine("could not locate testdata/fixtures from the current directory");
            return 2;
        }

        var drift = new List<string>();
        var written = 0;

        foreach (var caseDir in Directory.EnumerateDirectories(root, "*", SearchOption.AllDirectories)
                     .Where(d => File.Exists(Path.Combine(d, TwinName)))
                     .OrderBy(d => d, StringComparer.Ordinal))
        {
            var wire = FixtureEncoder.Encode(File.ReadAllText(Path.Combine(caseDir, TwinName)));
            written += Emit(Path.Combine(caseDir, BinaryName), wire, check, drift, root);
        }

        foreach (var poisonDir in Directory.EnumerateDirectories(root, "poison", SearchOption.AllDirectories)
                     .OrderBy(d => d, StringComparer.Ordinal))
        {
            var source = Path.Combine(Path.GetDirectoryName(poisonDir)!, "happy-path", BinaryName);
            if (!File.Exists(source))
            {
                Console.Error.WriteLine($"poison fixture {Rel(poisonDir, root)} has no happy-path sibling to truncate");
                return 2;
            }

            var truncated = File.ReadAllBytes(source).Take(PoisonPrefixBytes).ToArray();
            written += Emit(Path.Combine(poisonDir, BinaryName), truncated, check, drift, root);
        }

        if (check)
        {
            if (drift.Count == 0)
            {
                Console.WriteLine("fixtures: every binary matches its twin");
                return 0;
            }

            Console.Error.WriteLine("fixtures out of date with their twins:");
            foreach (var d in drift)
            {
                Console.Error.WriteLine($"  {d}");
            }

            Console.Error.WriteLine("run: dotnet run --project worker/Plumbline.Fixtures");
            return 1;
        }

        Console.WriteLine($"fixtures: wrote {written} binary payload(s)");
        return 0;
    }

    private static int Emit(string path, byte[] wire, bool check, List<string> drift, string root)
    {
        if (check)
        {
            var current = File.Exists(path) ? File.ReadAllBytes(path) : Array.Empty<byte>();
            if (!current.AsSpan().SequenceEqual(wire))
            {
                drift.Add(Rel(path, root));
            }

            return 0;
        }

        File.WriteAllBytes(path, wire);
        return 1;
    }

    private static string Rel(string path, string root) =>
        Path.GetRelativePath(Path.GetDirectoryName(root)!, path);

    private static string? FindFixtureRoot()
    {
        var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
        while (dir is not null)
        {
            var candidate = Path.Combine(dir.FullName, "testdata", "fixtures");
            if (Directory.Exists(candidate))
            {
                return candidate;
            }

            dir = dir.Parent;
        }

        return null;
    }
}
