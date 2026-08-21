# Workload Identity Federation for GitHub Actions (F0 spec §W6.1,
# architecture §6.1).
#
# The repository is public, so the identity binding is explicit rather than
# resting on default GitHub behaviour: the provider itself refuses assertions
# from any other repository or owner, before any role is consulted.
#
# No exported service account key exists anywhere in this design. Gate C scans
# for one, but a scan is a backstop; the reason there is nothing to find is that
# nothing ever issues a key.

locals {
  # Matches the name bootstrap/ gives the bucket, so the common case needs no
  # variable at all.
  state_bucket = coalesce(var.state_bucket, "${var.project_id}-tfstate")
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  description               = "Identity pool for CI running in ${var.github_repository}."

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }

  # A pool or provider without an attribute condition is treated as a defect,
  # not a default: without this line every GitHub Actions workflow on the
  # internet can present a valid token to this provider.
  attribute_condition = "assertion.repository == '${var.github_repository}' && assertion.repository_owner == '${var.github_owner}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# F0 ships exactly one CI identity, and it cannot deploy anything.
resource "google_service_account" "ci_readonly" {
  project      = var.project_id
  account_id   = "ci-readonly"
  display_name = "CI (read-only)"
  description  = "GitHub Actions identity for build, validate and plan. No mutating permissions."

  depends_on = [google_project_service.required]
}

resource "google_service_account_iam_member" "ci_readonly_wif" {
  service_account_id = google_service_account.ci_readonly.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

# Read across the project, so `terraform plan` can refresh state. Mutating IAM
# is deliberately absent: a plan that cannot change anything is the whole point
# of the F0 CI identity.
resource "google_project_iam_member" "ci_readonly_viewer" {
  project = var.project_id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.ci_readonly.email}"
}

# `terraform plan` refreshes every resource in state, and two of them are not
# reachable through project-level Viewer.
#
# The budget is a billing-account resource, so project Owner does not reach it and
# neither does project Viewer. Billing Account Viewer is the narrowest role that
# can read a budget — budgets carry no IAM of their own — and it does mean the CI
# identity can read this billing account's costs. Read-only, and the alternative
# was worse: planning with `-refresh=false` would keep the identity narrower at the
# cost of making CI blind to drift, which is a bug class this project refuses to
# stop looking for.
#
# The cleaner long-term shape is to hold billing-account-scoped resources in their
# own state, so the CI identity never needs to read across that boundary at all.
# That is an F2 conversation, not an F0 change.
resource "google_billing_account_iam_member" "ci_readonly_billing" {
  billing_account_id = var.billing_account_id
  role               = "roles/billing.viewer"
  member             = "serviceAccount:${google_service_account.ci_readonly.email}"
}

# `plan` refreshes IAM-member resources by reading the policy they belong to, and
# basic Viewer carries `getIamPolicy` for the project, service accounts and Cloud
# Run — but not for storage buckets. Security Reviewer is the read-only role whose
# entire purpose is reading IAM policies; the storage roles that include
# `buckets.getIamPolicy` also include `setIamPolicy`, which this identity must not
# have (F0 spec §W6.1: no mutating IAM).
resource "google_project_iam_member" "ci_readonly_security_reviewer" {
  project = var.project_id
  role    = "roles/iam.securityReviewer"
  member  = "serviceAccount:${google_service_account.ci_readonly.email}"
}

# Required because the provider sends X-Goog-User-Project on every request
# (user_project_override in versions.tf). Without it CI authenticates, then fails
# on `caller does not have serviceusage.services.use`.
resource "google_project_iam_member" "ci_readonly_service_usage" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${google_service_account.ci_readonly.email}"
}

# Cloud Quotas is recent enough that the basic Viewer role cannot be relied on to
# carry its read permissions. Granting the service's own viewer role is explicit
# and costs nothing.
resource "google_project_iam_member" "ci_readonly_quota_viewer" {
  project = var.project_id
  role    = "roles/cloudquotas.viewer"
  member  = "serviceAccount:${google_service_account.ci_readonly.email}"
}

# State access is scoped to the state bucket rather than granted project-wide:
# the same identity must not be able to reach the function-source bucket.
# objectAdmin rather than objectViewer because Terraform writes a state lock
# even for a plan that changes nothing.
resource "google_storage_bucket_iam_member" "ci_readonly_state" {
  bucket = local.state_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ci_readonly.email}"
}

# The F2 deploy identity, documented here and deliberately not created (F0 spec
# §2, §W6.1): a separate `ci-deploy` service account whose principalSet requires
# the branch as well as the repository —
#
#   principalSet://iam.googleapis.com/${pool}/attribute.repository/${repo}
#   with an additional attribute condition on attribute.ref == 'refs/heads/main'
#
# so a pull request cannot obtain deploy credentials even from this repository.
# Writing the pattern now and creating it in F2 keeps F0's identity provably
# incapable of deploying.
