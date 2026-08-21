data "google_project" "this" {
  project_id = var.project_id
}

# Services required by the F0 footprint only. Application APIs (BigQuery jobs,
# Firestore, Scheduler) are enabled by F2 alongside the resources that use them;
# bigquery.googleapis.com is here because the quota override in quota.tf targets
# it and cannot be applied to a disabled service.
#
# The list is sorted, and every entry earns its place by a resource in this
# module or by a runtime path this module creates. An API that no longer has a
# reason here is removed rather than kept "just in case": enabling one is free,
# but an unexplained entry is indistinguishable from a mistake.
resource "google_project_service" "required" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    # quota.tf speaks to the Cloud Quotas API; without this the override is not a
    # misconfiguration, it is an apply failure.
    "cloudquotas.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "eventarc.googleapis.com",
    "iam.googleapis.com",
    # iamcredentials and sts are the two halves of what Workload Identity
    # Federation does at run time: sts exchanges the GitHub OIDC assertion for a
    # federated token, iamcredentials mints the service account token that
    # identity impersonates with. Creating the pool needs neither; using it needs
    # both, and the failure would land in CI rather than in an apply.
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ])

  project = var.project_id
  service = each.key

  # Disabling an API on destroy can break unrelated resources in the project and
  # is not reversible within one apply; leave the API enabled.
  disable_on_destroy = false
}
