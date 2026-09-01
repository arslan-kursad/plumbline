"""Tests for the cloud harness's guards (directive v1.7, Decisions 6-13; §8).

§8 requires the guards be exercised in both directions: a check that has only ever
passed is not yet evidence. Every test here is written so it can fail -- the refusals
are asserted by triggering them, not by reading the code.

Run directly: python3 scripts/e2e/cloud_test.py
"""

import datetime as dt
import json
import pathlib
import re
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


class RunIdPath(unittest.TestCase):
    """Where the run id lands in the `attributes` column, pinned against real output.

    The obvious path -- `$."plumbline.e2e_run_id"` -- is wrong, and wrong in the quiet
    direction: JSON_VALUE returns NULL for every row, the run-scoped predicate matches
    nothing, and DoD 3's two assertions both pass over an empty set. It would have
    surfaced during the exam.

    So this asserts against a committed golden file, which is normalizer output, rather
    than against the string in the module -- a test that restated the constant would
    re-encode the bug rather than catch it.
    """

    def golden(self):
        path = cloud.FIXTURES / "claude-code" / "happy-path" / "expected-rows.json"
        return json.loads(path.read_text())[0]["attributes"]

    def test_resource_attributes_nest_under_resource(self):
        attributes = self.golden()
        self.assertIn("resource", attributes)
        self.assertIn("service.name", attributes["resource"])

    def test_a_resource_attribute_is_not_reachable_at_the_top_level(self):
        # The precise reason the obvious path fails.
        self.assertNotIn("service.name", self.golden())

    def test_the_run_id_path_addresses_the_resource_object(self):
        self.assertTrue(
            cloud.RUN_ID_JSON_PATH.startswith("$.resource."),
            f"{cloud.RUN_ID_JSON_PATH} does not address the object resource attributes land in",
        )
        self.assertIn(cloud.RUN_ID_ATTRIBUTE, cloud.RUN_ID_JSON_PATH)

    def test_the_corpus_writes_the_attribute_the_path_reads(self):
        # The two halves have to name the same key, or the corpus is scoped by one name
        # and queried by another.
        with tempfile.TemporaryDirectory() as tmp:
            payload = json.loads(cloud.build_corpus("run-alpha", pathlib.Path(tmp))[0].read_text())
            keys = [a["key"] for a in payload["resourceSpans"][0]["resource"]["attributes"]]
        self.assertIn(cloud.RUN_ID_ATTRIBUTE, keys)


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


class VolatileAllowlist(unittest.TestCase):
    """Decision 12. One list, in two languages, kept in step by this test.

    The harness excludes columns on the Python side and the local normalization excludes
    them on the C# side. Decision 12 asks for *one* checked-in constant; two constants
    that agree today are one constant only while something checks.
    """

    CSHARP = cloud.REPO / "worker" / "Plumbline.Fixtures" / "VolatileFields.cs"

    def csharp_keys(self):
        # The dictionary initialiser entries, e.g. ["ingest_time"] = "...".
        return set(re.findall(r'\["([a-z_]+)"\]\s*=', self.CSHARP.read_text()))

    def test_both_sides_exclude_the_same_columns(self):
        self.assertEqual(self.csharp_keys(), set(cloud.VOLATILE))

    def test_ingest_time_is_excluded_because_it_is_a_clock(self):
        self.assertIn("ingest_time", cloud.VOLATILE)

    def test_api_key_id_is_not_excluded(self):
        # Decision 12 admits it only if the two paths legitimately differ. The harness
        # hands the cloud run's key id to the local normalization, so they do not.
        self.assertNotIn("api_key_id", cloud.VOLATILE)
        self.assertNotIn("api_key_id", self.csharp_keys())

    def test_every_excluded_column_is_a_real_column(self):
        columns = {name for name, _ in cloud.projection()}
        for column in cloud.VOLATILE:
            with self.subTest(column):
                self.assertIn(column, columns)


