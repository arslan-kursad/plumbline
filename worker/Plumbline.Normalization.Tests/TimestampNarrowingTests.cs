using Plumbline.Normalization.Rows;

namespace Plumbline.Normalization.Tests;

/// <summary>
/// The nanosecond → microsecond narrowing at the BigQuery boundary.
/// </summary>
/// <remarks>
/// This behaviour was already correct and already pinned — by exactly one field, in one
/// fixture, in one golden file: <c>endTimeUnixNano: 1787133601612345678</c> in
/// <c>langgraph-python/happy-path</c>. Every other timestamp in the seven-fixture corpus
/// ends in three zeros and so is identical under truncation and rounding.
///
/// Nothing declared that the <c>678</c> suffix was load-bearing. Regenerating that fixture,
/// or adding a "cleaner" one, would have removed the corpus's only discriminating case and
/// nothing would have gone red — the same shape as the plan-guard fixture that was silent
/// about a field until the first check to read it (F2 decision log W3.6).
///
/// ADR-0007's D7 table states that the narrowing is truncation. These tests are what make
/// that a checked claim rather than a described one, independent of any fixture.
/// </remarks>
public class TimestampNarrowingTests
{
    [Theory]
    // The digits that distinguish the two rules: anything at or above 500 ns rounds up
    // and truncates down, so each of these fails if Math.Round is ever introduced.
    [InlineData(1_787_133_601_612_345_678UL, "2026-08-19T10:00:01.612345Z")]
    [InlineData(1_787_133_601_612_345_500UL, "2026-08-19T10:00:01.612345Z")]
    [InlineData(1_787_133_601_612_345_999UL, "2026-08-19T10:00:01.612345Z")]
    public void SubMicrosecondDigitsAreDroppedNotRounded(ulong unixNanos, string expected)
    {
        Assert.Equal(expected, Timestamps.Format(Timestamps.FromUnixNanos(unixNanos)));
    }

    [Fact]
    public void ExactMicrosecondsAreUnchanged()
    {
        Assert.Equal(
            "2026-08-19T10:00:01.612345Z",
            Timestamps.Format(Timestamps.FromUnixNanos(1_787_133_601_612_345_000UL)));
    }

    [Fact]
    public void TheEpochIsTheEpoch()
    {
        Assert.Equal(DateTimeOffset.UnixEpoch, Timestamps.FromUnixNanos(0));
    }

    [Fact]
    public void NarrowingIsMonotonicAcrossAMicrosecondBoundary()
    {
        // The property the dedup design rests on is that identical bytes produce an
        // identical TIMESTAMP. That holds under any deterministic rule. What a replay
        // after a redeploy would break is *two different* rules disagreeing across a
        // boundary — so the boundary itself is asserted rather than assumed.
        var below = Timestamps.FromUnixNanos(1_787_133_601_612_345_999UL);
        var above = Timestamps.FromUnixNanos(1_787_133_601_612_346_000UL);

        Assert.Equal("2026-08-19T10:00:01.612345Z", Timestamps.Format(below));
        Assert.Equal("2026-08-19T10:00:01.612346Z", Timestamps.Format(above));
        Assert.True(above > below);
    }
}
