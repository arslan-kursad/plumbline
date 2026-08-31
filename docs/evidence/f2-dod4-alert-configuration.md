# F2C-08.1 — the DLQ alert, read from the API

**Measured:** 2026-08-31 · **Directive item:** F2C-08 claim 1 (v1.6, `442d08e`)
**Claim proved:** the `num_undelivered_messages > 0` policy exists, is enabled, and is
bound to a notification channel.
**Claim NOT proved:** that a notification is delivered. That is claim 2, and it is
send-shaped — it needs its own go-ahead and has not been run.

## Provenance

The Lane A permission layer denied `gcloud alpha monitoring policies list`. Under the
directive's provenance clause the maintainer ran the commands and returned the raw
output; a human at the keyboard changes who typed it, not what was read. This is still
an API read, and it is not a reading of `pubsub.tf` — which would be intent, not state.

```
gcloud alpha monitoring policies list --project plumbline-19458 --format=json
gcloud alpha monitoring channels list  --project plumbline-19458 --format=json
```

**One field is redacted below** and only one: `labels.email_address` on the channel.
The address is not in this repository — Terraform takes it as `var.alert_email` — and
this repository is public. Redacting it here keeps it that way. Everything else is
verbatim.

## The policy

| Field | Value |
| --- | --- |
| `name` | `projects/plumbline-19458/alertPolicies/14947663537432968254` |
| `displayName` | `traces-dlq has undelivered messages` |
| `enabled` | **`true`** |
| `combiner` | `OR` |
| `conditions[0].displayName` | `undelivered messages on traces-dlq-pull` |
| filter | `resource.type = "pubsub_subscription" AND resource.label.subscription_id = "traces-dlq-pull" AND metric.type = "pubsub.googleapis.com/subscription/num_undelivered_messages"` |
| `comparison` | `COMPARISON_GT` |
| `duration` | `60s` |
| aggregation | `alignmentPeriod: 60s`, `perSeriesAligner: ALIGN_MAX` |
| `alertStrategy.autoClose` | `604800s` (7 days) |
| `notificationChannels` | `projects/plumbline-19458/notificationChannels/17645137777150770481` |
| created / last mutated | `2026-08-21T20:59:22Z` by `ci-deploy@plumbline-19458.iam.gserviceaccount.com` |

**`thresholdValue` is absent from the response, and that is worth naming rather than
glossing.** The Monitoring API omits zero-valued fields, so an absent `thresholdValue`
with `COMPARISON_GT` is `> 0` — which is the condition F2C-08 asks for. It is recorded
as *absent, read as zero* rather than as *"> 0" observed*, because those are different
observations and only one of them was actually made.

`mutatedBy` is `ci-deploy`, so the policy is Terraform-owned and arrived through the
gated path — consistent with DoD 5, and not evidence for it.

The policy also carries operator documentation, verbatim from the API:

> A message failed delivery to the ingestion worker five times and was dead-lettered.
> It may contain unredacted personal data: redaction happens in the worker, after this
> message stopped reaching it. Follow docs/runbooks/dead-letter.md — inspect on a
> workstation, never paste content into an issue, a pull request or a chat transcript,
> and prefer replay over manual extraction because a replayed message goes through the
> redaction stage.

That text is now slightly behind the runbook: `dead-letter.md` §1 has since replaced
"never paste content" with an enumerated archive rule (W2.20). The documentation is not
wrong, it is less specific than what it points at, and it points at the right file.

## The channel

| Field | Value |
| --- | --- |
| `name` | `projects/plumbline-19458/notificationChannels/17645137777150770481` |
| `displayName` | `plumbline alerts` |
| `type` | `email` |
| `enabled` | **`true`** |
| `labels.email_address` | *(redacted — see Provenance)* |
| created | `2026-08-21T20:59:18Z` |

## The binding, which is the part that could have been wrong

The policy's `notificationChannels[0]` and the channel's `name` are the same string:
`projects/plumbline-19458/notificationChannels/17645137777150770481`. A policy bound to
a channel that no longer exists, or to a different one, is the failure this check is
for, and it is ruled out by comparing the two identifiers rather than by observing that
both objects exist.

## What remains unproven

`enabled: true` on an email channel means the channel is configured and not disabled.
It does not mean mail arrives. Delivery is F2C-08.2 and needs a separate go-ahead;
until it runs, the alert is a configured control, not a proven one — and a drill that
discovers otherwise would have spent the clean-DLQ precondition to learn it.