class Projection(unittest.TestCase):
    """The wire shape is asked for, not inherited from the tool's defaults."""

    def test_timestamps_are_formatted_in_sql(self):
        # bq renders a TIMESTAMP as '2026-08-31 12:00:00' and drops the microseconds --
        # measured. The golden files carry six digits, so the diff would fail on every
        # row and blame normalization for a formatting difference.
        self.assertIn("FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M:%E6SZ', start_time)", cloud.select_list())

    def test_json_columns_are_stringified_then_parsed_back(self):
        self.assertIn("TO_JSON_STRING(attributes)", cloud.select_list())
        self.assertEqual(cloud.convert('{"a":1}', "JSON"), {"a": 1})

    def test_scalars_come_back_typed(self):
        self.assertIs(cloud.convert("true", "BOOLEAN"), True)
        self.assertIs(cloud.convert("false", "BOOLEAN"), False)
        self.assertEqual(cloud.convert("42", "INTEGER"), 42)
        self.assertEqual(cloud.convert("1.5", "FLOAT"), 1.5)
        self.assertIsNone(cloud.convert(None, "INTEGER"))

    def test_the_schema_comes_from_the_table_definition(self):
        columns = {name for name, _ in cloud.projection()}
        self.assertIn("synthetic", columns)
        self.assertIn("attributes", columns)
        self.assertGreater(len(columns), 20)


class GoldenDiff(unittest.TestCase):
    """Decision 12. It fails closed, and §8 requires that be demonstrated."""

    def row(self, **overrides):
        base = {"trace_id": "t1", "span_id": "s1", "name": "call", "synthetic": True,
                "ingest_time": "2026-08-31T00:00:00.000000Z"}
        base.update(overrides)
        return base

    def test_identical_rows_produce_no_findings(self):
        self.assertEqual(cloud.diff_rows([self.row()], [self.row()]), [])

    def test_a_volatile_field_may_differ(self):
        findings = cloud.diff_rows(
            [self.row()], [self.row(ingest_time="2027-01-01T00:00:00.000000Z")])
        self.assertEqual(findings, [])

    def test_a_non_allowlisted_field_that_differs_is_a_failure(self):
        findings = cloud.diff_rows([self.row()], [self.row(name="different")])
        self.assertEqual(len(findings), 1)
        self.assertIn("name", findings[0])

    def test_a_field_nobody_thought_about_is_still_caught(self):
        # The property that makes this an allowlist rather than a denylist.
        findings = cloud.diff_rows([self.row()], [self.row(some_future_column="x")])
        self.assertEqual(len(findings), 1)
        self.assertIn("some_future_column", findings[0])

    def test_a_span_missing_from_the_cloud_is_a_failure(self):
        findings = cloud.diff_rows([self.row()], [])
        self.assertEqual(len(findings), 1)
        self.assertIn("absent from the cloud view", findings[0])

    def test_an_unexpected_span_in_the_cloud_is_a_failure(self):
        # Scoped by run id, so this means the run wrote something the corpus did not.
        findings = cloud.diff_rows([], [self.row()])
        self.assertEqual(len(findings), 1)
        self.assertIn("not in the corpus", findings[0])

    def test_the_finding_names_both_sides(self):
        findings = cloud.diff_rows([self.row()], [self.row(name="other")])
        self.assertIn("local='call'", findings[0])
        self.assertIn("cloud='other'", findings[0])


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

    def test_the_exclusion_claim_reads_spans_real(self):
        # F2C-09 consequence 2. A different view proves a different claim, and the
        # runbook names which is which; asserting it against spans_deduped would prove
        # nothing about what F4's window will see.
        window = cloud.PartitionWindow(dt.date(2026, 8, 30), dt.date(2026, 9, 1))
        sql = cloud.exclusion_query(window, "w4-first")
        self.assertIn("spans_real", sql)
        self.assertNotIn("spans_deduped", sql)
        self.assertIn("DATE(start_time) BETWEEN", sql)
        self.assertIn("'w4-first'", sql)

    def test_the_two_claims_use_different_views(self):
        window = cloud.PartitionWindow(dt.date(2026, 8, 30), dt.date(2026, 9, 1))
        walling = cloud.walling_queries(window, "w4-first")
        self.assertTrue(all("spans_deduped" in sql for sql in walling.values()))
        self.assertIn("spans_real", cloud.exclusion_query(window, "w4-first"))

    def test_the_proof_reads_the_view_not_the_base_table(self):
        # DoD 3 claims rows arrive *through the views*. The base table is an easier
        # question wearing the same answer.
        window = cloud.PartitionWindow(dt.date(2026, 8, 30), dt.date(2026, 9, 1))
        for sql in cloud.walling_queries(window, "w4-first").values():
            self.assertNotIn(f"{cloud.DATASET}.spans`", sql)


if __name__ == "__main__":
    unittest.main(verbosity=2)
