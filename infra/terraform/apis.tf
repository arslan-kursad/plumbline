data "google_project" "this" {
  project_id = var.project_id
}

# Services required by the F0 footprint only. Application APIs (BigQuery jobs,
# Firestore, Scheduler) are enabled by F2 alongside the resources that use them;
# bigquery.googleapis.com is here because the quota override in quota.tf targets
# it and cannot be applied to a disabled service.
resource "google_project_service" "required" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "eventarc.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
  ])

  project = var.project_id
  service = each.key

  # Disabling an API on destroy can break unrelated resources in the project and
  # is not reversible within one apply; leave the API enabled.
  disable_on_destroy = false
}
