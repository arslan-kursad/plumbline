# ADR-0007 — Canonical dedup views under `require_partition_filter`

**Status:** Proposed · **Date:** 2026-08-26
**Related issues:** #61 (dedup view semantics vs. partition guardrail)
**Affects:** architecture §4.1 (views), §3.3 (downstream dedup), §7 (cost guardrails)
**Number:** reserved 2026-08-26 when ADR-0008 was filed, so the index held 0007 open rather than letting the next decision take it.

---

## Context

`spans` is partitioned on `start_time` with `require_partition_filter = true` (§4.1, a
cost invariant per §7). Delivery is at-least-once (§3.3), so duplicates land in the table
and are eliminated at query time by the canonical views `spans_deduped` and `spans_real`,
which all consumers read instead of the base table.

The views as originally specified dedup with
`ROW_NUMBER() OVER (PARTITION BY trace_id, span_id ORDER BY ingest_time DESC)`. A filter
on `start_time` cannot be pushed below that window, because pushing a predicate below a
window function is only valid when the predicate references columns in the window's
`PARTITION BY` clause — and `start_time` is not one. The inner scan therefore has no
partition predicate and the guardrail rejects the query. `spans_real`, built on top,
inherits the failure. This blocked Wave 4 arming.

The premise that resolves it: **two rows for the same `(trace_id, span_id)` always carry
the same `start_time`.** Duplicates originate from redelivery of identical OTLP bytes —
Pub/Sub redelivery, collector publish retry, Storage Write API default-stream retry,
SDK export retry — and `start_time` is derived from the span's `start_time_unix_nano`,
which is identical across those copies. Both copies land in the same partition. The
cross-partition window that appeared to be required was never actually required.

## Decision

**D1 — Keep `require_partition_filter = true`.** It is a cost invariant; the conflict is
resolved in the view definition, not by relaxing the guardrail.

**D2 — Add `start_time` to the window's `PARTITION BY`.**

```sql
ROW_NUMBER() OVER (PARTITION BY trace_id, span_id, start_time ORDER BY ingest_time DESC)
```

Under the premise above this is semantically identical to the original two-column window,
and it makes a consumer's `start_time` predicate legal to push below the window.

**D3 — No date predicate inside the views.** The views carry no `INTERVAL n DAY` window
and no other embedded time bound. §4.1 semantics are unchanged: the views dedup and
filter `synthetic`, nothing else.

**D4 — Consumers supply their own partition filter.** Every query against `spans_deduped`
or `spans_real` must carry a `start_time` predicate. This is the guardrail working as
designed: embedding a filter in the view would hide a cost control behind convenience,
which is what produced this conflict.

**D5 — No table-valued function.** Arbitrary ranges are served by D4. Looker Studio binds
directly to the views as a normal data source; the F4 risk that a TVF would break that
binding is retired.

**D6 — The dedup key change is recorded as a semantic change, not an implementation
detail.** The effective key becomes `(trace_id, span_id, start_time)`. Where the premise
holds the two are equivalent. Where it breaks they diverge, and the divergence is
directional:

| | premise holds | premise broken |
|---|---|---|
| old key `(trace_id, span_id)` | one row | one row — the other is **dropped** |
| new key `+ start_time` | one row | two rows retained |

The new shape fails toward retention, and extra rows are observable. The old shape fails
toward silent loss. For a project whose stated principle is *no silent degradation*, the
new shape is the better failure mode, and in the case of a genuine `span_id` collision
between two distinct spans it is strictly more correct.

**D7 — The premise is an invariant with an enforcement point, not an assumption.** It is
now load-bearing for correctness, not only for performance.

| Invariant | Enforcement point |
|---|---|
| `start_time_unix_nano` → BigQuery `TIMESTAMP` conversion is deterministic and stable across worker versions | Golden-file test asserting the exact converted value; a change to the conversion is a breaking change requiring an ADR |
| No `(trace_id, span_id)` group carries more than one distinct `start_time` | Standing check query (below), run once real data exists and on each F4 weekly review |

**The conversion clause was checked against the code before this ADR was filed, and it
holds.** `Timestamps.FromUnixNanos` (`worker/Plumbline.Normalization/Rows/SpanRow.cs`)
already truncates — `unixNanos / NanosPerMicrosecond` is integer division on a `ulong` —
and its own remarks say so: *"The remaining three digits are dropped, not rounded."* No
`Math.Round` exists on this path.

