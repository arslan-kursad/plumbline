# Pub/Sub transport and the dead-letter path (architecture §2.2, §3.2, §3.4).
#
# The main push subscription arrives in Wave 3, below. It was held out of Wave 1
# for two reasons: it needs the worker's URL, which did not exist until Wave 2,
# and it is gated on #44 — the two ADR-0006 obligations that make an unredacted
# dead-letter backlog defensible. Creating it early would have put personal data
# on a path whose runbook had not been written yet. Both obligations merged in
# f7d6ca3, with Wave 1's topics; this file is the other end of that ordering.

# Topic retention is set on neither topic, and that is a cost invariant rather
# than an oversight: topic-level retention is a paid feature (architecture §2.2),
# and the plan guard refuses any topic that declares it.
resource "google_pubsub_topic" "traces" {
  project = var.project_id
  name    = "traces"

  labels = {
    component = "transport"
  }

  depends_on = [google_project_service.required]
}

resource "google_pubsub_topic" "traces_dlq" {
  project = var.project_id
  name    = "traces-dlq"

  labels = {
    component = "transport"
  }

  depends_on = [google_project_service.required]
}

# The dead-letter subscription. Pull, with no consumer by default (§3.4): a poison
# message waits here for a human, and the alert below is what says it is waiting.
# Replay is manual in v0.1 — a documented runbook step, not automation.
resource "google_pubsub_subscription" "traces_dlq" {
  project = var.project_id
  name    = "traces-dlq-pull"
  topic   = google_pubsub_topic.traces_dlq.id

  # Set explicitly, and the value is argued rather than inherited (#44, ADR-0006).
  #
  # A dead-lettered message carries unredacted personal data: redaction happens in
  # the worker, after deserialization, so anything that failed before that stage
  # still holds whatever the payload held. This duration is therefore how long that
  # data persists after a failure, and the two pressures point opposite ways.
  #
  # Shorter limits exposure. Longer preserves the evidence the DLQ exists for — and
  # a window shorter than the operator's response time destroys exactly what the
  # dead-letter path was built to keep. This project is maintained part-time, on the
  # order of 90 hours spread over six weeks (ADR-0004), so a 24-hour window would
  # routinely expire before anyone looked, leaving an alert about a message that no
  # longer exists: the worst of both, exposure without evidence.
  #
  # Seven days is the shortest window that survives a week of not looking. It is
  # also the API default, which is the point of writing it down: the default is
  # being *chosen* here, not accepted silently, and a future change to it has to
  # argue against this paragraph.
  message_retention_duration = "604800s"

  # Acknowledged messages are not retained. `retain_acked_messages = true` is the
  # setting that turns subscription retention into billable storage, and it would
  # also keep personal data past the point where it had been handled.
  retain_acked_messages = false

  # No expiration: a subscription that quietly deletes itself after 31 idle days
  # takes the dead-letter path with it, and the failure would be invisible until a
  # poison message had nowhere to go.
  expiration_policy {
    ttl = ""
  }

  ack_deadline_seconds = 60
}

# Free, and the destination has to exist before the policy can reference it.
# The address is a variable rather than a literal: this repository is public, and a
# maintainer's email address is personal data that would be world-readable and
# unerasable the moment it was pushed.
resource "google_monitoring_notification_channel" "alerts" {
  project      = var.project_id
  display_name = "plumbline alerts"
  type         = "email"

  labels = {
    # Lowercased here rather than trusted as typed. Monitoring normalises the address
    # it stores, so a value entered with capitals comes back different from what was
    # sent and every subsequent plan proposes changing it back — a diff that never
    # converges and that a drift check is right to fail on. Normalising at the source
    # makes the configuration independent of how the secret was typed.
    email_address = lower(var.alert_email)
  }

  depends_on = [google_project_service.required]
}

