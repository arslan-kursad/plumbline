terraform {
  required_version = ">= 1.9.0, < 2.0.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region

  # Attribute API quota to this project, and say so in the request header.
  #
  # Without this, requests made with user credentials are attributed to the
  # project that owns the OAuth client — Google's shared gcloud client project —
  # and any API that requires a quota project fails there. Two resources here do:
  # the budget (billingbudgets) and the quota preference (cloudquotas). The error
  # says the quota project "is not set by default" and names a consumer project
  # nobody recognises, which reads like a missing API rather than a missing
  # header. Setting the ADC quota project is not enough: the provider only sends
  # it when told to.
  #
  # Callers therefore need serviceusage.services.use on this project — granted to
  # the CI identity in wif.tf.
  user_project_override = true
  billing_project       = var.project_id
}
