# Idempotence — asserted by replay, not by two invocations

**Measured:** 2026-09-01 · **Spec:** F2 §Wave 4, *"run it twice and show row counts through
the views stay stable"* · **Run:** `w4-third-delivery`, delivered three times

## Why two runs were not the test

The first attempt at this used two runs with different ids and produced `base = 26,
deduped = 26` — **no duplicate was ever presented.** Decision 6 derives span identity from
the run id (#102), so two run ids are two identities and the dedup window has nothing to
collapse. Two invocations of a harness that re-identifies per run is not a replay, and only
a replay tests what ADR-0002 rests on (W3.19).

The test is therefore *the same run id, again* — which reproduces the derived identity and
the untouched `start_time`, and so presents the window a genuine duplicate.

## The measurement

`w4-third-delivery` was delivered three times. Distinct write batches, from `ingest_time`:

| Window | Rows written |
| --- | --- |
| 03:55:03 – 03:55:19 | 13 |
| 04:09:10 – 04:09:28 | 13 |
| 04:19:23 – 04:19:43 | 13 |

| Object | Rows |
| --- | --- |
| `spans` (base table) | **39** for this run — every delivery retained |
| `spans_deduped` | **13** — one row per `(trace_id, span_id)` |
| `spans_real` | **0** — the walling holds under replay too |

Across both runs in the window: `base = 52`, `deduped = 26`. **The view count did not move
when the base table tripled**, which is the property the spec asks for, stated the way it
can fail.

## The tie-break is the one ADR-0007 specifies

```sql
SELECT MAX(ingest_time) FROM `…spans` = MAX(ingest_time) FROM `…spans_deduped` → true
```

The surviving row is the latest write, which is `ORDER BY ingest_time DESC` in the window
behaving as documented rather than as assumed.

## What this proves and what it does not

**Proves:** duplicates are retained in the base table and collapsed by the view; the
collapse is stable across three presentations; the survivor is deterministic and is the
latest write; synthetic walling survives replay.

**Does not prove** the dedup *premise* — that redeliveries carry an identical `start_time`.
Here they do by construction, because the corpus is static and Decision 6 leaves
`start_time` alone. The premise's real hazard is a nanosecond-to-microsecond conversion
differing between worker revisions, and the check for that is the runbook's dedup premise
query against real traffic, not this.

**Three deliveries, not two.** The spec asks for two; the third arrived because the run was
repeated once more than planned. Recorded as measured rather than trimmed to the number the
spec names — and it makes the result stronger, not weaker.
