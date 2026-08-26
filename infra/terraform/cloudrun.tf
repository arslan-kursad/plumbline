# The two services (architecture §2.1, §2.3, §6.1, §8).
#
# `analytics-api` is F3's and is deliberately absent: §7.1 lists the type for three
# services and this phase builds two (decision log D6).
#
# Both services are pinned to an image tag that lives in this repository
# (var.image_tag), not to a tag chosen at dispatch time. The approval gate binds a
# reviewer to a *fingerprint of addresses and actions* (W1.1), which by construction
# cannot see an attribute value — so an image chosen outside the repository would be
# the one attribute the gate was blind to, on the resource where it matters most.
# In git, the version being deployed is reviewed when the pull request is.

locals {
  registry = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.plumbline.repository_id}"

  collector_image = "${local.registry}/collector:${var.image_tag}"
  worker_image    = "${local.registry}/worker:${var.image_tag}"

  # The audience the worker requires and the Wave 3 subscription will mint for.
  # One expression, read by both, so the two cannot be edited apart — a mismatch
  # here refuses every delivery with a correct-looking configuration on both sides.
  push_oidc_audience = "plumbline-ingestion-worker"

  # The path the worker serves push deliveries on, by the same argument.
  #
  # The worker defaults `PLUMBLINE_PUSH_PATH` to this value, so Wave 2 could leave
  # it unset and Wave 3 could have written the path into the subscription's
  # endpoint directly. That would be two places stating one route and agreeing by
  # inspection — the shape W2.3 refused for the Firestore collection name. The
  # failure mode is quiet in a way the audience mismatch is not: a wrong path is a
  # 404 from the worker's own mux, which Pub/Sub retries five times and then
  # dead-letters, so the first symptom is a DLQ full of healthy messages.
  push_path = "/push"
}

# --- identities -------------------------------------------------------------
#
# One per component, per §6.1. Not one shared "runtime" identity: the whole point
# of the boundary table is that the collector cannot write BigQuery and the worker
# cannot publish to Pub/Sub, and a shared account would make both statements false
# while every other control still looked correct.

resource "google_service_account" "collector" {
  project      = var.project_id
  account_id   = "collector"
  display_name = "Cloud Run collector (data plane)"
  description  = "Publishes to the traces topic and reads the hashed key registry. Holds no secret (§6.3)."
}

resource "google_service_account" "worker" {
  project      = var.project_id
  account_id   = "ingestion-worker"
  display_name = "Cloud Run ingestion worker (write path)"
  description  = "Writes normalized spans to the spans table through the Storage Write API."
}

# Created in this wave, used in the next: Wave 3 binds it as the sole
# roles/run.invoker on the worker and mints the push subscription's OIDC tokens.
# It exists now because the worker's configuration names it — the audience check
# is against this address, so the service cannot be configured without it.
resource "google_service_account" "pubsub_push" {
  project      = var.project_id
  account_id   = "pubsub-push"
  display_name = "Pub/Sub push identity"
  description  = "Mints the OIDC tokens the push subscription presents to the worker (Wave 3)."
}

# --- collector --------------------------------------------------------------

