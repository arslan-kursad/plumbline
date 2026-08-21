# Remote-state bucket for the root module (F0 spec W5).
#
# Free-tier note: Cloud Storage Always Free is 5 GB-months in US regions. A
# Terraform state file for this project is measured in kilobytes; versioning is
# on so a corrupted apply is recoverable, and the lifecycle rule keeps the
# number of retained noncurrent versions bounded so the free tier cannot be
# eroded by accumulation.
resource "google_storage_bucket" "tfstate" {
  name     = "${var.project_id}-tfstate"
  location = var.region
  project  = var.project_id

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 10
    }
    action {
      type = "Delete"
    }
  }
}
