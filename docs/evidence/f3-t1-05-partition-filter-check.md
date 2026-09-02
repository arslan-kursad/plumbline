# T1-05 — the partition filter, constrained in the repository

**Measured:** 2026-09-02 · **Lane:** A · **Branch:** `feat/f3-t1-05-partition-filter-check`
**Task:** [`F3-prerequisite-directive.md`](../specs/F3-prerequisite-directive.md) T1-05
**Charter:** [`f3e-01b-rejection-probe.md`](f3e-01b-rejection-probe.md):58

---

## What it closes, and what it does not

The recorded gap:

> a query written outside the e2e path — a view, a dashboard, an eval-engine read — meets
> no local objection. That is the gap, and it is a gap in coverage rather than in
> behaviour.

`require_partition_filter` is enforced by BigQuery in the cloud and by nothing locally,
because the stand-in cannot create a partitioned table at all — T1-01, closed as
unsatisfiable. **T1-05 constrains the repository where the engine cannot be constrained.**

It does not restore emulator fidelity and does not claim to. The unreachable half stays
named in T1-01. This is the reachable half: a query that *forgets* the predicate in a file
is caught by review instead of by a production refusal.

**It is also not [#175](https://github.com/arslan-kursad/plumbline/issues/175).** That is
about the table *definition* — nothing asserts the DDL declares partitioning, or that
Terraform agrees with it. This is about the *queries*. The two are complementary and
neither covers the other.

## The tree as it stands

```
partition filter: 11 query site(s) against the plumbline dataset
    2  declared-absent
    6  filtered
    1  interpolated-predicate
    2  view-definition

every query site constrains start_time, is a view definition, or declares its absence
```

## Four things it must not do

A check that reports any of these would be worse than nothing — it would be asking for
correct code to be made wrong. Each is a case in the self-test corpus.

**1. Flag a view definition.** [`002_spans_deduped.sql`](../../analytics/sql/002_spans_deduped.sql)
selects from the base table with no predicate, deliberately: the consumer's `start_time`
filter is pushed below the window (ADR-0007 D2). Requiring one there means requiring the
views to be wrong. Two sites classify this way.

**2. Flag a query whose predicate arrives by interpolation.**
[`cloud.py`](../../scripts/e2e/cloud.py)'s `scoped_query` builds `WHERE {window.predicate()}`,
and `predicate()` is where `start_time` lives. That path is the most rigorously filtered in
the repository — eight tests in `cloud_test.py` assert it — so reporting it as unfiltered
would be exactly backwards. It is classified `interpolated-predicate`: **unverifiable here**,
which is what it is, and preferred over an assumed answer.

**3. Flag a query that is deliberately unfiltered.**
[`rejection-probe.sh`](../../scripts/probe/rejection-probe.sh) issues two queries with no
predicate on purpose — *their refusal is the measurement*. Adding a filter would delete the
case. They carry a marker:

```
# partition-filter: intentionally-absent -- the missing predicate IS the measurement.
# This query exists to be refused; adding a filter would delete the case.
```

**Declared, not excluded.** The reason travels with the query, and silencing a real finding
costs a visible line in review. An exclusion list inside the checker would have hidden both.
This follows the standing rule that a scanner's findings are not answered with scope.

**4. Miss a query because the table name is interpolated.**
[`query-rows.py`](../../scripts/e2e/query-rows.py) selects from `{PROJECT}.plumbline.{args.view}`.
Module-level string constants are resolved from the AST, and a reference landing in the
`plumbline` dataset is a site even when the view name does not survive — which is how the
red run below found it.

## Discrimination

### The self-test — durable, and it blocks

`scripts/ci/partition-filter-check.sh --self-test` runs the checker over a seven-site
fixture corpus and asserts the full classification, not merely that something was found:

```
  ok    1 × queries.py:20  UNFILTERED
  ok    1 × report.sql:2  UNFILTERED
  ok    1 × 1  view-definition
  ok    1 × 1  interpolated-predicate
  ok    1 × 1  declared-absent
  ok    1 × 2  filtered
  ok    1 × 7 query site(s)
partition-filter self-test: ok
```

Two seeded defects in two languages must be found; the four look-alike cases must stay
quiet; and the site count is asserted, because a scanner that stops finding sites reports
success forever. The corpus carries an eighth query against a different table that must
**not** be counted.

The self-test is not non-blocking. A checker that cannot fail on a known-bad corpus is
decoration.

### The red run against the real tree

The partition filter was removed from [`query-rows.py`](../../scripts/e2e/query-rows.py)
and the checker run against the working tree:

```
  scripts/e2e/query-rows.py:96  UNFILTERED
      SELECT * FROM `plumbline-local.plumbline.{?}` ORDER BY trace_id, span_id

1 query site(s) reach the plumbline dataset without constraining start_time
```

Exit 1. The file was restored from the index and the tree re-verified green. Note the
rendered `{?}` — this is case 4 working: the view name did not survive interpolation and
the site was still found.

### It does not match itself

Pointed at its own source and at its own wrapper, the checker reports **0 sites** in each
and the empty-corpus guard fires. The marker string and the table names appear in both
files, and neither becomes a finding — the self-matching trap the repository's scanner
convention exists for.

## Non-blocking

Per standing requirement R-D the scan ships **non-blocking**, emitting its findings as a CI
artifact. Flipping it to blocking changes what CI asserts and is a separate, Class 3
decision. The self-test blocks; the scan does not.

## Residual uncertainty, recorded rather than resolved

A static check over query text is weaker than an engine constraint in three ways, all of
them known at the time of writing:

- **A query assembled at runtime defeats it.** The `interpolated-predicate` class is
  exactly that boundary, honestly labelled rather than silently passed.
- **The eval engine does not exist yet to be scanned.** It is named in the charter as one
  of the consumers that would meet no objection, and it will be covered when it is written,
  not before.
- **A marker can be used to silence a real defect.** That is a review question, which is
  the trade the marker is chosen for: it is visible, it carries a reason, and it is in the
  file rather than in a list somewhere else.

What it does close is the case that has actually occurred: a filter forgotten in a file.
