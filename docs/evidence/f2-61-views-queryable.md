# #61 — the canonical views are queryable, measured after Wave 4

**Measured:** 2026-09-01T02:12Z · **Directive item:** Stage 3 step 11, first half
**Apply:** deploy run [`33461116779`](https://github.com/arslan-kursad/plumbline/actions/runs/33461116779), wave 4, issue #61
**Nothing here is inherited** (spec §7.2 CN4). Every reading was taken after the apply.

## The claim, and why an apply succeeding is not it

#61 closes on **a partition-filtered read succeeding against the cloud views**. A
successful apply is not that claim: #82 merged the corrected definitions on 2026-08-31 and
did not deploy them, which is precisely how the gap survived a merge.

## 1. The deployed definition, read from the API

```
PARTITION BY trace_id, span_id, start_time
```

Three columns. Before the apply, read 2026-08-31, it was `trace_id, span_id`
([`f2-state-readout`](f2-state-readout-2026-08-31.md) §5).

## 2. The read that was refused, now succeeding

Same query shape, one day apart.

**2026-08-31, before:**

```
Error in query string: Cannot query over table 'plumbline-19458.plumbline.spans'
without a filter over column(s) 'start_time' that can be used for partition elimination
```

**2026-09-01, after:**

```
[{"rows_seen":"0"}]
```

**Zero rows is the correct answer and is not the claim.** Nothing has been published to
`traces`; the claim is that the query *executes*. Under the two-column window it did not,
because a predicate may only be pushed below a window function when it references the
columns the window partitions on — so `require_partition_filter` refused the inner scan and
the views could not be queried at all.

## 3. The harness's own provenance check, both directions

Stage 0 compares the deployed DDL to the repository and aborts on a mismatch. It has now
done both, against reality rather than a fixture:

| When | Result |
| --- | --- |
| 2026-08-31 | refused, naming `repo: trace_id, span_id, start_time` against `deployed: trace_id, span_id` |
| 2026-09-01 | `MATCH: PARTITION BY trace_id, span_id, start_time` |

§8 asks that this check be shown to fail and to pass. It was not arranged; it is what
happened.

## 4. State readout — no failed readings

`scripts/state-readout.sh` exits 0. Its row-count reading, which failed yesterday with the
error in §2 and was left failing rather than routed around, now returns an empty result
set. Both Cloud Run services report image `9f70a875`, and `traces-dlq-pull` depth is 0 —
the drill's precondition, read before the drill rather than asserted during it.

## What this does not prove

- **Not DoD 3.** No row has reached the views. DoD 3 needs rows that arrived through them,
  flagged, and that is F2C-12 after the first delivery.
- **Not DoD 7b.** No message has been published to `traces`; push authentication has still
  never seen a real Google-signed token.
- **Not that the apply was harmless in general.** It changed three resources; this document
  measures one of them and reads the image tag of the other two.