# A poison message disappearing silently violates *no silent degradation*
# (architecture §3.4). This is the only signal that the dead-letter path has
# caught something, because the subscription has no consumer.
resource "google_monitoring_alert_policy" "dlq_depth" {
  project      = var.project_id
  display_name = "traces-dlq has undelivered messages"
  combiner     = "OR"

  conditions {
    display_name = "undelivered messages on ${google_pubsub_subscription.traces_dlq.name}"

    condition_threshold {
      filter = join(" AND ", [
        "resource.type = \"pubsub_subscription\"",
        "resource.label.subscription_id = \"${google_pubsub_subscription.traces_dlq.name}\"",
        "metric.type = \"pubsub.googleapis.com/subscription/num_undelivered_messages\"",
      ])

      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "60s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.alerts.id]

  # Closing after a week rather than the default 7-day-and-then-forever behaviour
  # matters here: the condition is "depth above zero", which stays true until a
  # human drains the queue. An incident that auto-closes while the message is
  # still there would be a lie, so this is set to the maximum rather than to
  # something that tidies the console.
  alert_strategy {
    auto_close = "604800s"
  }

  documentation {
    content   = "A message failed delivery to the ingestion worker five times and was dead-lettered. It may contain unredacted personal data: redaction happens in the worker, after this message stopped reaching it. Follow docs/runbooks/dead-letter.md — inspect on a workstation, never paste content into an issue, a pull request or a chat transcript, and prefer replay over manual extraction because a replayed message goes through the redaction stage."
    mime_type = "text/markdown"
  }

  depends_on = [google_project_service.required]
}

# --- the push path (Wave 3) -------------------------------------------------
#
# `traces` -> the ingestion worker, over an authenticated push. This is the
# resource #44 gated: everything below moves messages that still carry unredacted
# personal data, because redaction happens in the worker after deserialization
# (ADR-0006), and the dead-letter path holds whatever failed before that stage.

resource "google_pubsub_subscription" "traces_push" {
  project = var.project_id
  name    = "traces-push"
  topic   = google_pubsub_topic.traces.id

  labels = {
    component = "transport"
  }

  push_config {
    # Built from the service's own URI and the shared path local, not typed out.
    # A wrong path here is not a configuration error anyone sees: the worker's mux
    # answers 404, Pub/Sub counts that as a failed delivery, and five of them
    # dead-letter a message that nothing was ever wrong with.
    push_endpoint = "${google_cloud_run_v2_service.worker.uri}${local.push_path}"

    oidc_token {
      service_account_email = google_service_account.pubsub_push.email

      # The audience the worker checks, from the expression the worker's own
      # environment is set from (cloudrun.tf). A fixed string rather than the
      # service URL, so this resource does not depend on the earlier wave's
      # output for a value both sides have to agree on (W2.2).
      audience = local.push_oidc_audience
    }
  }

  # Matches the worker's request timeout (cloudrun.tf, `timeout = "60s"`), and the
  # two are one decision rather than two. A deadline shorter than the timeout
  # redelivers a message the worker is still working on, so a slow batch becomes
  # duplicate writes and burns delivery attempts on nothing; ADR-0002 makes those
  # duplicates survivable at the dedup layer, not free.
  ack_deadline_seconds = 60

  # Five, which is also the API's minimum and its default — set explicitly for the
  # same reason the DLQ's retention is (#44): a number nobody argued for is one a
  # future change has nothing to argue against.
  #
  # The floor is the right value here because the worker's failures are
  # deterministic. A payload that fails to deserialize fails identically on the
  # hundredth attempt, so additional attempts buy no recovery — they buy latency
  # to the DLQ, more CPU on a message that will not succeed, and more copies of
  # unredacted personal data in flight. What the five do cover is the transient
  # case: a cold start, a redeploy, an instance evicted mid-request.
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.traces_dlq.id
    max_delivery_attempts = 5
  }

  # Without a retry policy Pub/Sub redelivers immediately, and immediate is wrong
  # against a service with `min_instance_count = 0`. A cold start that refuses
  # three deliveries in the time it takes to boot would spend most of the budget
  # above before the worker had answered once, and dead-letter a healthy message
  # for being early. Ten seconds is longer than a warm instance needs and shorter
  # than a cold one takes; the ceiling keeps a genuine outage from retrying
  # tightly for a week.
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Seven days, matching `traces-dlq-pull` deliberately rather than by coincidence.
  #
  # This backlog is transit and the dead-letter subscription is evidence, so the
  # arguments are not the same ones #44 made. Shortening this window would not
  # limit exposure much — a message here is either delivered in seconds or
  # dead-lettered within five attempts, and the DLQ's own window then governs.
  # What a shorter window would do is drop messages during the one failure this
  # policy cannot catch: an outage on the Pub/Sub side, where delivery is never
  # attempted, nothing is dead-lettered, and the expiry is silent. Keeping the two
  # windows equal means the exposure question has one answer instead of two.
  message_retention_duration = "604800s"

  # As on the DLQ subscription: this is the setting that turns retention into
  # billable storage, and it would hold personal data past the point it was
  # handled.
  retain_acked_messages = false

  # No expiration, and here it guards more than the DLQ's does. A subscription
  # expires after 31 days without activity, and a pipeline with no agents pointed
  # at it yet is idle by definition — so the default would delete the ingest path
  # during exactly the period before F4 puts traffic on it, and the first symptom
  # would be published messages going nowhere with no subscription to alert on.
  expiration_policy {
    ttl = ""
  }

  # Ordering, not decoration. A subscription created before the invoker binding
  # starts refusing deliveries at once, and a dead-letter policy whose service
  # agent cannot publish to the target fails *quietly* — Pub/Sub keeps retrying
  # and the message never lands in `traces-dlq`, which is the one path in this
  # design that is supposed to catch everything else.
  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_service_iam_member.worker_push_invoker,
    google_pubsub_topic_iam_member.pubsub_agent_publishes_dlq,
  ]
}

