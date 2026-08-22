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

output "workload_identity_provider" {
  description = "Value for the GCP_WORKLOAD_IDENTITY_PROVIDER repository variable used by .github/workflows/ci.yml."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "ci_service_account" {
  description = "Value for the GCP_CI_SERVICE_ACCOUNT repository variable."
  value       = google_service_account.ci_readonly.email
}

output "project_id" {
  description = "Value for the GCP_PROJECT_ID repository variable."
  value       = var.project_id
}

output "state_bucket" {
  description = "Value for the GCP_STATE_BUCKET repository variable; the bucket ./bootstrap created."
  value       = local.state_bucket
}

output "collector_url" {
  description = "Public OTLP/HTTP endpoint agents send to. OTLP/gRPC is not reachable in the cloud (decision log W2.4)."
  value       = google_cloud_run_v2_service.collector.uri
}

output "worker_url" {
  description = "Ingestion worker endpoint. Internal ingress: reachable by the Wave 3 push subscription, not from the internet."
  value       = google_cloud_run_v2_service.worker.uri
}

output "pubsub_push_service_account" {
  description = "Identity the Wave 3 push subscription mints OIDC tokens as, and the only caller the worker accepts."
  value       = google_service_account.pubsub_push.email
}

output "deployed_image_tag" {
  description = "Commit SHA of the images both services run — the answer to \"which code is in production\"."
  value       = var.image_tag
}
