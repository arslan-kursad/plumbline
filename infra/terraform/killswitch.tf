# Billing kill-switch (F0 spec W4, ADR-0004 §5).
#
#   budget (all cost updates) -> Pub/Sub topic -> Cloud Function (Gen2)
#                             -> projects.updateBillingInfo with an empty
#                                billing account = billing detached.
#
# The budget threshold is not the trigger. `all_updates_rule` publishes a
# notification on every cost update (~30 min cadence), and the function detaches
# whenever reported net cost reaches `detach_threshold` — a small epsilon rather
# than "greater than zero" (ADR-0004 Amendment 4, D2), because a reported figure
# can be non-zero while nothing has been billed. Threshold rules only add a
# labelled "exceeded" event to the same stream.
#
# A second budget lives at the bottom of this file and reports gross cost. It has
# no Pub/Sub binding and cannot reach this function: it emails, and that is all.

resource "google_pubsub_topic" "billing_alerts" {
  name    = "billing-alerts"
  project = var.project_id

  # message_retention_duration is deliberately unset: topic-level retention is a
  # paid feature and is forbidden on every topic (architecture §2.2, CLAUDE.md).

  depends_on = [google_project_service.required]
}

resource "google_service_account" "killswitch" {
  account_id   = "killswitch-fn"
  display_name = "Billing kill-switch function"
  description  = "Detaches the billing account from this project when any spend is reported."
  project      = var.project_id

  depends_on = [google_project_service.required]
}

# Detaching billing is authorized on both sides of the association, so both
# grants are required (ADR-0004 Amendment 2).
#
# Project side: resourcemanager.projects.deleteBillingAssignment, which Project
# Billing Manager carries on this project and nowhere else.
resource "google_project_iam_member" "killswitch_billing_manager" {
  project = var.project_id
  role    = "roles/billing.projectManager"
  member  = "serviceAccount:${google_service_account.killswitch.email}"
}

# Billing-account side: billing.resourceAssociations.delete, which exists in
# exactly one predefined role — Billing Account Administrator — and is grantable
# only on the billing account.
#
# This is more power than the design wanted. The first live-fire failed with a
# 403 exactly here, and the original claim that this identity "can detach and
# cannot re-attach" was false at the platform level: no narrower role can delete
# the association, and the role that can delete it can also create it. What keeps
# re-attachment human is the function's code and the operating procedure, not a
# permission boundary. Blast radius and the alternatives considered are in
# ADR-0004 Amendment 2 rather than left implicit behind a role name.
resource "google_billing_account_iam_member" "killswitch_billing_admin" {
  billing_account_id = var.billing_account_id
  role               = "roles/billing.admin"
  member             = "serviceAccount:${google_service_account.killswitch.email}"
}

# The permission the second live-fire found missing (ADR-0004 Amendment 3).
#
# The function's first call is Projects.GetBillingInfo, and reading a project's
# billing info needs `resourcemanager.projects.get` **on the project**. Project
# Billing Manager does not carry it — that role grants exactly two permissions,
# createBillingAssignment and deleteBillingAssignment — and Billing Account
# Administrator carries it against the *billing account*, which is a different
# resource. So the identity could detach billing and could not find out whether it
# needed to.
#
# A custom role with one permission rather than `roles/browser`, which would also
# hand over project IAM policy reads, folder and organization reads. This identity
# already holds administrator rights on the billing account (Amendment 2); it is
# the last one in the project that should collect incidental reads.
resource "google_project_iam_custom_role" "killswitch_billing_reader" {
  project     = var.project_id
  role_id     = "killswitchBillingReader"
  title       = "Kill-switch billing reader"
  description = "resourcemanager.projects.get, so the kill-switch can read the billing state it is about to change. Nothing else."

  permissions = ["resourcemanager.projects.get"]
}

resource "google_project_iam_member" "killswitch_billing_reader" {
  project = var.project_id
  role    = google_project_iam_custom_role.killswitch_billing_reader.id
  member  = "serviceAccount:${google_service_account.killswitch.email}"
}

resource "google_project_iam_member" "killswitch_event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.killswitch.email}"
}

# The live-fire evidence is the function's own log output (ADR-0004 §5), so log
# writing is part of the control, not incidental.
resource "google_project_iam_member" "killswitch_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.killswitch.email}"
}

