# DLQ archive — the failed first delivery, 2026-09-01

**Measured:** 2026-09-01 · **Source:** `traces-dlq-pull`, Pub/Sub REST `:pull`, read without acking
**Rule:** F2C-07 / W2.20 — metadata only. No payload bytes, raw or decoded, not one field.

These seven messages are the failed first delivery's remains (branch A,
[`f2-dod7b-first-delivery.md`](f2-dod7b-first-delivery.md)). They are **not** the drill's
poison fixture. Archived before draining, because draining is irreversible and these are the
only physical evidence that the dead-letter path carried a real failure.

| message_id | publish_time | attempts | bytes | sha256 |
| --- | --- | --- | --- | --- |
| `21634509354543198` | `2026-09-01T02:34:21Z` | 5 | 821 | `bd586a04238131a5997cae65d6f09c286ee75fc65c4328094b83845beb919cd5` |
| `21637115087194835` | `2026-09-01T02:34:23Z` | 5 | 849 | `5ab620169da792793e90f42526196cc71ec0cc4e9e4690125da0e73a9928e0ad` |
| `21641257305830290` | `2026-09-01T02:34:24Z` | 5 | 431 | `681691b1b7b6ad2b231b7dd403bfab4680036e5fba7c1576b07aaa51cc2819e3` |
| `21640076296202323` | `2026-09-01T02:34:27Z` | 5 | 907 | `7019320738b11fdbbd583136ffa539bd0a0a4b1037eb0e44e0dadf7ebb07a500` |
| `21641300423534899` | `2026-09-01T02:34:35Z` | 5 | 436 | `aa562c66e59f8d6ba7abfe6ed8cf50cebe7dcee5342582b981dd19a591fa12b2` |
| `21641244478731378` | `2026-09-01T02:34:36Z` | 5 | 423 | `2a46c523776d683df726c1a35b7b10c0b912d4463fcc6a57e543a7d6ca22e217` |
| `21639219023908774` | `2026-09-01T02:34:38Z` | 5 | 436 | `d3c6acdeb4a17abb8e325f24b9028c5b6916c07a97409ddec26acb3373bda9dc` |

## Attributes, identical across all seven but for the ids

```
CloudPubSubDeadLetterSourceDeliveryCount=5
CloudPubSubDeadLetterSourceSubscription=traces-push
CloudPubSubDeadLetterSourceSubscriptionProject=plumbline-19458
CloudPubSubDeadLetterSourceTopicPublishTime=2026-09-01T02:32:44.926+00:00
api_key_id=wave4-e2e
content_encoding=gzip
schema_url=https://opentelemetry.io/schemas/1.28.0
source_dialect=claude-code
```

`api_key_id=wave4-e2e` is the first key, whose plaintext was deleted before use — so these
messages also date the failure to the first attempt rather than to the retake.

## What the delivery count proves

Every message shows **5** attempts, which is `maxDeliveryAttempts` on `traces-push` and the
floor W3.3 settled. The policy was configured on 2026-08-21 and read back from the API on
2026-08-31; this is the first time it has been observed **executing**.

## A tooling finding: `gcloud`'s JSON payload is not the wire payload

This archive was first built from `gcloud pubsub subscriptions pull --format=json` and its
figures were wrong. The two sources disagree on the same messages:

| message_id | gcloud bytes | REST bytes | agree? |
| --- | --- | --- | --- |
| `21634509354543198` | 792 | 821 | no |
| `21640076296202323` | 878 | 907 | no |
| `21641300423534899` | 422 | 436 | no |
| `21641257305830290` | *not valid base64 at any padding* | 431 | no |

The delta is systematic rather than random. One message's `data` field came back 557
characters long, and base64 length is always a multiple of four — so that field cannot be
the encoded payload under any reading.

**Consequence for the runbook.** Attributes read through `gcloud` are fine, and that is what
`dead-letter.md` documents. Payload **size** and **SHA-256** must come from the REST `:pull`
response, because an archive exists to match a replayed message to its original — and a
digest of the wrong bytes cannot do that, silently.
