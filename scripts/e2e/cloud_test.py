"""Tests for the cloud harness's guards (directive v1.7, Decisions 6-13; §8).

§8 requires the guards be exercised in both directions: a check that has only ever
passed is not yet evidence. Every test here is written so it can fail -- the refusals
are asserted by triggering them, not by reading the code.

Run directly: python3 scripts/e2e/cloud_test.py
"""

import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import cloud  # noqa: E402


class Arming(unittest.TestCase):
    """Decision 10. The first cloud run is the DoD 7b exam and it is taken once."""

    def test_default_target_is_the_emulator(self):
        self.assertEqual(cloud.arming({}, None), "emulator")

    def test_cloud_without_a_run_id_is_refused(self):
        with self.assertRaises(cloud.Refused):
            cloud.arming({"PLUMBLINE_E2E_TARGET": "cloud"}, None)

    def test_cloud_with_both_is_allowed(self):
        # The other direction. A guard that refused everything would pass the test above.
        self.assertEqual(cloud.arming({"PLUMBLINE_E2E_TARGET": "cloud"}, "w4-first"), "cloud")

    def test_an_unusable_run_id_is_refused(self):
        for bad in ("W4", "a", "with space", "x" * 64, "trailing-"):
            with self.subTest(bad), self.assertRaises(cloud.Refused):
                cloud.arming({"PLUMBLINE_E2E_TARGET": "cloud"}, bad)

    def test_the_run_id_is_not_consulted_for_the_emulator(self):
        self.assertEqual(cloud.arming({"PLUMBLINE_E2E_TARGET": "emulator"}, None), "emulator")


class Window(unittest.TestCase):
    """Decision 7. The filter is satisfied by construction; the scan is bounded too."""

    def test_a_query_cannot_be_built_without_a_window(self):
        with self.assertRaises(cloud.Refused):
            cloud.scoped_query("2026-08-31", "run", "COUNT(*)", "spans_deduped")

    def test_a_backwards_window_is_refused(self):
        with self.assertRaises(cloud.Refused):
            cloud.PartitionWindow(dt.date(2026, 9, 1), dt.date(2026, 8, 1))

    def test_a_window_wide_enough_to_be_a_full_scan_is_refused(self):
        # require_partition_filter is satisfied by a year-wide predicate. The budget is not.
        with self.assertRaises(cloud.Refused):
            cloud.PartitionWindow(dt.date(2026, 1, 1), dt.date(2026, 12, 31))

    def test_the_query_carries_both_the_partition_and_the_run_scope(self):
        window = cloud.PartitionWindow(dt.date(2026, 8, 30), dt.date(2026, 9, 1))
        sql = cloud.scoped_query(window, "w4-first", "COUNT(*)", "spans_deduped")
        self.assertIn("DATE(start_time) BETWEEN '2026-08-30' AND '2026-09-01'", sql)
        self.assertIn("'w4-first'", sql)

    def test_the_window_comes_from_the_run_not_from_today(self):
        moment = dt.datetime(2026, 3, 4, 12, 0, tzinfo=dt.timezone.utc)
        window = cloud.PartitionWindow.around(moment)
        self.assertEqual((window.lower, window.upper), (dt.date(2026, 3, 3), dt.date(2026, 3, 5)))


