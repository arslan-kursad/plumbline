# Runbook — Wave 4's first push delivery

**Status:** written 2026-08-26, ahead of the delivery it describes. **Nothing in
this file has been executed.** Wave 3 wired the push path and deliberately did not
exercise it (F2 DoD 7b): a published Pub/Sub message cannot be unpublished, it
would be a mutation outside the gated path, and a message in the dead-letter queue
before Wave 4 would consume the triage rehearsal DoD 4 specifies against Wave 4's
own poison fixture.

## Why a runbook for one message

The first delivery is a **one-shot observation**. It answers the question W2.2
recorded as unanswerable by any test — whether the worker's OIDC validator accepts
a real Google-signed token, which nothing in this repository can mint — and its
failure modes have opposite signatures that are easy to confuse in the moment.
Three of the four end with messages in `traces-dlq`, so "the DLQ filled up" does
not identify which one happened.

Deciding what to look at while looking at it is how a silent failure gets recorded
as a success.

## 0. What is sent, and the one attribute that is not optional

The payload is the constructed corpus (D2), and **every resource in it carries
`synthetic=true`** (F2 completion directive, Decision 2). This is not a labelling
nicety and it is not reversible after the fact.

Without the flag the rows land in `spans_real`, which is the view F4's 14-day
real-source window reads. F4 has no cheap way to remove them afterwards: they are
indistinguishable from real spans by every other column, because being constructed is
not a property the data carries anywhere else. The flag is free now and expensive
later, and "later" is the point at which the contamination is discovered rather than
the point at which it happened.

The gain is that DoD 3 gets a stronger acceptance than it would otherwise have had.
Because the rows are flagged, this delivery becomes the **first live test of the
walled-off-synthetic invariant** — see §4.

## 1. Pre-flight — read the live configuration from the API

Not from the plan, and not from `main`. The plan says what Terraform intended; the
API says what exists.

```bash
gcloud pubsub subscriptions describe traces-push --project "$PROJECT_ID" --format=json
```

Confirm, one at a time:

| Field | Expected | Why it is on this list |
| --- | --- | --- |
| `pushConfig.oidcToken.audience` | `plumbline-ingestion-worker` | Must equal the worker's `PLUMBLINE_PUSH_OIDC_AUDIENCE`. A mismatch refuses every delivery with a correct-looking configuration on both sides |
| `pushConfig.oidcToken.serviceAccountEmail` | `pubsub-push@…` | Must equal the worker's `PLUMBLINE_PUSH_OIDC_SERVICE_ACCOUNT`. The worker checks the issuer-verified email, not just that a Google-signed token exists |
| `pushConfig.pushEndpoint` | the worker URI **plus `/push`** | The path is the half that fails quietly — see branch B |
| `ackDeadlineSeconds` | 60 | Matches the worker's request timeout; shorter redelivers work in progress |
| `deadLetterPolicy.maxDeliveryAttempts` | 5 | |
| `deadLetterPolicy.deadLetterTopic` | `…/topics/traces-dlq` | |

Then the two grants **whose absence is invisible to plan, apply and drift**, and
whose effect is that the path which catches everything else never runs:

```bash
gcloud pubsub topics get-iam-policy traces-dlq --project "$PROJECT_ID"
```

```bash
gcloud pubsub subscriptions get-iam-policy traces-push --project "$PROJECT_ID"
```

The Pub/Sub service agent — `service-<PROJECT_NUMBER>@gcp-sa-pubsub.iam.gserviceaccount.com`,
not any identity this project created — must hold `roles/pubsub.publisher` on the
**topic** and `roles/pubsub.subscriber` on the **subscription**. It holds neither
by default, and `roles/pubsub.serviceAgent` carries neither permission (checked
with `gcloud iam roles describe`, W3.5). Without them the subscription still
applies cleanly, the plan is clean, drift is clean, and dead-lettering simply never
happens: messages retry past the attempt limit and stay in the backlog while the
depth alert reports nothing, because nothing arrives.

And the invoker, which is the outer of the two authentication checks:

```bash
gcloud run services get-iam-policy ingestion-worker --region us-central1 --project "$PROJECT_ID"
```