resource "google_cloud_run_v2_service" "collector" {
  project  = var.project_id
  name     = "collector"
  location = var.region

  # Agents send from outside the project, so this endpoint is public and the API
  # key layer is the authentication boundary (§6.1). The approximate per-instance
  # rate limit that comes with it is the known limitation in §6.2, not a surprise.
  ingress = "INGRESS_TRAFFIC_ALL"

  # These services hold no state: the data is in BigQuery and Firestore, which
  # carry their own delete protection. A service the configuration that created it
  # cannot destroy is drift waiting to happen.
  deletion_protection = false

  template {
    service_account = google_service_account.collector.email

    scaling {
      # Both halves are cost invariants (§7): scale to zero is what makes an idle
      # pipeline free, and the ceiling is what bounds a runaway one.
      min_instance_count = 0
      max_instance_count = 2
    }

    # Bounded by memory and payload size rather than by throughput. A request can
    # carry an OTLP export up to the size budget, and the splitter holds the
    # compressed batches alongside it; 20 concurrent exports is what fits in 512Mi
    # with the Go runtime, and exceeding it would OOM the instance rather than
    # queue.
    max_instance_request_concurrency = 20

    containers {
      image = local.collector_image

      # Cloud Run routes to exactly one container port. The collector serves
      # OTLP/HTTP and OTLP/gRPC on separate listeners, so **only OTLP/HTTP is
      # reachable in the cloud in F2** — the gRPC listener still starts and
      # nothing routes to it. Recorded rather than papered over: closing it needs
      # either a second service or h2c multiplexing in the collector, and both are
      # beyond this spec (decision log W2.4).
      ports {
        name           = "http1"
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        # Request-based billing: CPU is allocated while a request is in flight and
        # not between them, which is what keeps an idle service at zero cost.
        cpu_idle          = true
        startup_cpu_boost = false
      }

      env {
        name  = "PLUMBLINE_HTTP_ADDR"
        value = ":8080"
      }

      env {
        name  = "PLUMBLINE_PUBSUB_PROJECT"
        value = var.project_id
      }

      env {
        name  = "PLUMBLINE_PUBSUB_TOPIC"
        value = google_pubsub_topic.traces.name
      }

      # The cloud key registry (F2 Wave 2). Setting this and PLUMBLINE_KEY_REGISTRY
      # together is a startup error by design, so there is nothing to get wrong here
      # except leaving both unset, which is also a startup error.
      env {
        name  = "PLUMBLINE_KEY_FIRESTORE_PROJECT"
        value = var.project_id
      }
    }
  }

  # The actAs binding, explicitly. A service references its runtime identity's
  # email, so Terraform orders it after the service account — but not after the
  # grant that lets this deployer impersonate it, which is a separate resource.
  # Without this the two race, and the apply fails with `iam.serviceaccounts.actAs
  # denied` on an account it created moments earlier.
  depends_on = [
    google_project_service.required,
    google_service_account_iam_member.ci_deploy_acts_as,
  ]
}

# Public, because agents authenticate with an API key and not with Google
# identities (§6.1). This is the one unauthenticated endpoint in the project and
# it is written where a reader looking for it will find it.
resource "google_cloud_run_v2_service_iam_member" "collector_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.collector.location
  name     = google_cloud_run_v2_service.collector.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- ingestion worker -------------------------------------------------------

resource "google_cloud_run_v2_service" "worker" {
  project  = var.project_id
  name     = "ingestion-worker"
  location = var.region

  # Verified against current documentation at wave time, as the wave issue
  # requires, rather than assumed: Cloud Run counts a Pub/Sub push subscription as
  # an internal source when it is in the same project (or VPC-SC perimeter) and
  # targets the default `run.app` URL rather than a custom domain. Both hold here —
  # one project, no custom domain — so INTERNAL_ONLY is reachable by the Wave 3
  # subscription and closed to the internet.
  #
  # Guessing this wrong has two failure modes and both are quiet: `all` leaves an
  # endpoint exposed whose only protection is the token check, and an over-tight
  # setting produces a subscription that delivers nothing while every dashboard
  # looks healthy.
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  deletion_protection = false

  template {
    service_account = google_service_account.worker.email

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    # Lower than the collector's, because this side deserializes: a push envelope
    # carries a base64 payload that is decompressed and parsed into an object
    # graph, so the working set per request is several times the message. Eight
    # concurrent messages is what 512Mi absorbs; Pub/Sub redelivers the rest
    # rather than dropping them.
    max_instance_request_concurrency = 8

    # A push that outlives the subscription's acknowledgement deadline is
    # redelivered whatever this service does afterwards, so finishing later than
    # that only burns CPU on a message someone else is already retrying.
    timeout = "60s"

    containers {
      image = local.worker_image

      ports {
        name           = "http1"
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = false
      }

      # Explicit, though it is also the default: this is the setting that decides
      # whether the endpoint is protected at all (§6.1), and a protection that
      # depends on a default staying put is worth one line.
      env {
        name  = "PLUMBLINE_PUSH_AUTH"
        value = "oidc"
      }

      # A fixed string, not the service URL: the subscription that mints these
      # tokens is created in Wave 3 from this same value, and an audience derived
      # from the service's own URL would make the earlier resource depend on the
      # later one's output.
      env {
        name  = "PLUMBLINE_PUSH_OIDC_AUDIENCE"
        value = local.push_oidc_audience
      }

      env {
        name  = "PLUMBLINE_PUSH_OIDC_SERVICE_ACCOUNT"
        value = google_service_account.pubsub_push.email
      }

      # Set explicitly, though it repeats the worker's own default: the Wave 3
      # subscription's push endpoint is built from the same local, so the route
      # is stated once and read twice rather than matched by hand.
      env {
        name  = "PLUMBLINE_PUSH_PATH"
        value = local.push_path
      }

      env {
        name  = "PLUMBLINE_SINK"
        value = "bigquery"
      }

      env {
        name  = "PLUMBLINE_BQ_PROJECT"
        value = var.project_id
      }

      env {
        name  = "PLUMBLINE_BQ_DATASET"
        value = google_bigquery_dataset.plumbline.dataset_id
      }

      env {
        name  = "PLUMBLINE_BQ_TABLE"
        value = google_bigquery_table.spans.table_id
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_service_account_iam_member.ci_deploy_acts_as,
  ]
}

# The worker's sole invoker (Wave 3, DoD 7's second half).
#
# Unauthenticated invocation is exactly "allUsers holds roles/run.invoker", so the
# control is what is *not* written here: no `allUsers` member on this service, in
# this wave or any later one. What is written is the one principal allowed to call
# it — the identity the push subscription mints its OIDC tokens as.
#
# This is IAM, and it is the outer of two independent checks. Cloud Run refuses a
# caller that is not this principal; the worker then refuses a token whose audience
# or issuer-verified email is not the pair it was configured with (W2.2). Either
# alone would be a defensible boundary. Both is what makes a mistake in one of them
# a failed delivery rather than an open write path to `spans`.
resource "google_cloud_run_v2_service_iam_member" "worker_push_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.worker.location
  name     = google_cloud_run_v2_service.worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_push.email}"
}

