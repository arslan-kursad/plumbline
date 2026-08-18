# ADR-0002 — Pub/Sub message contract & at-least-once delivery with downstream dedup

**Status:** Proposed · **Date:** 2026-08-18 · **Work package:** F0 / W2
**Architecture:** §2.2, §3.2, §3.3, §3.4, §4.1, §7, §8
**Supersedes:** — · **Superseded by:** —

## Context

Pub/Sub decouples the Go data plane from the .NET control plane. Two questions had to be
answered before either side existed: what exactly constitutes one message, and what
delivery guarantee downstream code is allowed to assume.

They are one decision, not two. Answering them separately is how systems end up with a
query layer written as if delivery were exactly-once while the transport is at-least-once
— a defect that surfaces only under a retry storm, months later, as quietly wrong
aggregate numbers. For a platform whose output is measurements, that failure mode is
worse than an outage.

Constraints in force: ADR-0001 forbids re-encoding the payload anywhere on the wire path;
topic-level retention is a paid feature and therefore unavailable; and no shared state may
be introduced for coordination (zero-cost invariant, §7).

## Decision

1. **One message = exactly one gzipped, binary OTLP `ExportTraceServiceRequest`.** No
   JSON encoding, no re-batching across export requests, no splitting one request across
   messages. The collector controls batch sizing so the compressed payload stays under
   the 10 MB push limit, working target ≤ 4 MiB; oversized batches are split at the
   collector before export, never truncated (§3.2).
2. **Four message attributes** carry provenance and audit metadata: `api_key_id`,
   `source_dialect` (hint only — worker detection is authoritative), `content_encoding`,
   `schema_url`. Attributes are metadata about the payload; they are never a second data
   path for content that belongs inside the spans.
3. **Delivery is at-least-once.** Pub/Sub exactly-once subscriptions are not used.
4. **Dedup is downstream and declared.** Duplicates land in BigQuery and are removed at
   query time on `(trace_id, span_id)`, keeping the latest `ingest_time`. The
   `spans_deduped` view encapsulates this; every consumer — Looker Studio, the eval
   engine, the SPA export — reads views, never the base table (§4.1).
5. **Write path matches transport:** Storage Write API default stream, which is itself
   at-least-once. No committed-stream / offset bookkeeping in v0.1.
6. **Poison messages are not silently dropped.** Main subscription max delivery attempts
   = 5, then `traces-dlq`, which has a pull subscription with no consumer and an alert on
   `num_undelivered_messages > 0`. Replay is a manual runbook step in v0.1 (§3.4).

## Alternatives considered

**A. Exactly-once end to end (Pub/Sub exactly-once subscriptions + BigQuery committed
streams with offsets).**
Rejected. It does not remove dedup, it relocates it and then hides it: exactly-once is
scoped to a subscription and does not survive a worker that crashes after a partial write
and is redelivered, so the query layer still needs the `(trace_id, span_id)` invariant to
be correct. The project would pay regional restrictions, ack-deadline handling, and
stream-offset bookkeeping to arrive at the same downstream requirement with a weaker
reason to enforce it. Under a free tier the benefit is zero and the cost is a false sense
of guarantee.

**B. Dedup at write time in the worker (read-before-write, or staging table + `MERGE`).**
Rejected. A read-before-write costs a query per batch, billed against the 2 TiB/month
scan tier and paid in latency; the Storage Write API is append-only, so `MERGE` implies
staging tables and a scheduled reconciliation job. Query-time dedup over a clustered
column costs approximately nothing and is verifiable by reading one view definition.

**C. Multiple export requests per message (collector re-batches to reduce message count).**
Rejected. Merging export requests requires decoding and re-encoding the payload, which
ADR-0001 forbids outright. It would also destroy the 1:1 correspondence between an SDK
export and a message, which is precisely what makes a dead-lettered message attributable
to an emitter, a key, and a time window.

**D. Topic-level retention as a replay safety net.**
Rejected: paid feature, and it duplicates protection that subscription-level unacked
retention (7 days, free) already provides for the only case that matters. These are two
distinct mechanisms and Terraform must not generalize one onto the other (§2.2).

**E. DLQ with an automatic replay consumer.**
Deferred rather than rejected. Automatic replay of a message that failed five times is a
loop unless the defect is fixed first, and the defect is by definition unknown at that
moment. A consumer becomes worthwhile once failure classes are known — F3 at the earliest,
and as a spec change.

## Consequences

**Positive**

- Downstream code carries exactly one stated assumption, and it is the weakest available:
  duplicates are possible, ordering is not guaranteed. Nothing needs redesigning the first
  time a retry storm happens.
- The 1:1 message ↔ export request mapping makes every dead-lettered message directly
  attributable to an emitter, an API key, and a time window, with no correlation work.
- Dedup lives in one view definition rather than in every consumer, so a new consumer
  cannot forget it by omission — only by explicitly bypassing it.

**Negative / accepted costs**

- Consumers *must* go through views. A query against the `spans` base table is a
  correctness bug, not a style preference, and nothing mechanically prevents one in v0.1:
  the Looker Studio connection and the eval engine's SQL are review-enforced only. This
  is a reporting gap with no detecting control, and it is named here rather than assumed
  away.
- Duplicate rows consume storage against the 10 GiB free tier. The volume is bounded by
  retry behaviour but unmeasured until F2. If it becomes material, the answer is a
  scheduled dedup `MERGE` on cold partitions — not a change to delivery semantics.
- Dedup assumes `(trace_id, span_id)` uniquely identifies a logical span. An emitter that
  reuses span IDs across exports would have distinct spans silently collapsed. Not
  observed in the three v0.1 dialects; this assumption is re-checked whenever a dialect is
  added (§5).
- Manual DLQ replay means a poisoned batch stays unavailable until a human acts. Accepted:
  the alternative is losing it quietly, which this project does not permit.

## Enforcement

- **Terraform owns the topology** (§8): dead-letter policy with max delivery attempts = 5,
  and message retention disabled on every topic. Hand-created or drifted configuration is
  a bug by definition.
- **Alert on `traces-dlq` `num_undelivered_messages > 0`** — this is the control that
  makes "no silent degradation" real on the transport. It reports; nothing prevents a
  poison message from being produced.
- **Collector batch-size behaviour** is covered by tests, per the §7 guardrail row
  (collector code + golden tests).
- **View discipline** (`spans_deduped`, `spans_real`) is review-enforced. See ADR-0004 for
  why the prevent/report distinction is recorded per invariant rather than assumed.

## References

- `docs/architecture.md` §2.2, §3.2, §3.3, §3.4, §4.1, §7, §8, §9.
- ADR-0001 — payload may not be re-encoded on the wire path.
- ADR-0004 — control taxonomy: which invariants are prevented and which only reported.
