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

        var encodeIndex = Array.IndexOf(args, "--encode");
        if (encodeIndex >= 0)
        {
            // One twin to one binary, for a corpus built outside testdata/fixtures. The
            // in-place regeneration below cannot serve the cloud harness, whose corpus is
            // run-scoped and lives in a working directory.
            if (encodeIndex + 2 >= args.Length)
            {
                Console.Error.WriteLine("usage: --encode <twin.otlp.json> <out.pb>");
                return 2;
            }

            File.WriteAllBytes(args[encodeIndex + 2], FixtureEncoder.Encode(File.ReadAllText(args[encodeIndex + 1])));
            return 0;
        }

        var normalizeIndex = Array.IndexOf(args, "--normalize");
        if (normalizeIndex >= 0)
        {
            // The cloud harness's local half (directive v1.7, Decision 12). It does not
            // need testdata/fixtures: the corpus it normalizes is run-scoped and built
            // elsewhere, so the root lookup below would fail for the wrong reason.
            var outIndex = Array.IndexOf(args, "--out");
            var keyIndex = Array.IndexOf(args, "--api-key-id");

            if (normalizeIndex + 1 >= args.Length || outIndex < 0 || outIndex + 1 >= args.Length
                || keyIndex < 0 || keyIndex + 1 >= args.Length)
            {
                Console.Error.WriteLine(
                    "usage: --normalize <corpus-dir> --out <rows.ndjson> --api-key-id <id>");
                return 2;
            }

            return CorpusNormalizer.Normalize(
                args[normalizeIndex + 1], args[outIndex + 1], args[keyIndex + 1], Console.Out);
        }

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
