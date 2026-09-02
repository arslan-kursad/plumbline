# F3E-01a — Emulator/production divergence: surface inventory

**Measured:** 2026-09-02 · **Lane:** A · **Repo:** `main` @ `efaa272`
**Charter:** [`F2-completion-note.md`](../specs/F2-completion-note.md) §5 — *"the
emulator/production divergence is real and only half-measured … Carried to F3."*
**Task:** [`F3-entry-directive.md`](../specs/F3-entry-directive.md) F3E-01a

**Read-only.** Nothing was executed against the cloud project and no container was started;
this host has no container runtime. Every entry cites the file and line it was read from.
Entries that could not be settled by reading say **unknown** rather than guessing, which
the task's acceptance prefers.

**Direction is the whole point.** *Emulator-permissive* — local green where production
would reject — is the only failure that matters, because it is the one that ships. The
opposite direction is noisy and harmless. The one divergence measured before today
(W2.16/W2.17) was in the harmless direction, and the note already records that the
dangerous direction is unmeasured.

---

## Summary

| # | Surface | Can diverge? | Direction if it does |
|---|---|---|---|
| S1 | Partitioning and `require_partition_filter` | **yes, by construction** | **emulator-permissive** |
| S2 | Write-stream type and delivery semantics | **yes, by construction** | **emulator-permissive** |
| S3 | DDL comment handling | **yes, measured** | production-permissive (harmless) |
| S4 | JSON column round-trip | unknown | unknown |
| S5 | Column-name matching | unknown | unknown |
| S6 | Nanosecond → microsecond TIMESTAMP truncation | **no** | — |
| S7 | Column set drift between DDL and Terraform | **no** | — |

Two surfaces diverge *by construction* rather than by defect, and both in the direction
that matters. Neither is a bug to fix; both are properties of the local stack that bound
what a green local run is allowed to mean.

---

## S1 — Partitioning and `require_partition_filter`

**The two tables are structurally different, and the repository says so in the file that
makes them different.**

The cloud table is partitioned on `start_time` with `require_partition_filter = true`
(`infra/terraform/bigquery.tf:88`). The local table is created through the REST API from
the same DDL, columns only:

> *"The stand-in refuses `CREATE TABLE … PARTITION BY` outright, and a table created
> through this API carrying `timePartitioning` does not resolve on its Storage Write
> default stream either — measured, both times, in CI. So the local table is an
> unpartitioned, unclustered copy of the same columns."*
> — `scripts/e2e/seed.py:187-193`

**Direction: emulator-permissive.** A query with no partition predicate succeeds locally
and is rejected by production. That is CI green over a statement the cloud refuses, which
is the shipping failure.

**Already mitigated, partially.** `seed.py:195-199` records that the local query step
carries a partition filter anyway, "exactly as a dashboard would have to", and the run
prints `unpartitioned` on every execution rather than burying it. So the *habit* is
enforced locally even though the *constraint* is not. What is not covered is a query
written elsewhere — a view, a dashboard, an eval-engine read — that omits the filter and
meets no local objection.

## S2 — Write-stream type and delivery semantics

**Production writes to the implicit `_default` stream; local creates an explicit
`COMMITTED` stream.**

- Production: `WriteStreamName.FormatProjectDatasetTableStream(…, "_default")` —
  `worker/Plumbline.Worker/Sinks/BigQueryStorageWriteSink.cs:187-188`
- Local: `CreateWriteStreamAsync(… Type = WriteStream.Types.Type.Committed)` — `:198-203`

The sink's own remark says the semantics are unchanged because *"the emulator creates its
own default stream as `COMMITTED` anyway"* (`:179-181`). That is true about the emulator
and it is the reason the divergence exists rather than a reason it does not matter.

**Why it matters here specifically.** The default stream is at-least-once, and the entire
dedup design rests on that: `spans_deduped` exists because duplicates are expected
(ADR-0002, architecture §3.3). A `COMMITTED` stream does not produce the duplicates the
views exist to remove.

**Direction: emulator-permissive.** A defect in the dedup path — a wrong window, a
mis-stated key, a view that silently drops rows — is less likely to be exposed locally,
because the local run may present no duplicates for it to mishandle. The local end-to-end
asserts `rows_seen = distinct_spans` on 13 rows per view; that assertion passes both when
dedup works and when there was nothing to dedup.

**Not measured:** whether the local stack ever produces a duplicate at all. Answering it
needs a run, and this host cannot start the stack.

## S3 — DDL comment handling — the one already measured

`goccy/bigquery-emulator` 0.8.1 scans statement text for keywords that open a partitioning
clause and matches them inside `--` comments, which suppressed view creation. Real
BigQuery parses the same text correctly, confirmed by `bq query --dry_run` against
`plumbline-19458` (decision log W2.16, W2.17).

