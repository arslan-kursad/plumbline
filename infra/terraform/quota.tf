# Project-level BigQuery custom cost control (architecture §7, ADR-0004 §2).
#
# Prevent-class: the project cannot process more query bytes per day than this,
# whatever a query asks for. The default for QueryUsagePerDay is 200 TiB/day —
# four orders of magnitude above anything this project should ever run — so the
# override is the control, not a formality.
#
# Unit is MiB (BigQuery custom quota documentation). The chosen value and its
# free-tier arithmetic are recorded in docs/runbooks/kill-switch.md; the number
# lives in a variable so runbook and configuration cannot drift apart silently.
resource "google_cloud_quotas_quota_preference" "bigquery_query_usage_per_day" {
  parent   = "projects/${data.google_project.this.number}"
  service  = "bigquery.googleapis.com"
  quota_id = "QueryUsagePerDay"

  # No dimensions block: QueryUsagePerDay is project-scoped and carries no
  # region or per-user dimension.

  quota_config {
    preferred_value = var.bigquery_daily_query_quota_mib
  }

  # Lowering 200 TiB/day to tens of GiB is a large decrease and the Cloud Quotas
  # API refuses it unless the safety check is acknowledged explicitly. The size
  # of the decrease is the point of the control.
  ignore_safety_checks = "QUOTA_DECREASE_PERCENTAGE_TOO_HIGH"

  depends_on = [google_project_service.required]
}