# Pub/Sub mints the OIDC token Eventarc uses to invoke the function.
resource "google_project_iam_member" "pubsub_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"

  depends_on = [google_project_service.required]
}

# Build identity, owned rather than inherited.
#
# A Gen2 function is built by Cloud Build, which since mid-2024 defaults to the
# project's default compute service account. That account only exists once the
# Compute Engine API has been enabled, so on a project like this one — which will
# never run a VM and has no reason to enable that API — the default is a principal
# that does not exist. Granting roles to it fails the apply, and the error names a
# service account nobody in this configuration created.
#
# Naming our own build identity removes the dependency entirely, and matches how
# every other component here gets an identity: explicitly.
resource "google_service_account" "killswitch_build" {
  project      = var.project_id
  account_id   = "killswitch-build"
  display_name = "Kill-switch function build"
  description  = "Cloud Build identity for building the billing kill-switch container."

  depends_on = [google_project_service.required]
}

# The umbrella build role: push to Artifact Registry, write build logs, read the
# source. Granular equivalents exist, but this is the role Google's own
# custom-build-service-account procedure names, and a build identity that fails
# obscurely is worse than one scoped by a documented role.
resource "google_project_iam_member" "killswitch_build_builder" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${google_service_account.killswitch_build.email}"
}

# Source access scoped to the one bucket that holds it, rather than relying on
# whatever the umbrella role happens to include for storage.
resource "google_storage_bucket_iam_member" "killswitch_build_source" {
  bucket = google_storage_bucket.function_source.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.killswitch_build.email}"
}

resource "google_storage_bucket" "function_source" {
  name     = "${var.project_id}-function-source"
  location = var.region
  project  = var.project_id

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  # Source archives are small and superseded on every deploy; keep the bucket
  # from accumulating against the 5 GB free tier.
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.required]
}

data "archive_file" "killswitch_source" {
  type        = "zip"
  source_dir  = "${path.module}/../functions/billing-killswitch"
  output_path = "${path.module}/.terraform/tmp/billing-killswitch.zip"
  excludes    = ["README.md"]
}

resource "google_storage_bucket_object" "killswitch_source" {
  # The hash in the name is what makes a source change a new object, and a new
  # object is what makes the function redeploy.
  name   = "billing-killswitch-${data.archive_file.killswitch_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.killswitch_source.output_path
}

resource "google_cloudfunctions2_function" "killswitch" {
  name        = "billing-killswitch"
  location    = var.region
  project     = var.project_id
  description = "Detaches billing from this project on any reported spend (ADR-0004 §5)."

  build_config {
    runtime         = var.killswitch_runtime
    entry_point     = "HandleBudgetNotification"
    service_account = google_service_account.killswitch_build.id

    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.killswitch_source.name
      }
    }
  }

  service_config {
    # Cloud Run limits apply here as well: scale to zero, never above two.
    min_instance_count = 0
    max_instance_count = 1

    available_memory      = var.killswitch_memory
    timeout_seconds       = 60
    service_account_email = google_service_account.killswitch.email
    ingress_settings      = "ALLOW_INTERNAL_ONLY"

    environment_variables = {
      TARGET_PROJECT_ID = var.project_id

      # The epsilon (Amendment 4, D2). Passed rather than compiled in so the
      # value is reviewable in a plan diff; the function refuses to start without
      # it rather than falling back to a default nobody chose.
      DETACH_THRESHOLD = var.detach_threshold
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic          = google_pubsub_topic.billing_alerts.id
    service_account_email = google_service_account.killswitch.email

    # A transient failure of the one control that stops spending must be retried.
    # Permanent failures are acked by the function itself so this cannot become a
    # retry loop; see infra/functions/billing-killswitch/main.go.
    retry_policy = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_project_service.required,
    google_project_iam_member.killswitch_build_builder,
    google_storage_bucket_iam_member.killswitch_build_source,
  ]
}

# Invoker scoped to this one service rather than roles/run.invoker on the
# project: F2 adds three more Cloud Run services and the kill-switch identity has
# no business reaching them.
resource "google_cloud_run_service_iam_member" "killswitch_invoker" {
  project  = var.project_id
  location = google_cloudfunctions2_function.killswitch.location
  service  = google_cloudfunctions2_function.killswitch.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.killswitch.email}"
}

