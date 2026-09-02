# T1-02 — Write-path tests classified against partition behaviour

**Measured:** 2026-09-02 · **Lane:** A · **Repo:** `main` @ `3ed5c76`
**Task:** [`F3-prerequisite-directive.md`](../specs/F3-prerequisite-directive.md) T1-02
**Charter:** [`f3e-01a-emulator-divergence.md`](f3e-01a-emulator-divergence.md) S1 — what did
write-path tests running against an unpartitioned table claim about partition behaviour?

**This is a classification, not a repair.** No test is changed here. Per the task, repairing
before classifying destroys the record of what was uncovered.

---

## The measurement that frames the table

The classification is not argued from reading names. It is derived from one experiment:
**delete the partitioning from the authored table definition and run everything.**

Removed from [`001_spans_table.sql`](../../analytics/sql/001_spans_table.sql): the
`PARTITION BY DATE(start_time)` clause (`:57`), the `CLUSTER BY trace_id, span_id` clause
(`:58`), and `require_partition_filter = TRUE` from the `OPTIONS` block (`:60`).

| Suite | Result against the stripped DDL |
|---|---|
| `Plumbline.Worker.Tests` | **38 passed**, 0 failed |
| `Plumbline.Normalization.Tests` | **76 passed**, 0 failed |
| `scripts/e2e/seed_test.py` | **11 passed** (`OK`) |
| `scripts/ci/bq-schema-guard.sh` | **match**, exit 0 |
| `scripts/ci/invariant-gates.sh` | **nine gates, all pass** |

**125 tests, nine gates and the schema guard are green against a `spans` definition that has
lost its cost invariant.** The DDL was restored from the index immediately afterwards and the
tree verified clean; the file in this repository is unchanged.

Under the project's standing invariant — every assertion must be able to fail — the corpus
contains **no assertion that can fail on the removal of `require_partition_filter`**.

## The distinction the whole classification turns on

`PARTITION BY` occurs in this repository with **two unrelated meanings**, and only one of
them is the cost invariant:

| Occurrence | Meaning |
|---|---|
| [`001_spans_table.sql`](../../analytics/sql/001_spans_table.sql)`:57` — `PARTITION BY DATE(start_time)` | **Table partitioning.** The cost invariant (`architecture.md` §4.1, §7) |
| [`002_spans_deduped.sql`](../../analytics/sql/002_spans_deduped.sql)`:37` — `PARTITION BY trace_id, span_id, start_time` | **Window-function partitioning**, inside `ROW_NUMBER() OVER (…)`. Dedup, not cost |

Every test in this repository that names the keyword is about the **second**. A keyword search
for partition coverage returns tests that have nothing to do with the constraint.

## What is asserted, and what is not

Sorting the write path by *which* partition property is asserted separates a covered habit
from an uncovered constraint:

| Property | Asserted by | State |
|---|---|---|
| The **query carries** a partition predicate | `cloud_test.py` `Window` (8) and `WallingProof` (4) | **covered** |
| A row's `start_time` is not shifted, so it lands in the partition its data implies | `cloud_test.py:154` | **covered** |
| The dedup view's window clause names its columns | `cloud_test.py:203`, `seed_test.py:84` | **covered** |
| The **table requires** a partition predicate | — | **nothing** |
| The DDL declares partitioning at all | — | **nothing** |
| Terraform's partitioning agrees with the DDL's | — | **nothing** |

**The habit is asserted; the constraint is not.** That is
[`f3e-01b-rejection-probe.md`](f3e-01b-rejection-probe.md)'s finding — *"the habit is enforced
by convention locally and by the engine in the cloud"* — now measured against the test corpus
rather than derived from the seeder.

---

## Classification

Categories are the task's: **PD** partition-dependent, **PI** partition-independent, **SPI**
silently partition-independent — written as though it covered partitioning, and does not.

### `scripts/e2e/cloud_test.py` — the cloud read-back harness