The golden test that pins it exists too, and it was **proven to fail** rather than assumed
to. `testdata/fixtures/langgraph-python/happy-path` carries
`endTimeUnixNano: 1787133601612345678`, and its golden file pins
`end_time: 2026-08-19T10:00:01.612345Z`. Switching the conversion to round-half-up as a
probe produces exactly the ADR's failure mode:

```
Failed GoldenFileTests.NormalizedRowsMatchTheGoldenFile(fixture: langgraph-python/happy-path)
  rows[2].end_time: expected "2026-08-19T10:00:01.612345Z", actual "2026-08-19T10:00:01.612346Z"
```

One microsecond, in a fixture chosen for that boundary. The probe was reverted.

The conversion clause is not decorative. OTLP expresses start time in **nanoseconds**;
BigQuery `TIMESTAMP` has **microsecond** precision, so the write path contains a lossy
narrowing step. If two deliveries of the same bytes are processed by different worker
revisions — a DLQ replay after a deploy is exactly this case — and the rounding behaviour
of that step changed between them (truncate vs. round-half-up differ by up to 1 µs), the
two rows get different `start_time` values and dedup silently stops matching them. The
conversion must therefore be specified (truncation toward zero), implemented once, and
pinned by a golden test.

## Alternatives rejected

- **Range-scoped table-valued function `spans_deduped(from, to)`** — works, but requires
  every consumer to change call shape and leaves Looker Studio's TVF binding as an
  unverified F4 risk. D2 makes it unnecessary.
- **Bounded window inside the view (`INTERVAL n DAY`)** — would have worked (untested;
  T1 passed first), but changes §4.1 semantics: the canonical views would silently stop
  representing the table beyond the window, and out-of-window access would need the TVF
  after all. Retained as the fallback if D2's optimizer behaviour ever regresses.
- **Move dedup to consumers** — rejected by ADR-0002; duplicates would reach dashboards
  and the eval engine.
- **Drop `require_partition_filter`** — rejected by the cost invariant (§7).
- **Materialized view / scheduled dedup table** — introduces new resource types and a
  second write path, adds latency between ingest and visibility, and lands in F3 budget
  territory for a problem D2 solves with a view definition.

## Consequences

- **§4.1 is amended:** the `spans_deduped` definition changes to the three-column window;
  a sentence records the effective dedup key and D6's failure direction; a sentence records
  that consumers must supply a partition filter.
- **§3.3 gains a pointer** to the premise, since "dedup is downstream" now depends on it.
- **Every consumer query carries a `start_time` predicate** — SPA nightly export, eval
  engine reads, Looker data source, ad-hoc runbook queries. Repo-resident SQL without such
  a predicate should be treated as a defect; a lightweight CI grep over `.sql` assets is
  cheap and worth adding when there is enough SQL in the repo to justify it.
- **D2 relies on optimizer behaviour that Google does not document as a contract.** If a
  future BigQuery change stops pushing the predicate below the window, the views fail with
  the guardrail error — loudly, at query time, not silently with wrong results. The
  fallback is the bounded-window alternative above. Acceptable because the failure is loud.
- **Clustering is unaffected**; `(trace_id, span_id)` clustering is a storage property and
  independent of the query-time window.

## Verification

Performed 2026-08-26 against the live dataset, single session, single variable:

| Experiment | Result |
|---|---|
| Existing `spans_deduped` + consumer `WHERE start_time >= …` | Failed: cannot query without a filter over `start_time` |
| Base table, no filter (**negative control**) | Failed — constraint is enforced even on an empty table |
| **T1**: `PARTITION BY trace_id, span_id, start_time`, no predicate in view | **Passed** |
| `spans_real` equivalent stacked on T1 | **Passed** |

The negative control is the reason the result is trustworthy: on an empty table a passing
query is also consistent with the constraint not being enforced at all. It is enforced,
and T1 passes anyway. The chained test was required because #61 recorded that `spans_real`
inherited the failure; under the new shape it does not.

Test views were dropped afterwards; the dataset holds only Terraform-owned objects.

**Outstanding, due when real data exists (F4):**

```sql
SELECT trace_id, span_id, COUNT(DISTINCT start_time) AS distinct_starts
FROM `plumbline.spans`
WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY trace_id, span_id
HAVING distinct_starts > 1;
```

Any row returned falsifies the premise. Expected result: empty. A non-empty result is not
a data-loss incident — it means duplicates went undeduplicated and are visible in the
views — but it requires an incident note and reopens this ADR.
