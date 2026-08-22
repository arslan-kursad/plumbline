# Artifact Registry (architecture §7, §8).
#
# The free allowance is 0.5 GB across the project, which is small enough that an
# image per deploy reaches it — this is a cost invariant with a real, near horizon
# rather than a theoretical one.

resource "google_artifact_registry_repository" "plumbline" {
  project       = var.project_id
  location      = var.region
  repository_id = "plumbline"
  format        = "DOCKER"
  description   = "Distroless collector and ingestion-worker images, built in CI and pushed through Workload Identity Federation."

  # Keep the last two versions per package: the one running and the one to roll
  # back to. Anything older is a copy of a commit that is still in git.
  cleanup_policies {
    id     = "keep-last-2"
    action = "KEEP"

    most_recent_versions {
      keep_count = 2
    }
  }

  # Everything the KEEP policy did not claim, once it has had a day to be wrong in.
  #
  # `older_than` was "0s" first, which reads as "no grace period" and is what the
  # intent actually was. Artifact Registry does not store a zero duration, so every
  # plan after the apply proposed re-adding a condition the API had dropped — a diff
  # that never converges. A day is the smallest value that both persists and buys
  # something real: an image is never eligible for deletion on the day it is pushed,
  # so a deploy cannot prune the artefact it just created.
  cleanup_policies {
    id     = "delete-the-rest"
    action = "DELETE"

    condition {
      older_than = "86400s"
    }
  }

  depends_on = [google_project_service.required]
}

# The repository this project did not create and has to bound anyway.
#
# A Gen2 Cloud Function is built by Cloud Build into an auto-created `gcf-artifacts`
# repository. Nothing in F0 owned it, it accumulates an image per function deploy,
# and it already holds ~93 MB of the 0.5 GB allowance from a handful of kill-switch
# deploys. `docs/runbooks/kill-switch.md` §7 assigns it to F2 explicitly.
#
# Adopted rather than left alone, because "not ours" is not a size limit.
import {
  to = google_artifact_registry_repository.gcf_artifacts
  id = "projects/${var.project_id}/locations/${var.region}/repositories/gcf-artifacts"
}

resource "google_artifact_registry_repository" "gcf_artifacts" {
  project       = var.project_id
  location      = var.region
  repository_id = "gcf-artifacts"
  format        = "DOCKER"

  # Cloud Functions' own words, preserved. Adopting a repository is not a licence
  # to erase the metadata of the system that still writes to it — and a plan that
  # blanks a description nobody asked to change is a diff a reviewer has to think
  # about for no reason.
  description = "This repository is created and used by Cloud Functions for storing function docker images."

  # Live from Wave 2 (#57). What the dry run was asked and what it answered, in
  # the order that matters:
  #
  # The question was whether keep-last-2 would ever select the image the
  # kill-switch function runs — deleting that breaks the last cost control in the
  # project, at the moment it is needed, and nothing reports it until then.
  #
  # **The dry run produced no decisions, because it had nothing to select.** Read
  # on 2026-08-22: each of the two packages here holds exactly one version, so
  # keep-last-2 claims both and DELETE selects nothing. There are no cleanup
  # entries in this project's Artifact Registry logs at all. W1.6 assumed this
  # repository accumulated an image per function deploy; the measurement says it
  # holds one image plus one build cache, 93 MB of a project-wide 0.5 GB.
  #
  # So the flag is switched on evidence that the policy is *inert today*, not on
  # evidence that it deletes the right things — and saying otherwise would be the
  # comfort object ADR-0004 §1 describes. What carries the remaining risk is
  # structural rather than observed: the running image is the most recent by
  # construction, keep-last-2 spares the two most recent, and `older_than` gives a
  # day of grace on top. It is the same protection the `plumbline` repository has
  # been running live under since Wave 1.
  #
  # The first genuine exercise is the third kill-switch deploy, which is when a
  # version first becomes eligible. docs/runbooks/kill-switch.md §7 is where to
  # look if a deploy is ever followed by a function that cannot pull its image.
  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-last-2"
    action = "KEEP"

    most_recent_versions {
      keep_count = 2
    }
  }

  # Everything the KEEP policy did not claim, once it has had a day to be wrong in.
  #
  # `older_than` was "0s" first, which reads as "no grace period" and is what the
  # intent actually was. Artifact Registry does not store a zero duration, so every
  # plan after the apply proposed re-adding a condition the API had dropped — a diff
  # that never converges. A day is the smallest value that both persists and buys
  # something real: an image is never eligible for deletion on the day it is pushed,
  # so a deploy cannot prune the artefact it just created.
  cleanup_policies {
    id     = "delete-the-rest"
    action = "DELETE"

    condition {
      older_than = "86400s"
    }
  }

  depends_on = [google_project_service.required]
}
