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
    surprise on the day the function is needed. Confirm the value is still
    supported with `gcloud functions runtimes list --region us-central1` before
    the first apply. The value is coupled to the function's go.mod: the resolved
    dependency set requires Go 1.25, so a lower runtime will not build.
  EOT
  type        = string
  default     = "go125"
}
