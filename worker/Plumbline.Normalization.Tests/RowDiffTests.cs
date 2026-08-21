using System.Text.Json.Nodes;
using Plumbline.Normalization.Rows;

namespace Plumbline.Normalization.Tests;

/// <summary>
/// Tests of the golden harness itself.
/// </summary>
/// <remarks>
/// The F1 spec makes diff quality part of the deliverable, which means it has to be a
/// tested property rather than an intention. Each test here states the diagnostic a
/// failing golden test must produce: which field, which two values, and all of them
/// rather than the first.
/// </remarks>
public class RowDiffTests
{
    private static JsonArray Rows(params string[] json) =>
        new(json.Select(j => (JsonNode?)JsonNode.Parse(j)!).ToArray());

    [Fact]
    public void IdenticalRowsProduceNoDifferences()
    {
        var rows = Rows("""{"name":"chat","gen_ai_usage_input_tokens":42,"attributes":{"span":{"a":1}}}""");
        Assert.Empty(RowDiff.Compare(rows, Rows(rows[0]!.ToJsonString())));
    }

    [Fact]
    public void AScalarMismatchNamesTheColumnAndBothValues()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"gen_ai_request_model":"claude-sonnet-4-5"}"""),
            Rows("""{"gen_ai_request_model":"gpt-4o-mini"}"""));

        var diff = Assert.Single(diffs);
        Assert.Equal("rows[0].gen_ai_request_model", diff.Path);
        Assert.Equal("\"claude-sonnet-4-5\"", diff.Expected);
        Assert.Equal("\"gpt-4o-mini\"", diff.Actual);
    }

    [Fact]
    public void ANullThatShouldHaveBeenAValueIsReportedAsAValueDifference()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"gen_ai_usage_input_tokens":1843}"""),
            Rows("""{"gen_ai_usage_input_tokens":null}"""));

        var diff = Assert.Single(diffs);
        Assert.Equal("rows[0].gen_ai_usage_input_tokens", diff.Path);
        Assert.Equal("null", diff.Actual);
    }

    [Fact]
    public void AMissingColumnIsDistinguishedFromAnUnexpectedOne()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"a":1,"b":2}"""),
            Rows("""{"a":1,"c":3}"""));

        Assert.Equal(2, diffs.Count);
        Assert.Contains(diffs, d => d.Path == "rows[0].b" && d.Kind == "missing");
        Assert.Contains(diffs, d => d.Path == "rows[0].c" && d.Kind == "unexpected");
    }

    [Fact]
    public void ADottedAttributeKeyIsBracketedSoThePathStaysReadable()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"attributes":{"span":{"llm.model_name":"claude-sonnet-4-5"}}}"""),
            Rows("""{"attributes":{"span":{"llm.model_name":"claude-haiku-4-5"}}}"""));

        var diff = Assert.Single(diffs);
        Assert.Equal("rows[0].attributes.span[\"llm.model_name\"]", diff.Path);
    }

    [Fact]
    public void ADroppedAttributeIsReportedAtItsOwnPathNotAsAChangedBlob()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"attributes":{"span":{"kept":"y","dropped":"x"}}}"""),
            Rows("""{"attributes":{"span":{"kept":"y"}}}"""));

        var diff = Assert.Single(diffs);
        Assert.Equal("rows[0].attributes.span.dropped", diff.Path);
        Assert.Equal("missing", diff.Kind);
    }

    [Fact]
    public void EventArraysAreComparedElementByElement()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"events":[{"name":"exception"},{"name":"retry"}]}"""),
            Rows("""{"events":[{"name":"exception"}]}"""));

        var diff = Assert.Single(diffs);
        Assert.Equal("rows[0].events[1]", diff.Path);
        Assert.Equal("missing", diff.Kind);
    }

    [Fact]
    public void AValueThatBecameAnObjectIsReportedAsATypeDifference()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"attributes":{"span":{"metadata":"{\"run\":7}"}}}"""),
            Rows("""{"attributes":{"span":{"metadata":{"run":7}}}}"""));

        var diff = Assert.Single(diffs);
        Assert.Equal("type", diff.Kind);
        Assert.Equal("rows[0].attributes.span.metadata", diff.Path);
    }

    [Fact]
    public void AMissingRowIsReportedWithoutHidingTheDifferencesInTheRowsThatArePresent()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"name":"a"}""", """{"name":"b"}"""),
            Rows("""{"name":"z"}"""));

        Assert.Equal(2, diffs.Count);
        Assert.Contains(diffs, d => d.Path == "rows[0].name" && d.Kind == "value");
        Assert.Contains(diffs, d => d.Path == "rows[1]" && d.Kind == "missing");
    }

    [Fact]
    public void EveryDifferenceIsReportedNotOnlyTheFirst()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"a":1,"b":2,"c":3}"""),
            Rows("""{"a":9,"b":8,"c":7}"""));

        Assert.Equal(3, diffs.Count);
    }

    [Fact]
    public void TheFailureMessageLeadsWithTheCountAndThenOneLinePerDifference()
    {
        var diffs = RowDiff.Compare(
            Rows("""{"a":1,"b":2}"""),
            Rows("""{"a":9,"b":8}"""));

        var text = RowDiff.Describe("claude-code/happy-path", diffs);
        var lines = text.Split(Environment.NewLine, StringSplitOptions.RemoveEmptyEntries);

        Assert.Equal("claude-code/happy-path: 2 differences", lines[0]);
        Assert.Equal(3, lines.Length);
        Assert.All(lines.Skip(1), line => Assert.StartsWith("  rows[0].", line));
    }

    [Fact]
    public void NoDifferencesDescribesItselfPlainly()
    {
        Assert.Equal(
            "claude-code/happy-path: no differences",
            RowDiff.Describe("claude-code/happy-path", Array.Empty<RowDifference>()));
    }
}