| Line | Test | Class |
|---|---|---|
| 49 | `test_a_query_cannot_be_built_without_a_window` | **PD** |
| 53 | `test_a_backwards_window_is_refused` | **PD** |
| 57 | `test_a_window_wide_enough_to_be_a_full_scan_is_refused` | **PD** — bounds the scan; its comment is explicit that `require_partition_filter` is satisfied by a year-wide predicate and the budget is the separate control |
| 62 | `test_the_query_carries_both_the_partition_and_the_run_scope` | **PD** — asserts the literal `DATE(start_time) BETWEEN …` |
| 68 | `test_the_window_comes_from_the_run_not_from_today` | **PD** |
| 73 | `test_the_corpus_window_covers_the_corpus_and_not_today` | **PD** |
| 99 | `test_an_empty_corpus_is_refused_rather_than_falling_back_to_the_clock` | **PD** |
| 104 | `test_no_query_path_derives_its_window_from_the_clock` | **PD** |
| 154 | `test_start_time_is_left_alone` | **PD** — names the consequence: shifting it would move rows between partitions |
| 191 | `test_it_passes_against_a_view_matching_the_repository` | PI |
| 195 | `test_it_fails_against_a_deliberately_mismatched_view` | PI |
| 203 | `test_the_repository_clause_is_read_past_the_comments` | PI — asserts the **window** clause's columns |
| 301 | `test_both_sides_exclude_the_same_columns` | PI |
| 304 | `test_ingest_time_is_excluded_because_it_is_a_clock` | PI |
| 307 | `test_api_key_id_is_not_excluded` | PI |
| 313 | `test_every_excluded_column_is_a_real_column` | PI |
| 323 | `test_timestamps_are_formatted_in_sql` | PI |
| 329 | `test_json_columns_are_stringified_then_parsed_back` | PI |
| 333 | `test_scalars_come_back_typed` | PI |
| 340 | `test_the_schema_comes_from_the_table_definition` | **SPI** — see below |
| 356–386 | `GoldenDiff`, 7 tests | PI — row comparison |
| 533 | `test_both_assertions_are_scoped_and_filtered` | **PD** — asserts `DATE(start_time) BETWEEN` in both walling queries |
| 543 | `test_the_exclusion_claim_reads_spans_real` | **PD** — same predicate, different view |
| 554 | `test_the_two_claims_use_different_views` | PI |
| 560 | `test_the_proof_reads_the_view_not_the_base_table` | PI |
| 26–42 | `Arming`, 5 tests | **excluded** — harness arming, not the write path |
| 229–245 | `RunIdPath`, 4 tests | **excluded** — attribute nesting |
| 257–282 | `StageResult`, 6 tests | **excluded** — run bookkeeping |
| 403–426 | `ResultIsWritten`, 4 tests | **excluded** — evidence emission |
| 441–487 | `DrillGates` and `DrillPayload`, 8 tests | **excluded** — dead-letter drill |

### `worker/Plumbline.Worker.Tests/SpanRowProtoTests.cs` — the row as sent

| Line | Test | Class |
|---|---|---|
| 22 | `TheProtoCarriesExactlyTheColumnsTheTableDeclares` | **SPI** — see below |
| 46 | `EveryColumnTheTableAllowsToBeNullIsOptionalInTheProto` | PI |
| 58 | `NullColumnsStayUnsetRatherThanBecomingZero` | PI |
| 85 | `TimestampsBecomeMicrosecondsSinceTheEpoch` | PI — but see the note on `start_time` below |
| 122 | `TheDescriptorSentToBigQueryCarriesNoProto3OptionalMarkers` | PI |
| 135 | `EveryColumnSurvivesTheConversionAsAnOptionalField` | PI |

### `worker/Plumbline.Worker.Tests/IngestionEndpointTests.cs` — receiving and writing

| Line | Test | Class |
|---|---|---|
| 34 | `AWellFormedMessageIsAcknowledgedAndItsRowsAreWritten` | PI |
| 48 | `APoisonMessageIsRefusedSoPubSubCanDeadLetterIt` | PI |
| 59 | `APoisonMessageDoesNotAffectTheMessagesAroundIt` | PI |
| 76 | `AMalformedEnvelopeIsRefusedRatherThanIgnored` | PI |
| 92 | `TheEnvelopeAttributesReachTheRow` | PI |
| 108 | `DetectionOverridesAWrongHintRatherThanTrustingIt` | PI |
| 120 | `AnUncompressedPayloadIsReadWhenTheAttributeSaysSo` | PI |
| 139 | `TheHealthEndpointNamesTheMechanismSoAcceptAllCannotShipQuietly` | PI |