resource "google_billing_budget" "zero_spend" {
  billing_account = var.billing_account_id
  display_name    = "plumbline zero-spend"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]

    # Net of every credit (ADR-0004 Amendment 4, D1). Do not narrow this back to
    # an enumerated list.
    #
    # Amendment 1 subtracted one named credit type and nothing else, so that usage
    # beyond Always Free stayed visible. Live operation falsified its premise: this
    # account's usage is absorbed by a promotional credit, no matching credit line
    # appeared, and the filter therefore subtracted nothing. The budget reported
    # gross, and this chain detaches on any reported spend — so the kill-switch
    # detached billing 18 minutes after it was attached, on 0.04 TRY of its own
    # CPU seconds.
    #
    # Enumerating types re-creates that failure the next time a type appears that
    # nobody anticipated. Subtracting all of them is the one reading that cannot
    # be wrong about a category it has not met, and the guard against a credit
    # masking real spend moves to two places that do not depend on guessing: the
    # epsilon threshold below, and the gross-cost alert budget in this file.
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      # Currency deliberately unset: the Budget API rejects a create whose
      # currency does not match the billing account's, and this project's account
      # bills in a currency that is not the one this file was first written with.
      # Inheriting is both correct and portable. The amount is not the trigger, so
      # its currency does not affect when the kill-switch fires.
      currency_code = var.budget_currency_code
      units         = var.budget_amount
    }
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  all_updates_rule {
    pubsub_topic                   = google_pubsub_topic.billing_alerts.id
    schema_version                 = "1.0"
    disable_default_iam_recipients = false
  }

  depends_on = [google_project_service.required]
}

# The runaway signal while a promotional credit absorbs everything
# (ADR-0004 Amendment 4, D3).
#
# The kill-switch budget above now reports net of every credit, which is what
# stops it firing on credit-absorbed usage — and it means that during the
# promotional period net cost is zero by construction and the detach guard cannot
# fire at all (D4). That inertness is acknowledged rather than hidden, and this
# budget is what covers the window: it reports **gross**, so usage hidden behind
# the credit is still visible to a human.
#
# It is notification-only, and the absence of a Pub/Sub binding is the design.
# Two budgets publishing to `billing-alerts` would mean two independent things
# could detach billing, one of them on a figure that is non-zero during entirely
# free operation. The plan guard asserts that exactly one budget references that
# topic, so this stays true by mechanism rather than by memory.
resource "google_billing_budget" "gross_cost_alert" {
  billing_account = var.billing_account_id
  display_name    = "plumbline gross-cost alert"

  budget_filter {
    projects               = ["projects/${data.google_project.this.number}"]
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      # Unlike the kill-switch budget, this amount *is* the trigger: the
      # thresholds below are percentages of it, so the currency has to be stated
      # and has to match the billing account's or the API refuses the create.
      currency_code = var.billing_currency
      units         = var.gross_alert_threshold
    }
  }

  # Two rules rather than one. 50% is the signal that something changed while
  # there is still room to look at it; 100% is the one that says the month's
  # gross has reached a figure nobody planned for.
  threshold_rules {
    threshold_percent = 0.5
    spend_basis       = "CURRENT_SPEND"
  }

  threshold_rules {
    threshold_percent = 1.0
    spend_basis       = "CURRENT_SPEND"
  }

  # No `all_updates_rule` block at all, and that is what delivers the email.
  #
  # The directive asked for the block with `disable_default_iam_recipients =
  # false`. The provider refuses it: `all_updates_rule` requires either
  # `pubsub_topic` or `monitoring_notification_channels`, so the block cannot be
  # written without giving this budget one of the two programmatic paths D3
  # forbids it. Omitting the block leaves the API default — threshold
  # notifications emailed to the billing account's administrators — which is
  # exactly what D3 specifies, reached by absence rather than by configuration.
  #
  # It also changes the cadence in the right direction: with no `all_updates_rule`
  # this budget notifies on the threshold rules above rather than on every cost
  # update. An alert that fired every thirty minutes would be ignored by the third
  # day.

  depends_on = [google_project_service.required]
}