**Direction: production-permissive.** CI fails on SQL production accepts. Loud, harmless,
and fixed by stripping comments before posting (`scripts/e2e/seed.py:66-67`).

Recorded here because it is the *only* divergence this project has actually measured, and
because its direction is the one that does not matter — which is exactly why the closure
note flagged the unobserved direction as the open risk.

## S4 — JSON column round-trip — **unknown**

`attributes`, `events` and `links` are `JSON NOT NULL`
(`analytics/sql/001_spans_table.sql:51-53`) and carry the losslessness claim SC-1 row 1.3
rests on. Whether 0.8.1 stores and returns JSON byte-identically — key order, unicode
escaping, number formatting — was not established by reading, and the emulator's
documentation was not consulted from this host.

**Unknown, and deliberately not assumed.** If it normalises, a local round-trip test would
pass over a transformation production does not perform, or vice versa. This is the surface
with the most direct line to a success criterion.

## S5 — Column-name matching — **unknown**

The compose pin comment records that the 0.7 series carries *"the Storage Write fixes for
wrapper types and case-insensitive column matching"* (`docker-compose.yml:37-38`). That
sentence implies the emulator matched column names case-insensitively before the fix; it
does not establish what 0.8.1 does now, nor what production does.

All `gen_ai_*` columns are lower-snake `STRING` (`001_spans_table.sql:33-40`) and the proto
twin is generated, so nothing in the current corpus would exercise a case difference.
**Unknown, and low exposure today** — it becomes live if a mapping ever emits a
differently-cased key.

## S6 — Nanosecond → microsecond truncation — **cannot diverge**

OTLP carries nanoseconds; BigQuery `TIMESTAMP` holds microseconds. The conversion happens
in the worker, before either write path is chosen:
`worker/Plumbline.Normalization/Rows/SpanRow.cs:135-151`, with the truncation pinned and
documented at the sub-microsecond boundary.

Both paths therefore receive the same already-truncated value. There is no second
implementation for the emulator to disagree with. ADR-0007 records a related rounding
question, and it too is settled in code rather than at the sink.

## S7 — Column set drift — **cannot diverge, and this is a control rather than luck**

The Terraform JSON schema is generated from the same DDL the local stand-in parses, and a
CI diff guards the pair (`scripts/ci/bq_schema.py:1-16`, `bq-schema-guard.sh`). A column
added in one place and forgotten in the other is the failure the generation exists to
prevent — *"a local test that passes against a shape the cloud does not have"*.

Listed as a surface because it is the one people assume is the risk. It is already closed.

---

## Recommendation on F3E-01b

**Build it, but not as a row diff — as a rejection probe.**

The task as chartered is *"run the fixture corpus through both paths and diff the results"*.
Against this inventory that would report nothing useful. S6 and S7 make the *rows*
identical by construction, and S1 and S2 make the *tables and streams* different in ways a
row diff cannot see: the divergence is in what each side **refuses**, not in what it
stores. A row diff would come back clean and read as reassurance.

The valuable instrument is the inverse: take statements and queries production rejects and
assert the local stack rejects them too, enumerating where it does not. S1 gives it a first
case that is known to fail — a query with no partition predicate.

**S4 is the one to build first regardless of shape.** It is unknown, it is cheap to
measure, and it sits directly under SC-1 row 1.3's losslessness claim.

## Lane determination for F3E-01b

**Lane A, if and only if the scope is fixed to dry-run validation and read-only queries.
Lane C the moment it needs to create or write a cloud table.**

The strongest permission the execution requires, stated before work begins rather than
discovered during it — which is what `#109` did wrong:

| Probe | Cloud operation | Lane |
|---|---|---|
| Does production reject this DDL / query? | `bq query --dry_run` | **A** — precedent set in W2.17: *"A dry run creates nothing, so this cost no mutation"* |
| Does production reject an unfiltered read of `spans`? | dry-run against the existing table | **A** |
| Does production round-trip this JSON identically? | requires writing a row | **C** |
| Is `require_partition_filter` enforced on a table built like the local one? | requires creating a table | **C** |

**So the boundary runs through the middle of the task.** S1 and S3 are answerable from
Lane A by dry run. S4 and S5 are not — establishing a round-trip needs a row written and
read back, and no dry run produces one.

**Recommendation: split F3E-01b at that line rather than assigning it one lane.** A single
task spanning both would begin in Lane A, reach S4, and stop — which is the `#109` failure
repeating, and §8 of the directive says to stop at the discovery rather than reclassify
afterwards. Splitting it now is that stop, taken early.

---

## What this inventory does not establish

It enumerates what *can* diverge. It measures nothing new: S1, S2, S6 and S7 are settled by
reading, S3 was measured by someone else in W2.17, and S4 and S5 are open. **No claim here
is evidence that the pipeline is or is not correct** — that is F3E-01b's output, and it
does not exist yet.
