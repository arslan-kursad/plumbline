output "billing_alerts_topic" {
  description = "Topic the budget publishes to; the live-fire test publishes here (docs/runbooks/kill-switch.md)."
  value       = google_pubsub_topic.billing_alerts.id
}

output "killswitch_function" {
  description = "Kill-switch function name."
  value       = google_cloudfunctions2_function.killswitch.name
}

output "killswitch_service_account" {
  description = "Identity that detaches billing."
  value       = google_service_account.killswitch.email
}

output "bigquery_daily_query_quota_mib" {
  description = "Applied BigQuery per-day query quota, MiB."
  value       = var.bigquery_daily_query_quota_mib
}
