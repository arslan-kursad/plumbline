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

# The F2 deploy identity. F0 described it in a comment and deliberately did not
# create it, so that F0's CI identity was *demonstrably* unable to mutate anything
# (F0 spec §2, §W6.1). This is that identity, built to the shape F0 specified.
resource "google_service_account" "ci_deploy" {
  project      = var.project_id
  account_id   = "ci-deploy"
  display_name = "CI (deploy)"
  description  = "GitHub Actions identity for gated applies. Reachable only from main, only behind the gcp-production environment gate."

  depends_on = [google_project_service.required]
}

# The principalSet is narrower than the read-only identity's by one attribute: the
# ref. A pull request from this repository can obtain the read-only identity and
# plan; it cannot obtain this one at all, because its assertion carries a ref that
# is not refs/heads/main.
#
# The restriction lives in the principalSet rather than in an IAM condition on the
# binding. An IAM condition evaluates request attributes and cannot see the OIDC
# assertion, so `assertion.ref == '...'` written there would be a condition that
# reads a variable it has no access to — a control that looks present and grants
# nothing, or refuses everything. `attribute.ref` is already mapped on the provider
# (above), and a principalSet keyed on a mapped attribute is the documented
# mechanism.
#
# One attribute per principalSet, so this line carries the ref and the provider's
# attribute_condition carries the repository. Together they are "this repository,
# on main". The two are enforced by Google and fail independently of the
# environment gate, which is enforced by GitHub — a mistake in the workflow file
# cannot reach this identity from a branch.
resource "google_service_account_iam_member" "ci_deploy_wif" {
  service_account_id = google_service_account.ci_deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.ref/refs/heads/main"
}

# --- What this identity may do, and the part that is not comfortable --------
#
# Growing its own grants per wave (F2 D6) requires project IAM administration,
# which means this identity can grant itself any project-level role. Stating the
# consequence rather than implying otherwise: **at project scope this identity is
# administrator-equivalent, and the control is not the role list.**
#
# The controls that are real:
#
#   - it is unreachable except from main (the condition above, enforced by Google);
#   - every apply pauses on a required reviewer (the gcp-production environment,
#     enforced by GitHub);
#   - every plan is checked by scripts/ci/terraform-plan-guard.sh against the
#     architecture §7.1 allowlist, so a resource type nobody argued for is refused
#     even with the permission to create it;
#   - no key exists to steal (§6.1).
#
# ADR-0004 Amendment 2 had to withdraw a claim that an identity "could not" do
# something. This comment is written so there is nothing to withdraw later.
#
# --- And the part that is a real boundary -----------------------------------
#
# **Nothing here is granted on the billing account.** wif.tf named the cleaner
# shape in F0 — billing-scoped resources kept away from the CI identity — and F2
# is where that was decided (decision log W0.2). The deploy identity gets
# billing.viewer and nothing else, so `terraform plan` can refresh the budget and
# no CI run can ever change it. Billing-account writes stay with a human, which is
# what Wave 0 already demonstrated.
#
# A plan that needs a billing-account write therefore fails in CI with a
# permission error. That is the intended behaviour: it is visible, it names the
# resource, and it routes the change to the only path allowed to make it.

resource "google_project_iam_member" "ci_deploy" {
  for_each = toset([
    # Enabling the APIs each wave needs (google_project_service).
    "roles/serviceusage.serviceUsageAdmin",
    # The provider sends X-Goog-User-Project on every request (versions.tf).
    "roles/serviceusage.serviceUsageConsumer",
    # Reading state during a plan, across every resource in it.
    "roles/viewer",
    # Reading IAM policies that basic Viewer does not reach — the same gap
    # ci-readonly hit on storage buckets.
    "roles/iam.securityReviewer",
    # Wave 1: BigQuery. dataOwner rather than dataEditor, verified against the
    # role definitions rather than assumed: dataEditor can create a dataset and
    # cannot update one, so the second apply that changed a description would fail
    # on a permission the first apply did not need.
    "roles/bigquery.dataOwner",
    # Wave 1: Pub/Sub topics and the dead-letter subscription.
    "roles/pubsub.editor",
    # Wave 1: the DLQ depth alert and its notification channel.
    "roles/monitoring.editor",
    # Wave 1: Firestore in native mode.
    "roles/datastore.owner",
    # Wave 1: the image repository and its cleanup policy.
    "roles/artifactregistry.admin",
    # Wave 2 creates a service account per component (§6.1), and D6's per-wave
    # growth is what these two lines make possible — at the price named above.
    "roles/iam.serviceAccountAdmin",
    "roles/resourcemanager.projectIamAdmin",
    # Wave 2: the two Cloud Run services and their invoker policies. actAs on the
    # runtime identities is *not* here — it is granted per service account in
    # cloudrun.tf, so this identity cannot impersonate the kill-switch's.
    "roles/run.admin",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.ci_deploy.email}"
}

# Read-only on the billing account, for the same reason the read-only identity has
# it: `terraform plan` refreshes the budget, and a plan that cannot see it is a
# plan blind to drift. Write is deliberately absent — see above.
resource "google_billing_account_iam_member" "ci_deploy_billing_viewer" {
  billing_account_id = var.billing_account_id
  role               = "roles/billing.viewer"
  member             = "serviceAccount:${google_service_account.ci_deploy.email}"
}

# State access scoped to the state bucket, not project-wide: this identity must
# not reach the function-source bucket. objectAdmin because an apply writes state
# and a lock.
resource "google_storage_bucket_iam_member" "ci_deploy_state" {
  bucket = local.state_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ci_deploy.email}"
}
