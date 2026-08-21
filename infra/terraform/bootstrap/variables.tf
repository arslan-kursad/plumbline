variable "project_id" {
  description = "GCP project ID that owns the Terraform state bucket."
  type        = string
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
