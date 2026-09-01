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

### The archive rule: metadata only, and it is a list rather than a judgement

"Elided" above was a principle without an enumeration, which leaves the decision to
whoever is archiving at the time. This is the list. **A DLQ archive never contains
payload bytes** — not raw, not base64, not decoded, not "just the interesting field".
What may be recorded is exactly:

| Field | Where it comes from |
| --- | --- |
| `message_id` | Pub/Sub, assigned at publish |
| `publish_time` | Pub/Sub |
| delivery attempt count | `deliveryAttempt` on the pulled message |
| message attributes | the §3.2 contract — `api_key_id`, `source_dialect`, `content_encoding`, `schema_url` |
| payload size in bytes | measured, not quoted |
| SHA-256 of the payload | computed locally, never the payload itself |

The digest is what makes the rule usable rather than merely safe: two archives can be
compared, and a replayed message can be matched to its original, without either
document holding the data. Size and digest together answer "is this the same message"
which is the question an archive is normally opened to answer.

### The last two fields must come from the REST pull, not from `gcloud`

**Measured 2026-09-01 against seven real dead-lettered messages.** An archive built from
`gcloud pubsub subscriptions pull --format=json` disagreed with the Pub/Sub REST `:pull`
response about the same messages — 792 bytes against 821, 878 against 907, 422 against 436 —
and one message's `data` field came back 557 characters long, which cannot be base64 under
any reading, since base64 length is always a multiple of four. The delta is systematic
rather than random.

So `gcloud`'s rendering of `message.data` is not the wire payload, and a size or digest
derived from it is wrong. It is wrong in the worst available way for this table: the archive
exists so a replayed message can be matched to its original, and a digest of the wrong bytes
fails that comparison **silently**, looking exactly like a genuine mismatch.

Attributes read through `gcloud` are unaffected, and the read-without-acking command above
stays as it is. For size and digest:

```bash
curl -s -X POST -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H 'Content-Type: application/json' -d '{"maxMessages":10}' \
  "https://pubsub.googleapis.com/v1/projects/$PROJECT_ID/subscriptions/traces-dlq-pull:pull"
```

Decode `message.data`, measure and hash it in memory, and keep neither. Leases mean one pull
rarely returns everything; poll until the ids stop being new rather than trusting a single
response — the first attempt at this archive reported five messages, then six, and the true
count was seven. Worked example: [`f2-dlq-archive-2026-09-01.md`](../evidence/f2-dlq-archive-2026-09-01.md).

**Why this rule is here and not in ADR-0006.** ADR-0006 places redaction
post-deserialize, pre-write. A dead-lettered message is *defined* by never having
reached that stage — it is in the queue because deserialization failed — so the
redaction boundary does not cover it and was never intended to. That is a gap in
coverage, not a defect in the ADR: the boundary is drawn correctly for the path it
describes, and this path is the one that leaves it. The rule above closes the gap at
the only other point where the bytes can escape, which is the archive.

The rule binds regardless of how harmless a specific message looks. A poison payload
constructed by this project carries no personal data by construction — and it is
archived under the same rule anyway, because an archive procedure that depends on
knowing the payload is safe has already read the payload.

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

## 5. The DoD 4 drill fixture

Written before the drill, per the F2 completion directive F2C-07, so the procedure is
reviewable before any message exists to triage. **Nothing in this section has been
executed.** Publishing is irreversible and send-shaped: it needs its own go-ahead.

### What the fixture is

A message published **directly to `traces`**, not through the collector. That is the
difference from the local end-to-end run, where the poison fixture travels through
`/v1/traces` like everything else and is accepted there before failing downstream.
Wave 4's drill targets the worker's deserialization failure specifically, so it skips
the hop that would otherwise have to be innocent for the test to mean anything.

The body is bytes the worker cannot deserialize. Either will do and the first is
preferable because its failure is unambiguous:

1. **Not gzip.** The contract says `content_encoding: gzip` (§3.2) and the worker
   inflates before it parses; ASCII text fails at the first byte with a gunzip error
   rather than somewhere inside a protobuf.
2. **Truncated protobuf.** Valid gzip wrapping a prefix of a real OTLP request.

Reuse `testdata/fixtures/claude-code/poison/request.pb` only if it is first confirmed
to fail *at the worker* rather than at the collector; it was built for the local path
and its guarantee is about that path.

### Attributes, which are the whole point

The message carries attributes that identify it in the DLQ **without opening the
payload** — which is what makes §1's archive rule practical rather than a constraint
to be worked around:

| Attribute | Value | Why |
| --- | --- | --- |
| `content_encoding` | `gzip` | the contract value; the drill tests the worker, not attribute validation |
| `source_dialect` | `claude-code` | hint only, and it keeps the message shaped like a real one |
| `api_key_id` | `drill` | not a real issued key id; the drill does not travel the authenticated path |
| `plumbline_drill` | `f2-dod4` | **the identifying attribute** — absent on every genuine message |
| `plumbline_drill_published_at` | RFC 3339, set at publish | pairs with the alert timestamp so the two are attributable |

`plumbline_drill` is what separates this exercise from an incident. A DLQ message
without it during Wave 4 is a real failure and belongs in the §2 triage, not in the
drill transcript.

### The procedure

1. Confirm the pre-drill depth is **0** and record it. If it is not, stop: the drill's
   evidence is not separable from whatever is already in the queue (directive F2C-13).
2. Record the time. Leave a clear gap after F2C-08's channel test so two notifications
   into the same inbox stay attributable.
3. Publish one message, with the attributes above.
4. Expect five delivery attempts, then arrival in `traces-dlq`. The interval is
   10s → 600s backoff, so this is not instant.
5. Pull **without** acking, per §3, and archive under §1's rule — metadata only.
6. Then the step most drills omit: send one **valid** delivery and confirm it succeeds.
   A subscription that dead-lettered a poison message and then quietly stopped working
   has not been shown to recover, and DoD 4 asks whether the path survived the failure,
   not only whether it caught it.

### What the drill does not prove

That the alert is *deliverable*. The alert firing shows the policy evaluated its
condition; that a human receives it is a separate claim, proven separately by the
channel test in F2C-08.2. A drill run against an undeliverable channel would look
identical from here.

## 6. What this runbook does not cover

- **Why** a message failed. That is the worker's logs and the poison-fixture tests,
  not this file.
- Bulk replay. There is no tooling for it in v0.1, and building some in the middle
  of an incident is how a replay loop gets written.
- The main push subscription's configuration — `traces-push`, in
  [`infra/terraform/pubsub.tf`](../../infra/terraform/pubsub.tf), with its reasoning
  in F2 decision log W3.2–W3.5. What belongs here is what to do with a message once
  it has arrived; why five delivery attempts rather than fifty belongs there.
