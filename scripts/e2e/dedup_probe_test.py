#!/usr/bin/env python3
"""Tests for the dedup probe's verdict, which is the part with the judgement in it.

The probe's value is that it fails in the four ways a dedup view can be wrong, and that
it fails when there was no duplicate to collapse. Each of those is a case here, because a
probe that has only ever been seen green is not evidence (standing requirement R-A).

Run directly: python3 scripts/e2e/dedup_probe_test.py
"""

import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location(
    "dedup_probe", pathlib.Path(__file__).resolve().parent / "dedup-probe.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

EARLIER = "2026-08-19T10:00:00.000000Z"
LATER = "2026-08-19T10:05:00.000000Z"


def duplicated(copies=2, latest=LATER, trace="trace-aaaaaaaaaaaa", span="span-bbbb"):
    return [{"trace_id": trace, "span_id": span, "copies": copies, "latest": latest}]


def view(ingest_times, trace="trace-aaaaaaaaaaaa", span="span-bbbb"):
    return [{"trace_id": trace, "span_id": span, "ingest_time": t} for t in ingest_times]


class TheWorkingCase(unittest.TestCase):

    def test_two_base_rows_collapsed_to_the_later_one_is_clean(self):
        self.assertEqual(probe.verdict(duplicated(), view([LATER])), [])

    def test_several_duplicated_keys_all_collapsed_is_clean(self):
        dupes = duplicated() + duplicated(trace="trace-cccccccccccc", span="span-dddd")
        rows = view([LATER]) + view([LATER], trace="trace-cccccccccccc", span="span-dddd")
        self.assertEqual(probe.verdict(dupes, rows), [])


class TheWaysItMustFail(unittest.TestCase):
    """One case per way the assertion can be wrong. None of these may pass."""

    def test_an_absent_duplicate_is_a_failure_not_a_pass(self):
        # The whole reason this probe exists. Before it, an empty duplicate set and a
        # working view produced the same output.
        findings = probe.verdict([], view([LATER]))
        self.assertEqual(len(findings), 1)
        self.assertIn("nothing to dedup", findings[0])

    def test_a_view_returning_both_rows_is_caught(self):
        # What removing `WHERE duplicate_rank = 1` from 002_spans_deduped.sql produces.
        findings = probe.verdict(duplicated(), view([EARLIER, LATER]))
        self.assertEqual(len(findings), 1)
        self.assertIn("view returns 2", findings[0])

    def test_a_view_returning_the_earlier_row_is_caught(self):
        # What an ORDER BY ingest_time ASC would produce: one row, and the wrong one.
        findings = probe.verdict(duplicated(), view([EARLIER]))
        self.assertEqual(len(findings), 1)
        self.assertIn("later of the", findings[0])

    def test_a_view_dropping_the_key_entirely_is_caught(self):
        findings = probe.verdict(duplicated(), [])
        self.assertEqual(len(findings), 1)
        self.assertIn("view returns 0", findings[0])

    def test_one_broken_key_among_several_is_reported_and_the_others_are_not(self):
        dupes = duplicated() + duplicated(trace="trace-cccccccccccc", span="span-dddd")
        rows = view([LATER]) + view([EARLIER, LATER], trace="trace-cccccccccccc", span="span-dddd")
        findings = probe.verdict(dupes, rows)
        self.assertEqual(len(findings), 1)
        self.assertIn("trace-cccccc", findings[0])  # the label truncates at 12


class TheReportingContract(unittest.TestCase):

    def test_a_finding_names_both_sides_rather_than_only_the_verdict(self):
        finding = probe.verdict(duplicated(copies=3), view([EARLIER, LATER]))[0]
        self.assertIn("base holds 3", finding)
        self.assertIn("view returns 2", finding)

    def test_the_wrong_row_finding_quotes_both_timestamps(self):
        finding = probe.verdict(duplicated(), view([EARLIER]))[0]
        self.assertIn(EARLIER, finding)
        self.assertIn(LATER, finding)


if __name__ == "__main__":
    unittest.main(verbosity=2)
