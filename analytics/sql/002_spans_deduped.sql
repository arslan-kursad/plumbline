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
-- `require_partition_filter` on the base table applies through this view: a query against
-- it still has to constrain start_time.
CREATE OR REPLACE VIEW `plumbline.spans_deduped` AS
SELECT
  * EXCEPT (duplicate_rank)
FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY trace_id, span_id
      ORDER BY ingest_time DESC
    ) AS duplicate_rank
  FROM `plumbline.spans`
)
WHERE duplicate_rank = 1;