# --- data-plane grants ------------------------------------------------------

# Publish to `traces` and to nothing else. A project-level roles/pubsub.publisher
# would also let the collector publish to `billing-alerts`, which is the kill-switch
# trigger — the one topic in this project where a spurious message has consequences.
resource "google_pubsub_topic_iam_member" "collector_publishes_traces" {
  project = var.project_id
  topic   = google_pubsub_topic.traces.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.collector.email}"
}

# Write to `spans` and to nothing else — not the dataset, so the views the analytics
# path will read are not writable by the write path.
#
# dataEditor at table scope is what the Storage Write API needs
# (bigquery.tables.updateData plus tables.get); the legacy streaming path is
# unreachable by construction anyway (Gate A).
resource "google_bigquery_table_iam_member" "worker_writes_spans" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.plumbline.dataset_id
  table_id   = google_bigquery_table.spans.table_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.worker.email}"
}

# The key registry read, and the one grant in this file that is wider than §6.1
# describes.
#
# §6.1 asks for a collection-scoped grant. Firestore has no such thing: IAM is
# granted at project scope (conditions can narrow it to a *database*, and this
# project has exactly one), and per-collection access exists only through Security
# Rules, which govern mobile and web clients rather than a server-side client
# library. So the narrowest grant that reads `api_keys` is read access to all
# Firestore data in the project.
#
# Recorded rather than rounded down to what the document says: the boundary table
# is corrected in the same change (architecture v0.9, §6.1), because a document that
# describes a control the platform cannot implement is worse than one that admits
# the limit. Decision log W2.5.
resource "google_project_iam_member" "collector_reads_firestore" {
  project = var.project_id
  role    = "roles/datastore.viewer"
  member  = "serviceAccount:${google_service_account.collector.email}"
}

# --- what the deploy identity needs to create the above ---------------------
#
# D6: the roles grow per wave, in the wave that needs them, and are enumerated in
# the wave issue.

# actAs on the three runtime identities, granted per service account rather than
# through a project-level roles/iam.serviceAccountUser. Deploying a Cloud Run
# service that runs as an identity requires impersonation rights over *that*
# identity; the project-level role would grant them over every service account in
# the project, including the kill-switch's.
resource "google_service_account_iam_member" "ci_deploy_acts_as" {
  for_each = {
    collector   = google_service_account.collector.name
    worker      = google_service_account.worker.name
    pubsub_push = google_service_account.pubsub_push.name
  }

  service_account_id = each.value
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.ci_deploy.email}"
}