class Corpus(unittest.TestCase):
    """Decision 6 and issue #102. A second run has to be a second run."""

    def build(self, run_id, where):
        return cloud.build_corpus(run_id, pathlib.Path(where))

    def test_every_resource_carries_both_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in self.build("run-alpha", tmp):
                payload = json.loads(path.read_text())
                for resource_spans in payload["resourceSpans"]:
                    keys = [a["key"] for a in resource_spans["resource"]["attributes"]]
                    self.assertIn("synthetic", keys)
                    self.assertIn("plumbline.e2e_run_id", keys)

    def test_synthetic_is_a_boolean_because_the_normalizer_requires_one(self):
        # Normalizer.cs takes the flag only when ValueCase is BoolValue. A stringValue
        # "true" would normalize to synthetic=false and DoD 3 would fail on real rows.
        with tempfile.TemporaryDirectory() as tmp:
            payload = json.loads(self.build("run-alpha", tmp)[0].read_text())
            flag = [a for a in payload["resourceSpans"][0]["resource"]["attributes"]
                    if a["key"] == "synthetic"][0]
            self.assertEqual(flag["value"], {"boolValue": True})

    def test_identity_is_derived_per_run_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = json.loads(self.build("run-alpha", f"{tmp}/a")[0].read_text())
            again = json.loads(self.build("run-alpha", f"{tmp}/b")[0].read_text())
            other = json.loads(self.build("run-beta", f"{tmp}/c")[0].read_text())

            def trace(doc):
                return doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["traceId"]

            self.assertEqual(trace(first), trace(again), "the same run must rebuild identically")
            self.assertNotEqual(trace(first), trace(other), "two runs must not collide in the dedup window")

    def test_identifier_lengths_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            for path in self.build("run-alpha", tmp):
                for resource_spans in json.loads(path.read_text())["resourceSpans"]:
                    for scope_spans in resource_spans["scopeSpans"]:
                        for span in scope_spans["spans"]:
                            self.assertEqual(len(span["traceId"]), 32)
                            self.assertEqual(len(span["spanId"]), 16)

    def test_start_time_is_left_alone(self):
        # Shifting it would move rows between partitions and make Decision 7's window a
        # function of the run rather than of the data.
        original = json.loads(
            (cloud.FIXTURES / "claude-code" / "happy-path" / "request.otlp.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            built = [p for p in self.build("run-alpha", tmp) if p.name.startswith("claude-code-happy")][0]
            rebuilt = json.loads(built.read_text())
        self.assertEqual(
            [s["startTimeUnixNano"] for s in original["resourceSpans"][0]["scopeSpans"][0]["spans"]],
            [s["startTimeUnixNano"] for s in rebuilt["resourceSpans"][0]["scopeSpans"][0]["spans"]],
        )

    def test_poison_is_not_in_the_happy_path_corpus(self):
        # Decision 9: the drill is a separate entry point. One corpus would fire the
        # DoD 7b exam and the DoD 4 drill together and weaken both.
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse([p for p in self.build("run-alpha", tmp) if "poison" in p.name])


class Provenance(unittest.TestCase):
    """Decision 8. §8 requires this fail on a mismatch and pass on a match."""

    class FakeBq:
        def __init__(self, clause):
            self.clause = clause

        def __call__(self, *_args, **_kwargs):
            query = f"ROW_NUMBER() OVER (\n  PARTITION BY {self.clause}\n  ORDER BY ingest_time DESC\n)"

            class Proc:
                returncode = 0
                stdout = json.dumps({"view": {"query": query}})
                stderr = ""

            return Proc()

    def test_it_passes_against_a_view_matching_the_repository(self):
        expected = cloud.repo_window_clause(cloud.SQL_DIR / "002_spans_deduped.sql")
        self.assertEqual(cloud.check_provenance(runner=self.FakeBq(expected)), expected)

    def test_it_fails_against_a_deliberately_mismatched_view(self):
        with self.assertRaises(cloud.Refused) as caught:
            cloud.check_provenance(runner=self.FakeBq("trace_id, span_id"))
        message = str(caught.exception)
        # The message must name both sides, or triage starts by re-deriving them.
        self.assertIn("trace_id, span_id, start_time", message)
        self.assertIn("deployed", message)

    def test_the_repository_clause_is_read_past_the_comments(self):
        # The file names the clause in prose as well as in the window (F2C-02, #91).
        # Reading the raw text would find the prose first and compare the wrong string.
        self.assertEqual(
            cloud.repo_window_clause(cloud.SQL_DIR / "002_spans_deduped.sql"),
            "trace_id, span_id, start_time",
        )


class StageResult(unittest.TestCase):
    """Decision 11. The stage names a branch of the runbook's fault tree."""

    def test_an_undeclared_stage_is_refused(self):
        with self.assertRaises(cloud.Refused):
            cloud.Result("run-alpha", "cloud").reached("nearly_done")

    def test_a_run_that_stopped_early_does_not_report_passed(self):
        result = cloud.Result("run-alpha", "cloud").reached("push_auth")
        self.assertFalse(result.document()["passed"])
        self.assertEqual(result.document()["stage"], "push_auth")

    def test_completion_is_the_only_passing_stage(self):
        result = cloud.Result("run-alpha", "cloud").reached("complete")
        self.assertTrue(result.document()["passed"])

    def test_the_stages_match_the_runbook_fault_tree_order(self):
        self.assertEqual(cloud.STAGES[0], "view_provenance")
        self.assertEqual(cloud.STAGES[-1], "complete")


class WallingProof(unittest.TestCase):
    """Decision 13. DoD 3 is a claim about rows, so the evidence is a query over rows."""

    def test_both_assertions_are_scoped_and_filtered(self):
        window = cloud.PartitionWindow(dt.date(2026, 8, 30), dt.date(2026, 9, 1))
        queries = cloud.walling_queries(window, "w4-first")
        self.assertEqual(set(queries), {"distinct_identity", "unflagged_rows"})
        for name, sql in queries.items():
            with self.subTest(name):
                self.assertIn("DATE(start_time) BETWEEN", sql)
                self.assertIn("'w4-first'", sql)
                self.assertIn("spans_deduped", sql)

    def test_the_proof_reads_the_view_not_the_base_table(self):
        # DoD 3 claims rows arrive *through the views*. The base table is an easier
        # question wearing the same answer.
        window = cloud.PartitionWindow(dt.date(2026, 8, 30), dt.date(2026, 9, 1))
        for sql in cloud.walling_queries(window, "w4-first").values():
            self.assertNotIn(f"{cloud.DATASET}.spans`", sql)


if __name__ == "__main__":
    unittest.main(verbosity=2)
