# F3E-01b — Rejection probe: what production refuses

**Measured:** 2026-09-02 · **Lane:** A · **Repo:** `main` @ `770f7d2`
**Project:** `plumbline-19458` · **Mechanism:** `bq query --dry_run`, which creates nothing
**Task:** [`F3-entry-directive.md`](../specs/F3-entry-directive.md) F3E-01b
**Scoped from:** [`f3e-01a-emulator-divergence.md`](f3e-01a-emulator-divergence.md)

Reproduce with `scripts/probe/rejection-probe.sh`. Four cases ran; three surfaces were not
probed and are named below with the reason, which is what the acceptance asks for when a
report cannot be complete.

**No mutation.** Every statement was a dry run. The precedent is decision log W2.17, where
the same mechanism settled the comment-parsing question at no cost.

---

## Result

| Case | Production | Expected |
|---|---|---|
| `spans`, no partition predicate | **REJECTED** | rejected |
| `spans`, with partition predicate | VALIDATED | validated — the control |
| `spans_deduped`, no partition predicate | **REJECTED** | rejected |
| Comment naming `PARTITION BY` | VALIDATED | validated |

## S1 — `require_partition_filter` — divergence confirmed, emulator-permissive

Production, verbatim:

```
Error in query string: Cannot query over table 'plumbline-19458.plumbline.spans'
without a filter over column(s) 'start_time' that can be used for partition
elimination
```

The same query with `WHERE start_time >= "2026-08-01"` validates and reports an upper
bound of 416 bytes. **The control matters:** a probe that only ever sees rejection is
measuring that the table exists, not that the constraint holds.

`spans_deduped` rejects identically, so the requirement reaches through the view — which is
what [`002_spans_deduped.sql`](../../analytics/sql/002_spans_deduped.sql) claims in prose
and is now measured rather than claimed.

**The local side is not executed, and is settled by construction instead.**
`scripts/e2e/seed.py:187-193` creates the local table through the REST API with columns
only, because the stand-in refuses `CREATE TABLE … PARTITION BY`. A table with no
`timePartitioning` cannot carry a partition-filter requirement under BigQuery semantics, so
the local side accepts what production rejected here. That is a derivation from the code
that creates the table, not a measurement, and it is labelled as one.

**Direction: emulator-permissive.** CI green over a statement the cloud refuses. This is the
direction the F2 closure note recorded as unmeasured, and it now has one confirmed instance.

**What it does and does not imply.** It does not mean anything in the repository is broken:
`seed.py:195-199` records that the local query step carries a partition filter anyway, and
the e2e run prints `unpartitioned` on every execution. What it means is that the habit is
enforced by convention locally and by the engine in the cloud, so **a query written outside
the e2e path — a view, a dashboard, an eval-engine read — meets no local objection.** That
is the gap, and it is a gap in coverage rather than in behaviour.

## S3 — DDL comment handling — no divergence in this direction

A query whose `--` comment contains `PARTITION BY` validates in production. The emulator
matches the keyword inside the comment and misparses the statement (W2.16), which is why
`seed.py` strips comments before posting.

**Direction: production-permissive.** Harmless, and re-asserted here so a regression in the
mitigation would surface rather than being rediscovered.

---

## Not probed, and why

| Surface | Reason |
|---|---|
| S2 — write-stream semantics | Needs a write. **F3E-01c, Lane C.** |
| S4 — JSON round-trip | Needs a row written and read back; no dry run produces one. **F3E-01c, Lane C.** |
| S5 — column-name matching | Same. |
| Local side of S1 and S3 | Needs the emulator running. **No container runtime on the Lane A host** — derived from `seed.py`, not executed. |

Four of seven surfaces are therefore unprobed by this task, and three of them are unprobed
*by design* rather than by omission: the lane boundary F3E-01a identified runs exactly
there, and crossing it inside this task is the failure §8 tells it to stop at.

## What this establishes

**One confirmed emulator-permissive divergence**, in the surface the inventory ranked most
likely, measured on the production side and derived on the local side.

It is not a claim that the pipeline is correct. S2 remains the one with the sharpest
consequence — the local `COMMITTED` stream does not produce the at-least-once duplicates
`spans_deduped` exists to remove, so the local assertion `rows_seen = distinct_spans`
passes both when dedup works and when there was nothing to dedup. **That surface needs a
write, and this task may not make one.**
