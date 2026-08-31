-- spans_deduped — one row per (trace_id, span_id), keeping the latest write.
--
-- Delivery is at-least-once (§3.3, ADR-0002): duplicates land in the base table by
-- design, and this view is where they stop. Encapsulating the rule here rather than in
-- each consumer is the point — Looker Studio, the eval engine and the SPA export cannot
-- each be relied on to re-implement it identically.
--
-- ROW_NUMBER in a subquery rather than QUALIFY, which architecture §4.1 names. The
-- semantics are identical; QUALIFY is a BigQuery extension that the local stand-in does
-- not necessarily parse, and one definition that runs in both places is worth more than
-- the shorter spelling (decision log W5.4).
--
-- `require_partition_filter` on the base table applies through this view, and a query
-- against it still has to constrain start_time — but that alone was not enough, and the
-- earlier version of this comment stated it as if it were (#61).
--
-- `start_time` is one of the window's partitioning columns, and that is load-bearing
-- rather than cosmetic (ADR-0007 D2). A predicate may only be pushed below a window
-- function when it references the columns the window partitions on; with the
-- two-column window a consumer's `start_time` filter could not be pushed, the inner
-- scan of `spans` had no partition predicate, and the guardrail refused the query
-- outright. The views could not be queried at all.
--
-- The wording above is roundabout on purpose, and the reason is measured rather than
-- stylistic. The local stand-in scans the statement text for the two keywords that
-- open a partitioning clause, finds them in a comment, and then answers the whole
-- file with HTTP 200, a result set, and no view — silently, which is the shape this
-- project treats as worse than an error. Bisected one comment line at a time in CI
-- (decision log W2.16). So the clause is named in prose everywhere except the window
-- itself, where it has to be spelled. If someone tidies this back into the direct
-- phrasing, `make e2e` fails naming the missing object: the seeder asks the dataset
-- what it holds rather than trusting the status code.
--
-- Semantically this is the same dedup: two rows for one (trace_id, span_id) come from
-- redelivery of identical OTLP bytes and carry the same start_time, so they already
-- shared a partition. Where that premise breaks the shapes differ, and this one keeps
-- both rows rather than dropping one — visible rather than silent (ADR-0007 D6). The
-- premise has an enforcement point: the nanosecond-to-microsecond conversion is
-- truncation, pinned by a golden file.
CREATE OR REPLACE VIEW `plumbline.spans_deduped` AS
SELECT
  * EXCEPT (duplicate_rank)
FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY trace_id, span_id, start_time
      ORDER BY ingest_time DESC
    ) AS duplicate_rank
  FROM `plumbline.spans`
)
WHERE duplicate_rank = 1;
