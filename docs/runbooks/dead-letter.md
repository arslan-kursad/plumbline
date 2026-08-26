# Runbook — the dead-letter path

**Status:** written ahead of the subscription it describes (F2 Wave 1) and now
live. The push subscription that produces dead letters was gated on this file
existing first (#44); it was created in Wave 3, two waves after this was merged,
which is what makes the ordering claim checkable.

A message that fails delivery to the ingestion worker five times is routed to the
`traces-dlq` topic and waits on the `traces-dlq-pull` subscription, which has no
consumer. Nothing drains it automatically. The depth alert is the only thing that
says a message is there.

*Fails* covers more than a poison payload. A 404 from a wrong push path, a 403 from
a broken invoker binding, and a worker that never became ready all count as failed
deliveries, so a full DLQ is not by itself evidence that anything was wrong with
the messages in it — and in those three cases every message is dead-lettered, not
one. Check the delivery response codes and the worker's logs before concluding the
payloads are at fault; a queue that filled all at once is a transport failure until
proven otherwise.

Design and rationale: [ADR-0002](../adr/ADR-0002-pubsub-contract-at-least-once.md),
[ADR-0006](../adr/ADR-0006-pii-redaction-boundary.md), architecture §3.4.
Configuration: [`infra/terraform/pubsub.tf`](../../infra/terraform/pubsub.tf).

## 1. What a dead-lettered message contains

**Assume personal data. It is not a hypothetical.**

Redaction happens in the worker, *after* deserialization (ADR-0006). A message
reaches the dead-letter path precisely because it never got through that stage, so
it still carries whatever the agent emitted:

- `user.id`, `user.email`, `organization.id`, `session.id`
- `workspace.host_paths` for the claude-code dialect, which embeds real filesystem
  paths and therefore usernames
- whatever else the emitter attached that the mapping tables would have dropped or
  hashed

The payload is a gzipped OTLP protobuf, so `gcloud pubsub subscriptions pull`
prints base64, not prose. That is not protection — it is one decode away — but it
does mean exposure is something you do deliberately rather than something the
terminal does to you. The message *attributes* (`api_key_id`, `source_dialect`,
`content_encoding`, `schema_url`) are visible immediately and carry no personal
data by design (§3.2).

**This repository and its issue tracker are public.** Message content is inspected
on a workstation and **never** pasted into an issue, a pull request, a commit
message, or a chat transcript. When a transcript of a triage session is archived —
and F2's acceptance criteria require one — the content is elided and the shape is
described instead.

## 2. When the alert fires

`traces-dlq has undelivered messages` fires when depth exceeds zero for a minute.
It stays open until the queue is drained, because the condition it names stays
true until then.

Triage, in order:

1. **Depth and age.** How many, and how long have they been there?

   ```bash
   gcloud pubsub subscriptions describe traces-dlq-pull --project "$PROJECT_ID"
   ```

2. **Attributes before content.** Pull one message without acknowledging it. The
   attributes usually identify the failure without decoding anything:

   ```bash
   gcloud pubsub subscriptions pull traces-dlq-pull \
     --project "$PROJECT_ID" --limit 1 --format='value(message.attributes)'
   ```

   `--auto-ack` is deliberately absent. Acknowledging removes the message, and the
   retention window (§4) is what stands between you and losing the evidence.

3. **Worker logs for the same window.** The worker logs why a message failed. That
   is the diagnosis; the message body is corroboration, and most triage never needs
   it.

4. **Decode only if the logs are not enough**, and only on your own machine. Never
   into a shared paste, a gist, or a screenshot destined for an issue.

## 3. Resolving it

**Replay is the preferred resolution.** A replayed message re-enters the pipeline
at the collector's output and therefore passes through the redaction stage;
anything extracted by hand does not, and whatever you extracted is now sitting
outside the system's controls in a place nobody audits.

Replay is manual in v0.1 — a documented step, not automation (§3.4):

```bash
# Republish one message's data back to the main topic, then acknowledge the copy
# on the dead-letter subscription. Do this only after the cause is fixed: a replay
# into an unfixed worker dead-letters again, five deliveries later.
gcloud pubsub subscriptions pull traces-dlq-pull \
  --project "$PROJECT_ID" --limit 1 --format='value(message.data)' > /tmp/dlq-message.b64

base64 --decode < /tmp/dlq-message.b64 > /tmp/dlq-message.bin
gcloud pubsub topics publish traces \
  --project "$PROJECT_ID" --message="$(cat /tmp/dlq-message.bin)" \
  --attribute=content_encoding=gzip,...   # carry the original attributes across

shred -u /tmp/dlq-message.b64 /tmp/dlq-message.bin 2>/dev/null || rm -f /tmp/dlq-message.b64 /tmp/dlq-message.bin
```

Two things about those temporary files: they hold unredacted personal data on your
disk for as long as they exist, and `/tmp` is not a safe place to leave them. Remove
them in the same session, not "later".

**If the message is genuinely unprocessable** — a truncated payload, a protobuf the
worker will never deserialize — acknowledge it to clear the queue, and record what
it was: dialect, `api_key_id`, size, and the worker's error. That record is the
finding. The bytes are not.

## 4. Retention, and what it costs either way

The subscription retains messages for **seven days** (`604800s`), set explicitly in
Terraform rather than inherited (#44).

The window is the exposure window: unredacted personal data persists exactly that
long after a failure. It is also the evidence window, and a window shorter than the
operator's response time destroys what the dead-letter path exists to preserve.
This project is maintained part-time, so a day would routinely expire before anyone
looked — leaving an alert about a message that no longer exists, which is exposure
without evidence.

Acknowledged messages are **not** retained (`retain_acked_messages = false`): that
setting is what turns subscription retention into billable storage, and it would
also keep personal data past the point where it had been handled.

Topic-level retention is off on every topic. It is a paid feature, a separate
mechanism, and the plan guard refuses any topic that declares it (architecture
§2.2, §7.1).

## 5. What this runbook does not cover

- **Why** a message failed. That is the worker's logs and the poison-fixture tests,
  not this file.
- Bulk replay. There is no tooling for it in v0.1, and building some in the middle
  of an incident is how a replay loop gets written.
- The main push subscription's configuration — `traces-push`, in
  [`infra/terraform/pubsub.tf`](../../infra/terraform/pubsub.tf), with its reasoning
  in F2 decision log W3.2–W3.5. What belongs here is what to do with a message once
  it has arrived; why five delivery attempts rather than fifty belongs there.
