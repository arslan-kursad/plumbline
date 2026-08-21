terraform {
  required_version = ">= 1.9.0, < 2.0.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }

  # Local state on purpose. This module creates the bucket that every other
  # module uses as its remote backend, so it cannot itself be backed by that
  # bucket. Its state describes exactly one resource and is reproducible by
  # re-running the module against the existing bucket; see README.md.
}

provider "google" {
  project = var.project_id
  region  = var.region
}