### `worker/Plumbline.Worker.Tests/WorkerOptionsTests.cs` — sink configuration

| Line | Test | Class |
|---|---|---|
| 98 | `TheBigQuerySinkNamesItsDestinationAndItsStream` | PI — the stream is S2's surface, not S1's |
| 111 | `ASinkWithNoDestinationIsAStartupFailure` | PI |
| 33–90 | six push-auth tests | **excluded** — authentication, not the write path |

### `scripts/e2e/seed_test.py` — table and view creation

| Line | Test | Class |
|---|---|---|
| 69 | `test_the_view_file_carries_the_trigger_in_a_comment` | PI — the **window** clause |
| 84 | `test_only_the_window_clause_survives_stripping` | PI — honestly named for the window clause; see the keyword note |
| 90 | `test_every_view_file_still_declares_its_view` | PI |
| 102 | `test_the_table_schema_still_parses_after_stripping` | PI — asserts the column parse is unchanged; the parser cannot see the clauses |
| 32–61 | seven stripper unit tests | PI |

### Not a test, but load-bearing

| Artefact | Class |
|---|---|
| [`bq_schema.py`](../../scripts/ci/bq_schema.py) / `bq-schema-guard.sh` | **SPI** — see below |

---

## The three SPI findings

**Filed as `#175`**, per the task's acceptance that any test in this category is named and an
issue opened.

**1. `bq_schema.py` — the DDL↔Terraform guard covers columns only.**
Its own docstring states the purpose: *"a second hand-written copy of thirty columns is the
silent divergence D4 exists to prevent — a column added in one place and forgotten in the
other."* Partitioning **is** in both places — `001_spans_table.sql:57,60` and
[`bigquery.tf`](../../infra/terraform/bigquery.tf)`:77,88` — and is guarded in neither. The
guard's parsing is *"deliberately narrow… the column list of one CREATE TABLE"*, which is
correct for what it does and is narrower than what the file it guards is understood to
assert. This is the largest of the three: it is the only mechanism that compares the two
definitions of the same table.

**2. `cloud_test.py:340` — `test_the_schema_comes_from_the_table_definition`.**
The strongest-sounding name in the corpus. It asserts that the projection contains
`synthetic`, contains `attributes`, and has more than twenty columns. The table definition
declares partitioning, clustering and a filter requirement; the test reads none of them and
passed unchanged with all three deleted.

**3. `SpanRowProtoTests.cs:22` — `TheProtoCarriesExactlyTheColumnsTheTableDeclares`.**
Milder, and included because it is the .NET side's only reader of the DDL. The name scopes
itself to columns, which is honest; the risk is that it is the test a reader reaches for when
asking whether the proto and the table agree, and the answer it gives is narrower than the
question.

### A fourth thing, which is not a defect

`seed_test.py:69` and `:84` are **honestly named** — `test_only_the_window_clause_survives_stripping`
says *window clause*. They are recorded here only because a keyword search for partition
coverage surfaces them, and because the constant they use is assembled as
`TRIGGER = "PARTITION" + " BY"` specifically so the file does not match itself. They cover the
comment stripper, they say so, and they are the right tests for what they are for.

## What this does not claim

It does not claim any test is wrong. Every test above passes for the reason it was written.
The finding is about the **shape of the corpus**: the property that the local table cannot
carry (T1-01, closed as unsatisfiable) is also the property that no test asserts about the
definition that *can* carry it — the authored DDL and the Terraform resource, both of which
are partitioned today and neither of which is guarded.

`TimestampNarrowingTests` (4 tests) is excluded as normalization rather than write-path, and
noted here because `start_time` is the partition key: truncation defects would move rows
between partitions. The tests pin truncation, and are partition-relevant by consequence
rather than by assertion.
