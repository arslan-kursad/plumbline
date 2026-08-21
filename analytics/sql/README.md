# Analytical SQL

The `spans` table definition and the two canonical views, as SQL.

**Terraform owns these objects in the cloud** (architecture §8; the `google_bigquery_table`
type enters the allowlist in F2). These files are not a second deployment path. They exist
because F1 runs the whole pipeline locally against a BigQuery stand-in that Terraform does
not manage, and because a view definition is easier to review, and to keep identical
across both, as SQL than as an HCL string.

| File | Object |
| --- | --- |
| `001_spans_table.sql` | `spans` — the base table, partitioned, clustered, partition filter required |
| `002_spans_deduped.sql` | `spans_deduped` — one row per `(trace_id, span_id)` |
| `003_spans_real.sql` | `spans_real` — `spans_deduped` minus synthetic traffic |

Applied in order; the numbering is the dependency order and nothing else.

## Consumers read views, never the base table

Looker Studio, the eval engine and the SPA export all read `spans_deduped` or
`spans_real` (architecture §4.1). The reason is in §3.3: delivery is at-least-once, so the
base table holds duplicates by design, and every consumer that queried it directly would
have to re-implement the dedup — correctly, and identically, forever.

## Every query needs a partition filter

`require_partition_filter = true` is a cost invariant (§7): it makes a full-table scan
impossible to write by accident, which is what keeps the BigQuery free tier from being
consumed by one careless `SELECT *`. It applies through the views, so a query against
`spans_real` still has to constrain `start_time`:

```sql
SELECT trace_id, name, gen_ai_request_model
FROM `plumbline.spans_real`
WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY);
```

Without the predicate the query is refused, and that refusal is the control working.
