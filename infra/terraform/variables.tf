variable "project_id" {
  description = "GCP project ID hosting the plumbline pipeline."
  type        = string
}

variable "billing_account_id" {
  description = <<-EOT
    Billing account ID (format 012345-6789AB-CDEF01) the project is linked to.
    Used to create the budget. The kill-switch detaches this account from the
    project; re-attaching is a manual human step (docs/runbooks/kill-switch.md).
  EOT
  type        = string

  validation {
    condition     = can(regex("^[0-9A-F]{6}-[0-9A-F]{6}-[0-9A-F]{6}$", var.billing_account_id))
    error_message = "Billing account ID must look like 012345-6789AB-CDEF01."
  }
}

variable "region" {
  description = "Region for all resources. Fixed to us-central1 by the zero-cost envelope (architecture §8)."
  type        = string
  default     = "us-central1"

  validation {
    condition     = var.region == "us-central1"
    error_message = "Region is fixed to us-central1 (architecture §8, zero-cost envelope)."
  }
}

variable "budget_amount" {
  description = <<-EOT
    Budget amount in whole units of the billing account's own currency. The budget
    is not the trigger: notifications are published on every cost update
    (all_updates_rule) and the function detaches billing whenever reported cost is
    strictly greater than zero. The amount only scales the threshold rule that
    records "budget exceeded" in the alert stream, so its currency is immaterial to
    the control.
  EOT
  type        = string
  default     = "1"
}

variable "budget_currency_code" {
  description = <<-EOT
    ISO 4217 currency for the budget amount. Left null on purpose: the Budget API
    requires a specified currency to match the billing account's currency exactly,
    and rejects the create otherwise. Omitting it inherits the account's currency,
    so this configuration is portable across billing accounts rather than pinned to
    whichever one it was first written against.
  EOT
  type        = string
  default     = null
}

variable "bigquery_daily_query_quota_mib" {
  description = <<-EOT
    Project-level custom quota for BigQuery query bytes processed per day, in MiB
    (the unit the BigQuery custom-quota API takes). Default 20480 MiB = 20 GiB/day:
    31 such days total 620 GiB, inside the 1 TiB/month free query tier, and a
    single runaway query is bounded four orders of magnitude below the 200 TiB/day
    default. Rationale: docs/runbooks/kill-switch.md.
  EOT
  type        = number
  default     = 20480

  validation {
    # 1 TiB/month over a 31-day month is 33825 MiB/day; above that, a full month
    # at the daily limit would leave the free query tier.
    condition     = var.bigquery_daily_query_quota_mib > 0 && var.bigquery_daily_query_quota_mib <= 33825
    error_message = "Quota must be positive and at most 33825 MiB/day, so a 31-day month stays inside the 1 TiB/month free query tier."
  }
}

variable "killswitch_memory" {
  description = <<-EOT
    Memory for the kill-switch function. 256Mi rather than the 128Mi floor: this
    is the last control in the chain (ADR-0004 §2) and its reliability matters
    more than the marginal GB-seconds, which stay far inside the free tier at a
    ~30-minute notification cadence.
  EOT
  type        = string
  default     = "256Mi"
}

variable "killswitch_runtime" {
  description = <<-EOT
    Cloud Functions Gen2 runtime for the kill-switch. Pinned rather than tracking
    "latest": a runtime deprecation must be a visible change to this file, not a
    surprise on the day the function is needed.

    `go126` rather than `go125`, though both are generally available and the
    function's dependency set only requires Go 1.25: go125 is deprecated on
    2026-10-01 and decommissioned on 2027-04-01, while go126 runs to Feb/Mar 2027
    and Aug/Sep 2027. Same code, a year more runway, and the kill-switch is the
    component least worth rebuilding under time pressure.

    Confirm the value is still supported with
    `gcloud functions runtimes list --region us-central1` before the first apply.
    Raising it past the language version in the function's go.mod is safe; lowering
    it below is not.
  EOT
  type        = string
  default     = "go126"
}

variable "github_owner" {
  description = "GitHub account that owns the repository; pinned in the WIF provider's attribute condition."
  type        = string
  default     = "arslan-kursad"
}

variable "github_repository" {
  description = "owner/name of the repository allowed to federate. Any other repository is refused by the provider itself."
  type        = string
  default     = "arslan-kursad/plumbline"
}

variable "state_bucket" {
  description = <<-EOT
    Terraform state bucket created by ./bootstrap. Named here so the CI identity's
    storage access is scoped to this bucket alone rather than to the project.
    Defaults to the name bootstrap/ generates.
  EOT
  type        = string
  default     = null
}

variable "image_tag" {
  description = <<-EOT
    Commit SHA tagging the collector and worker images Cloud Run runs. CI pushes
    both images tagged by commit and never as `latest`, so this value answers
    "which code is running" exactly.

    It lives in the repository rather than arriving at dispatch time on purpose.
    The approval gate binds the reviewer to a fingerprint of addresses and actions
    (decision log W1.1), which cannot see an attribute value — so a tag chosen
    outside the repository would be invisible to the one control that is supposed
    to make a deploy deliberate. Here, bumping it is a reviewed pull request.

    Consequence, accepted: the deployed image lags the merge that produced it by
    one commit, because the images for a commit exist only after CI has built it.

    **Bumping it is part of arming a wave, not an afterthought.** The default below
    must name a commit whose images CI has actually pushed *and* whose code carries
    what the wave deploys — the plan job verifies the first half against Artifact
    Registry and refuses if the images are absent; the second half is the reviewer's.
  EOT
  type        = string

  # Merge commit of #62, the change that first pushed both images (recorded in
  # issue #63 with the push time). Bumped by the wave pull request to the commit
  # carrying the OIDC validator and the Firestore registry before Wave 2 is armed.
  default = "0a0993da1e1453b28b5b9dc6e93a4c82824db676"

  validation {
    # A full commit SHA, not a moving tag: `latest` or a branch name would make
    # "which image is running" unanswerable and would silently redeploy on the
    # next apply.
    condition     = can(regex("^[0-9a-f]{40}$", var.image_tag))
    error_message = "image_tag must be a full 40-character commit SHA — the tag CI pushes. Moving tags are refused."
  }
}

variable "alert_email" {
  description = <<-EOT
    Destination for the dead-letter depth alert (architecture §3.4). An email
    notification channel is free; every other channel type this project could use
    either costs money or depends on a third-party SaaS.

    Deliberately a variable with no default. The repository is public, so a
    hard-coded address would be world-readable personal data in a history that is
    not erasable in practice — and CI supplies it from a secret, which the plan
    output then masks.
  EOT
  type        = string

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+$", var.alert_email))
    error_message = "alert_email must be an email address."
  }
}
