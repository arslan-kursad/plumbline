#!/usr/bin/env python3
"""Asserts that `spans_deduped` collapses a duplicate that actually exists.

The local stack writes through an explicit COMMITTED stream, which produces no
at-least-once duplicates (`docs/evidence/f3e-01a-emulator-divergence.md` S2). So the
end-to-end assertion `rows_seen = distinct_spans` passed identically whether dedup worked
or whether there was nothing to dedup — a working view and an absent duplicate are the
same output. This probe removes that ambiguity by asserting both halves:

    the base table holds two rows for a key, and the view returns exactly the later one.

Co-existence is not identity. "The view returned one row" is satisfied by a view that
drops rows, by a view that never had two, and by a view that works. Only the pair of
assertions separates them, which is why the base-table reading is not optional here.

The duplicate is produced by replaying a payload through the real write path — collector,
Pub/Sub, worker, Storage Write API — because that is what at-least-once redelivery looks
like. Nothing here writes a row directly: `insertAll` is a forbidden cost invariant
(`CLAUDE.md`), and a row inserted by the probe would not exercise the path the claim is
about.

Usage:
    python3 scripts/e2e/dedup-probe.py [--bigquery http://localhost:9050]
"""

import argparse
import importlib.util
import pathlib
import sys

# `query-rows.py` carries the hyphen, so it cannot be imported by name. Loading it keeps
# one definition of the query call and one of the timestamp conversion; a second copy
# here would be a second thing to keep in step with the stand-in's wire format.
_spec = importlib.util.spec_from_file_location(
    "query_rows", pathlib.Path(__file__).resolve().parent / "query-rows.py")
query_rows = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(query_rows)

PROJECT = "plumbline-local"

# The window key of `spans_deduped` is the triple, not the pair: `002_spans_deduped.sql`
# partitions by (trace_id, span_id, start_time) so a consumer's start_time predicate can
# be pushed below the window (ADR-0007 D2). A probe grouping by the pair alone would call
# two rows a duplicate that the view is designed to keep, and would then report the view
# as broken for doing what it says.
DUPLICATES_SQL = f"""
SELECT trace_id, span_id, COUNT(*) AS copies, MAX(ingest_time) AS latest
FROM `{PROJECT}.plumbline.spans`
WHERE start_time >= TIMESTAMP('2020-01-01')
GROUP BY trace_id, span_id, start_time
HAVING COUNT(*) > 1
"""

VIEW_SQL = f"""
SELECT trace_id, span_id, ingest_time
FROM `{PROJECT}.plumbline.spans_deduped`
WHERE start_time >= TIMESTAMP('2020-01-01')
"""


def verdict(duplicated, view_rows):
    """Compares the base table's duplicates against what the view returns.

    `duplicated` is one entry per key the base table holds more than once, carrying the
    copy count and the latest ingest_time. `view_rows` is every row the view returns.

    Returns a list of findings. Empty means the view collapsed every duplicate to its
    latest row and dropped none of them.
    """
    findings = []

    # An empty reading here is the failure, not a pass. If the replay presented no
    # duplicate, every assertion below is vacuous and the probe would report success
    # while measuring nothing — the empty-result blindness this file exists to close.
    if not duplicated:
        return ["the base table holds no duplicated key: the replay presented nothing to "
                "dedup, so this run proves nothing about the view"]

    seen = {}
    for row in view_rows:
        seen.setdefault((row["trace_id"], row["span_id"]), []).append(row["ingest_time"])

    for entry in duplicated:
        key = (entry["trace_id"], entry["span_id"])
        returned = seen.get(key, [])
        label = f"{key[0][:12]}…/{key[1][:8]}…"

        if len(returned) != 1:
            findings.append(
                f"{label}: base holds {entry['copies']} rows, view returns "
                f"{len(returned)} — expected exactly 1")
            continue

        if returned[0] != entry["latest"]:
            findings.append(
                f"{label}: view returned ingest_time {returned[0]}, but the later of the "
                f"{entry['copies']} base rows is {entry['latest']}")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bigquery", default="http://localhost:9050")
    args = parser.parse_args()

    duplicated = query_rows.rows(query_rows.query(args.bigquery, DUPLICATES_SQL))
    view_rows = query_rows.rows(query_rows.query(args.bigquery, VIEW_SQL))

    base_total = sum(int(entry["copies"]) for entry in duplicated)
    print(f"  base table: {len(duplicated)} duplicated key(s), {base_total} row(s) across them")
    print(f"  spans_deduped: {len(view_rows)} row(s) total")

    findings = verdict(duplicated, view_rows)
    if findings:
        print("\ndedup probe: FAIL", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1

    for entry in duplicated:
        print(f"  {entry['trace_id'][:12]}…/{entry['span_id'][:8]}…: "
              f"{entry['copies']} base rows -> 1 view row at {entry['latest']}")
    print("dedup probe: PASS — every duplicate collapsed to its latest row")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
