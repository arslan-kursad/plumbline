# BigQuery — the analytical store (architecture §4.1, F2 spec §6 Wave 1).
#
# Three objects: the dataset, the `spans` table, and the two canonical views every
# consumer reads instead of the table. `eval_results` is F3's and is deliberately
# absent — its schema is an open question owned by the eval-engine spec, and a
# table created here to be redefined there is worse than no table.

resource "google_bigquery_dataset" "plumbline" {
  project    = var.project_id
  dataset_id = "plumbline"
  location   = var.region

  description = "Normalized OTLP spans and the views consumers read (architecture §4.1)."

  # Left at their defaults on purpose, and the defaults are the free-tier ones:
  # no default table expiration (data is kept, and 10 GB of storage is free), and
  # `max_time_travel_hours` unset, which is 168 — time travel storage is billed
  # only past the free allowance this project will not approach.

  # The dataset holds the only copy of ingested spans. Destroying it because a
  # resource address moved is not a recoverable mistake, so Terraform refuses
  # rather than cascading.
  delete_contents_on_destroy = false

  depends_on = [google_project_service.required]
}

locals {
  sql_dir = "${path.module}/../../analytics/sql"

  # D4 — one definition of the view logic, shared by the local stand-in and the
  # cloud. The files under analytics/sql/ are executable DDL so compose can apply
  # them unchanged; a BigQuery view resource takes the query body alone. Rather
  # than keep a second copy of the dedup rule in HCL, the prologue is stripped
  # here: everything from the first `AS` after the view name, minus the trailing
  # semicolon.
  #
  # A drifted copy of the dedup rule between local and cloud is the class of
  # divergence golden tests exist to catch; here it is prevented structurally,
  # because there is only one place to edit.
  view_source = {
    spans_deduped = "002_spans_deduped.sql"
    spans_real    = "003_spans_real.sql"
  }

  view_query = {
    for name, source in local.view_source :
    name => trimsuffix(
      trimspace(
        regex("(?s)CREATE\\s+OR\\s+REPLACE\\s+VIEW.*?\\sAS\\s(.*)", file("${local.sql_dir}/${source}"))[0]
      ),
      ";"
    )
  }

  # The DDL addresses tables as `plumbline.spans` — dataset-qualified, which is
  # what the local stand-in understands. A stored view resolves an unqualified
  # project against the view's own, and relying on that is a needless bet, so the
  # reference is expanded to three parts for the cloud copy.
  view_query_qualified = {
    for name, query in local.view_query :
    name => replace(query, "`plumbline.", "`${var.project_id}.plumbline.")
  }
}

resource "google_bigquery_table" "spans" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.plumbline.dataset_id
  table_id   = "spans"

  description = "Normalized OTLP spans. Consumers read spans_deduped or spans_real, never this table."

  # Generated from analytics/sql/001_spans_table.sql, which is the authored
  # definition; scripts/ci/bq-schema-guard.sh fails CI if the two disagree.
  schema = file("${path.module}/generated/spans-schema.json")

  time_partitioning {
    type  = "DAY"
    field = "start_time"
  }

  clustering = ["trace_id", "span_id"]

  # The cost invariant, at the one enforcement point that cannot be forgotten by a
  # query author: an unfiltered scan of this table is refused by BigQuery itself
  # rather than by a reviewer noticing (architecture §7). Set at the top level —
  # the identically named field inside time_partitioning is the deprecated spelling.
  require_partition_filter = true

  # Default (true), stated because it is load-bearing: this table holds the only
  # copy of ingested spans.
  deletion_protection = true

  lifecycle {
    precondition {
      condition     = length(jsondecode(file("${path.module}/generated/spans-schema.json"))) > 0
      error_message = "generated/spans-schema.json is empty; regenerate it from analytics/sql/001_spans_table.sql"
    }
  }
}

# The canonical views (§4.1, ADR-0002). Every consumer — Looker Studio, the eval
# engine, the SPA export — reads these; nothing reads `spans` directly, because
# at-least-once delivery means the base table contains duplicates by design.
resource "google_bigquery_table" "spans_deduped" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.plumbline.dataset_id
  table_id   = "spans_deduped"

  description = "One row per (trace_id, span_id), latest write wins. Defined by analytics/sql/002_spans_deduped.sql."

  view {
    query          = local.view_query_qualified["spans_deduped"]
    use_legacy_sql = false
  }

  # A view holds no data; recreating one costs nothing and blocking its
  # replacement would make the definition harder to change than the rule it
  # encodes.
  deletion_protection = false

  lifecycle {
    precondition {
      condition     = startswith(upper(local.view_query_qualified["spans_deduped"]), "SELECT")
      error_message = "the extracted spans_deduped query does not start with SELECT; the DDL prologue strip in bigquery.tf matched the wrong thing"
    }
  }

  depends_on = [google_bigquery_table.spans]
}

resource "google_bigquery_table" "spans_real" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.plumbline.dataset_id
  table_id   = "spans_real"

  description = "Deduplicated spans excluding synthetic traffic. Defined by analytics/sql/003_spans_real.sql."

  view {
    query          = local.view_query_qualified["spans_real"]
    use_legacy_sql = false
  }

  deletion_protection = false

  lifecycle {
    precondition {
      condition     = startswith(upper(local.view_query_qualified["spans_real"]), "SELECT")
      error_message = "the extracted spans_real query does not start with SELECT; the DDL prologue strip in bigquery.tf matched the wrong thing"
    }
  }

  depends_on = [google_bigquery_table.spans_deduped]
}