Exactly one member, `pubsub-push@`. **No `allUsers`** — that member *is*
"unauthenticated invocations enabled"; there is no separate switch.

## 2. Failure signatures — a decision tree

Send one message, then read in this order. Each branch names what to look at
first, not just what went wrong.

### A. Wrong audience or wrong push identity

**Signature:** loud, immediate, uniform. Every delivery refused; the worker logs a
validation failure naming the audience or the issuer-verified email. Cloud Run
request logs show the request **reaching the container** and the worker answering
4xx.

**Look at:** the worker's logs first, then the two env vars against the
subscription's `oidcToken` block. This is the one branch where the application
tells you the answer directly.

### B. Wrong push path

**Signature:** silent. Cloud Run returns 404, Pub/Sub counts a failed delivery like
any other, five attempts, then `traces-dlq`. The DLQ fills with **healthy
messages** and the depth alert reports what looks like a poison-message incident.

**Look at:** the request log's response body, not just the status. `404 page not
found` is Go's `http.NotFound`, so the request reached the worker and the mux had
no handler — that is a path mismatch. Then compare `pushConfig.pushEndpoint`
against the worker's `PLUMBLINE_PUSH_PATH`; both are built from one Terraform
local (`local.push_path`, W3.2), so a divergence means someone edited one side.

### C. Platform path interception — the same 404, and not the worker's fault

**Signature:** identical to branch B from the outside. The difference is the
witness: a **styled HTML 404 from Google's edge** never reached your code, while
`404 page not found` did.

This is not hypothetical. On the collector, the exact path `/healthz` is
intercepted at the Cloud Run layer and never reaches the container, while
`/health`, `/healthz/`, `/` and `/v1/traces` all do. The cause is unknown and
recorded as unknown — [`collector-endpoints.md`](collector-endpoints.md).

**Rule this out before blaming the endpoint configuration.** Curl the worker's
push path directly and read the body, not the status code. If the body is Google's
page, no configuration in this repository is wrong and the fix is not in
`pubsub.tf`.

### D. Worker exception after a valid token

**Signature:** the token was accepted — the worker's success log line for
validation appears — and processing then fails 5xx. Retried with backoff
(10s → 600s), five attempts, then `traces-dlq`.

**Look at:** the worker's logs for the deserialization or write error. This is the
branch where the DLQ is doing its job and the message genuinely is the problem.

**This branch also has the one signature that is genuinely good news for DoD 7b:**
the validator accepted a real Google-signed token, which is the property Wave 3
could not establish.

## 3. Success signature

Three things, in order, and all three are needed:

1. **The worker's validation log line for an accepted token.** This is DoD 7b's
   first half and the reason this delivery matters more than the row it produces.
2. **The ack** — the subscription's backlog returns to zero and
   `num_undelivered_messages` stays at zero.
3. **The row** — §4.

A row without (1) would mean the row arrived some other way; (1) without (3) means
the transport works and the write path does not. Record all three.

## 4. Verification — the base table only

**Query `plumbline.spans` directly, with an explicit `start_time` partition
filter. Do not verify through `spans_deduped` or `spans_real`.**

The views are not the subject of this exercise, and reading through them would let
a view defect and a transport defect mask each other — the views have their own
open history (#61, #82) and a failure there would look like a delivery that never
landed.

```sql
SELECT trace_id, span_id, start_time, synthetic, ingest_time
FROM `PROJECT.plumbline.spans`
WHERE start_time >= TIMESTAMP('YYYY-MM-DD')
ORDER BY ingest_time DESC
LIMIT 20
```

The partition filter is not optional: the table carries
`require_partition_filter = true` and refuses a query without one — which is a
live guardrail, not a formality (#82 confirmed it fires even on an empty table).

### The dedup premise check

Wave 4 is the **first moment real data can test the premise the dedup design rests
on**. Run it here, and record the result whether it passes or not.

```sql
SELECT trace_id, span_id, COUNT(DISTINCT start_time) AS distinct_start_times
FROM `PROJECT.plumbline.spans`
WHERE start_time >= TIMESTAMP('YYYY-MM-DD')
GROUP BY trace_id, span_id
HAVING distinct_start_times > 1
```

**Every pair must have exactly one `start_time`**, so this query must return no
rows.

The premise is that duplicates are redeliveries of identical OTLP bytes, which
therefore produce an identical `start_time`. It has a concrete failure mechanism
rather than a hypothetical one: OTLP carries nanoseconds and BigQuery `TIMESTAMP`
holds microseconds, so the write path narrows lossily, and two deliveries
processed by worker revisions that rounded differently would land 1 µs apart and
stop deduplicating. **A DLQ replay after a deploy is exactly that scenario**,
which makes this runbook's own §5 the most likely way to trigger it.

Where the premise breaks, the design retains both rows rather than dropping one —
visible rather than silent — which is why this query is a check and not an alarm.

**The record this belongs to is [ADR-0007](../adr/ADR-0007-canonical-dedup-views.md)
(#61, #82).** Its status is the ADR index's to state (architecture §10) and is
deliberately not repeated here: a fact kept in two places is a fact one of which
will be stale, and the one that goes stale is always the copy.

What this section does depend on is the *shape* of the views, and that is why it
reads the base table regardless: under the two-column dedup window the views are
unqueryable against a partition-filtered table (#61), so verifying through them
would confuse a view defect with a delivery that never landed.

### The views come later, and each one proves a different claim

Exercise `spans_deduped` and `spans_real` as a **separate, later step**, after the
premise check passes. Which view carries which claim is stated here rather than left
to be worked out at the keyboard, because they are not interchangeable and reading
the wrong one would look like a pass:

| Claim | View | Query shape | What a failure means |
| --- | --- | --- | --- |
| **DoD 3** — the delivered spans are present and correct through the canonical view | `spans_deduped` | partition-filtered read; row count recorded **alongside the base-table count** | either the delivery or the dedup window; the base-table count separates them |
| **The walled-off-synthetic invariant** — flagged rows are excluded from the real-source view | `spans_real` | the same partition filter; assert the delivered `trace_id`s are **absent** | the `synthetic` flag did not survive the write path, and F4's window is contaminated the moment it opens |

The second row is an **exclusion** assertion, and that is the whole of its content: a
`spans_real` query returning the delivered spans is a failure, not a success, and it
is the one result in this runbook where rows arriving is the bad outcome. Anyone
reading down the page looking for row counts will get this backwards unless it is
written here.

Neither claim is marked from the fact that the apply succeeded, and neither is marked
from the other. `spans_deduped` returning rows says nothing about whether `spans_real`
excludes them — the views are stacked, so a defect in the flag shows up only in the
view that is supposed to filter on it.

## 5. Dead-letter triage

Full procedure: [`dead-letter.md`](dead-letter.md). Two things specific to a first
delivery:

**Read without acking.**

```bash
gcloud pubsub subscriptions pull traces-dlq-pull --project "$PROJECT_ID" --limit 1 --format='value(message.attributes)'
```

`--auto-ack` is deliberately absent: acknowledging removes the message and the
seven-day retention window is what stands between you and losing the evidence.
Attributes before content, always — they identify the failure without decoding
anything, and the payload carries unredacted personal data because redaction
happens in the worker, after the stage that failed (ADR-0006).

**Distinguish a poison message from a misconfiguration, which is the whole point
of triaging a first delivery:**

- A **misconfiguration** dead-letters *everything*, uniformly, starting with the
  very first message. Branches A, B and C all look like this.
- A **poison message** dead-letters *that message* while others succeed.

So: if the DLQ depth equals the number of messages sent, stop reading payloads and
go back to §2 — nothing is wrong with the messages. A queue that filled all at
once is a transport failure until proven otherwise.

**Replay is the preferred resolution** and it is manual in v0.1 (architecture
§3.4): a replayed message re-enters at the collector's output and therefore passes
through the redaction stage, while anything extracted by hand does not. Replay only
after the cause is fixed — a replay into an unfixed worker dead-letters again five
deliveries later. And note the interaction with §4: a replay after a redeploy is
the exact scenario the dedup premise check is written for.
