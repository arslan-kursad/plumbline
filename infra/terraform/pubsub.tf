# Pub/Sub transport and the dead-letter path (architecture §2.2, §3.2, §3.4).
#
# The main push subscription is **not** here. It needs the worker's URL, which
# does not exist until Wave 2, and it is gated on #44 — the two ADR-0006
# obligations that make an unredacted dead-letter backlog defensible. Creating it
# early would put personal data on a path whose runbook had not been written yet.

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
    email_address = var.alert_email
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
