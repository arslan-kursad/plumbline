output "state_bucket" {
  description = "Bucket name to pass to the root module as -backend-config=bucket=..."
  value       = google_storage_bucket.tfstate.name
}