# --- what Pub/Sub itself needs ----------------------------------------------
#
# Dead-lettering is performed by Google's own Pub/Sub service agent, not by any
# identity this project created, and it holds no rights on these resources by
# default. Verified against Google's dead-letter documentation at wave time rather
# than assumed: the agent needs `roles/pubsub.publisher` on the dead-letter
# **topic** to forward the message, and `roles/pubsub.subscriber` on the
# **subscription** carrying the policy to acknowledge the original.
#
# Both omissions fail silently, which is why they are written down rather than
# discovered: the subscription applies cleanly either way and the gap shows up as
# messages that retry forever and never reach the DLQ.

resource "google_pubsub_topic_iam_member" "pubsub_agent_publishes_dlq" {
  project = var.project_id
  topic   = google_pubsub_topic.traces_dlq.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "pubsub_agent_acks_traces_push" {
  project      = var.project_id
  subscription = google_pubsub_subscription.traces_push.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# No `roles/iam.serviceAccountTokenCreator` on `pubsub-push@` is written here, and
# the absence is deliberate rather than an omission.
#
# Minting the push token needs `iam.serviceAccounts.getOpenIdToken` on that
# account or an ancestor. Two grants already carry it, and one of them cannot be
# removed: `roles/pubsub.serviceAgent`, Google's automatic grant to the agent,
# includes that permission at project scope — read off `gcloud iam roles describe`
# rather than inferred — and `killswitch.tf` additionally grants project-scoped
# `roles/iam.serviceAccountTokenCreator` for Eventarc's own OIDC invocation.
#
# A third, narrower grant would change nothing that is reachable: it cannot make
# the subscription work in any case where it does not already, because the widest
# of the three is Google's and is a precondition of Pub/Sub functioning at all. It
# would only look like the control. W2.5 declined a decorative Firestore IAM
# condition on the same argument — a grant that narrows nothing teaches a reader
# that grants here are decorative — so the fact is recorded where the dependency
# is instead of restated as a resource.
