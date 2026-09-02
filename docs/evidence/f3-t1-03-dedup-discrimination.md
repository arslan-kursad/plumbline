# T1-03 — the dedup view, shown to be asserted rather than assumed

**Measured:** 2026-09-02 · **Lane:** A · **Branch:** `feat/f3-t1-03-local-duplicates`
**Task:** [`F3-prerequisite-directive.md`](../specs/F3-prerequisite-directive.md) T1-03
**Charter:** [`f3e-01a-emulator-divergence.md`](f3e-01a-emulator-divergence.md) S2;
[`architecture.md`](../architecture.md) §3.3

Both runs are CI runs. The Lane A host runs no containers (standing requirement R-F), so
neither could be produced locally and neither is quoted from a local invocation.

---

## The finding being repaired

The local sink writes through an explicit `COMMITTED` stream, which produces no
at-least-once duplicates. So the end-to-end assertion that exercises `spans_deduped` held
identically whether dedup worked or whether there was nothing to dedup — **a working view
and an absent duplicate are the same output**. S2 stated it as *"the local assertion
`rows_seen = distinct_spans` passes both when dedup works and when there was nothing to
dedup."*

## The green run

**Run [`33650089405`](https://github.com/arslan-kursad/plumbline/actions/runs/33650089405)**,
job `local end-to-end`, 1m52s, conclusion **success**.

```
=== replaying claude-code/happy-path to produce a duplicate
=== waiting for the replayed rows to land
  base table should reach 16 row(s): 13 + 3 replayed
  16 row(s) in the base table after 1s
  base table: 3 duplicated key(s), 6 row(s) across them
  spans_deduped: 13 row(s) total
dedup probe: PASS — every duplicate collapsed to its latest row
```

**Both halves are asserted, which is the point** (standing requirement R-B). The base table
holds 16 rows with three keys duplicated across six of them, **and** the view returns 13 —
one row per key, each the later `ingest_time`. "The view returned one row" alone is satisfied
by a view that drops rows, by a view that never had two, and by a view that works; only the
pair separates them.

## The red run

**Run [`33650374134`](https://github.com/arslan-kursad/plumbline/actions/runs/33650374134)**,
branch `probe/f3-t1-03-red-run`, conclusion **failure**.

The mutation is one line: `WHERE duplicate_rank = 1` removed from
[`002_spans_deduped.sql`](../../analytics/sql/002_spans_deduped.sql), which turns the view
into a passthrough over the base table.

```
=== asserting the dedup view returns the later row, not just one row
  base table: 3 duplicated key(s), 6 row(s) across them
dedup probe: FAIL
  e5d4c3b2a190…/0f1e2d3c…: base holds 2 rows, view returns 2 — expected exactly 1
  e5d4c3b2a190…/1e2d3c4b…: base holds 2 rows, view returns 2 — expected exactly 1
  e5d4c3b2a190…/2d3c4b5a…: base holds 2 rows, view returns 2 — expected exactly 1
  spans_deduped did not collapse the duplicate correctly
```

Every other job in that run passed: `collector (go)`, `worker and analytics (.net)`,
`kill-switch function (go)`, `terraform static checks`, `terraform plan (wif)`,
`images (distroless)`, `invariant gates`, `changed paths`. The only failure is
`local end-to-end`, and within it the only failing step is the new one.

## What the red run actually proves, and it is more than "the check can fail"

**Every pre-existing assertion passed against a dedup view whose predicate had been
deleted.** From the same failing run, before the replay:

```
  spans_deduped: 13 row(s) -> .e2e/spans_deduped.ndjson
  spans_real: 13 row(s) -> .e2e/spans_real.ndjson
  spans_real agrees with spans_deduped (13 rows, none synthetic)
=== comparing against the golden files
  ok    claude-code/happy-path: 3 row(s) match the golden file
  ok    claude-code/unmapped-attributes: 1 row(s) match the golden file
  ok    dotnet-agent/happy-path: 3 row(s) match the golden file
  ok    dotnet-agent/unmapped-attributes: 1 row(s) match the golden file
  ok    langgraph-python/happy-path: 3 row(s) match the golden file
  ok    langgraph-python/unmapped-attributes: 1 row(s) match the golden file
  ok    unknown/happy-path: 1 row(s) match the golden file
pipeline output matches every golden file
```

The view was a no-op passthrough and **the entire existing corpus called it correct** —
seven golden files, the `spans_real` cross-check, and the row-count wait. The defect became
visible only once a duplicate existed for the view to mishandle, which is the whole of S2's
argument, now measured rather than reasoned.

## How the duplicate is produced

By **replaying one payload through the real write path** — collector, Pub/Sub, worker,
Storage Write API — because that is what at-least-once redelivery looks like, and because
`IngestionEndpoint.cs:24` records that *"deduplication is deliberately absent"* in the
worker. Nothing is written beside the pipeline: `insertAll` is a forbidden cost invariant
(`CLAUDE.md`), and an injected row would not exercise the path the claim is about.

The stream type is **not** changed. T1-03 is separable from stream parity, which
[`F3-prerequisite-directive.md`](../specs/F3-prerequisite-directive.md) closed as T1-04 —
the stand-in cannot resolve `_default` at all.

## Two details that would have made the probe wrong

**The window key is the triple, not the pair.**
[`002_spans_deduped.sql`](../../analytics/sql/002_spans_deduped.sql)`:37` partitions by
`(trace_id, span_id, start_time)` so a consumer's `start_time` predicate can be pushed below
the window (ADR-0007 D2). A probe grouping by the pair alone would call two rows a duplicate
that the view is **designed** to keep, and would then report the view broken for doing what
its comment says it does. The probe groups by the triple.

**The replay excludes poison.** The dead-letter check asserts an exact depth, so re-sending
the poison payloads would double it and fail a check that has nothing to do with dedup.
`PLUMBLINE_ONLY` carries that restriction, and a filter matching nothing is **refused**
rather than reported as an empty success — the same rule the probe applies to its own empty
reading.

## The empty reading is a failure, not a pass

[`dedup-probe.py`](../../scripts/e2e/dedup-probe.py) treats an empty duplicate set as a
finding: *"the base table holds no duplicated key: the replay presented nothing to dedup, so
this run proves nothing about the view."* Without that, a replay that silently failed to land
would produce a green probe over zero duplicates — the empty-result blindness class this
phase has now produced four times, and the exact failure mode T1-03 exists to remove.

Nine unit tests cover the verdict, one per way a dedup view can be wrong — both rows
returned, the earlier row returned, the key dropped entirely, one broken key among several —
plus the absent-duplicate case. They run in `invariant gates` and need no containers.

## Housekeeping

`probe/f3-t1-03-red-run` is a throwaway branch carrying the deliberate mutation. It is **not
for merge**. The run it produced is preserved in Actions independently of the branch, so the
branch can be deleted after review without costing the evidence.
