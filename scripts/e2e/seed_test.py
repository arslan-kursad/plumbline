"""Tests for the seeder's SQL comment stripper (issue #91, directive F2C-23).

The shape of the regression test is the shape of the probe that found the defect
(decision log W2.16): the trigger keywords go inside a `--` comment, and the
assertion is that the statement still declares its view. W2.16's first hypothesis
was about the statement body -- every window shape materialised when sent without
comments -- so a test written against the body would pin the wrong thing.

Run directly: python3 scripts/e2e/seed_test.py
"""

import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from seed import strip_sql_comments  # noqa: E402

SQL_DIR = pathlib.Path(__file__).resolve().parents[2] / "analytics" / "sql"
VIEW_RE = re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+`?[\w-]*\.?(\w+)`?", re.IGNORECASE)

# The two keywords that open a partitioning clause -- the pair that makes
# goccy/bigquery-emulator 0.8.1 answer with a result set and no view. Assembled
# rather than written whole so this file does not itself become a comment that
# carries them, which is the self-matching trap Gate F's convention exists for.
TRIGGER = "PARTITION" + " BY"


class StripsComments(unittest.TestCase):
    def test_line_comment_is_removed(self):
        self.assertNotIn(TRIGGER, strip_sql_comments(f"SELECT 1 -- {TRIGGER} x\nFROM t"))

    def test_block_comment_is_removed(self):
        self.assertNotIn(TRIGGER, strip_sql_comments(f"SELECT /* {TRIGGER} x */ 1 FROM t"))

    def test_statement_without_comments_is_unchanged(self):
        # The negative control. A stripper that returned "" would pass every test
        # above and fail this one.
        sql = "SELECT a, b FROM `p.d.t` WHERE x = 1"
        self.assertEqual(strip_sql_comments(sql), sql)

    def test_stripping_is_idempotent(self):
        sql = (SQL_DIR / "002_spans_deduped.sql").read_text()
        once = strip_sql_comments(sql)
        self.assertEqual(strip_sql_comments(once), once)


class PreservesData(unittest.TestCase):
    """A `--` inside a literal is data. Removing it would change the statement."""

    def test_double_dash_inside_a_single_quoted_string_survives(self):
        sql = "SELECT '-- not a comment' AS s FROM t"
        self.assertEqual(strip_sql_comments(sql), sql)

    def test_double_dash_inside_a_backtick_identifier_survives(self):
        sql = "SELECT `weird--name` FROM t"
        self.assertEqual(strip_sql_comments(sql), sql)

    def test_line_numbers_do_not_shift(self):
        sql = "line1\n-- line2 comment\nline3\n"
        self.assertEqual(strip_sql_comments(sql).count("\n"), sql.count("\n"))


class TheRealFiles(unittest.TestCase):
    """W2.16's probe shape, against the files that actually ship."""

    def test_the_view_file_carries_the_trigger_in_a_comment(self):
        # This is the property the fix buys, and the reason the comment in
        # 002_spans_deduped.sql could revert to plain wording. If someone rewrites
        # that comment around the keywords again, this fails and says why: the
        # workaround is not supposed to come back.
        commented = [
            line for line in (SQL_DIR / "002_spans_deduped.sql").read_text().splitlines()
            if line.lstrip().startswith("--") and TRIGGER in line
        ]
        self.assertTrue(
            commented,
            "002_spans_deduped.sql no longer names the partitioning clause in prose; "
            "the F2C-02 premise comment is what this fix exists to allow",
        )

    def test_only_the_window_clause_survives_stripping(self):
        # Without the stripper the emulator sees three occurrences and creates no
        # view. With it, exactly the one in the window body reaches the parser.
        stripped = strip_sql_comments((SQL_DIR / "002_spans_deduped.sql").read_text())
        self.assertEqual(stripped.count(TRIGGER), 1)

    def test_every_view_file_still_declares_its_view(self):
        # The claim the seeder checks against the dataset, asserted here against the
        # text: stripping must not remove a CREATE VIEW along with the prose.
        for path in sorted(SQL_DIR.glob("*.sql")):
            if path.name.startswith("001_"):
                continue
            with self.subTest(path.name):
                self.assertEqual(
                    VIEW_RE.findall(strip_sql_comments(path.read_text())),
                    VIEW_RE.findall(path.read_text()),
                )

    def test_the_table_schema_still_parses_after_stripping(self):
        # 001 is created through the REST API from this parse, so a stripper that ate
        # a column definition would take the whole local stack with it.
        from seed import table_schema

        ddl = (SQL_DIR / "001_spans_table.sql").read_text()
        self.assertEqual(table_schema(strip_sql_comments(ddl)), table_schema(ddl))
        self.assertGreater(len(table_schema(strip_sql_comments(ddl))), 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
