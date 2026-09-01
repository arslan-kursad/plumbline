# DoD 4 — the dead-letter drill

**Fired:** 2026-09-01 · **Run:** `w4-drill` · **Directive items:** F2C-13, F2C-14
**Go-ahead:** given per §4 — the third and last of F2's send-shaped actions
**Separation:** Decision 14, enforced by the harness against the recorded channel test

## 1. Preconditions, checked by the tool rather than remembered

```
armed; separation satisfied (earliest was 05:18:39Z); depth 0
```

Three gates, all mechanical: `PLUMBLINE_E2E_DRILL_ARMED=yes` on top of the cloud target,
thirty minutes since the F2C-08.2 channel test at `04:48:39Z`, and a drained queue. A drill
starting from a non-empty queue cannot attribute what it finds there to itself, and the
seven messages that were in it are archived separately
([`f2-dlq-archive`](f2-dlq-archive-2026-09-01.md)).

## 2. Published

| | |
| --- | --- |
| fixture | `testdata/fixtures/claude-code/poison/request.pb` |
| size | 96 bytes — a protobuf truncated mid-field, unrecoverable by construction |
| sha256 | `7597adc77eabc3a9d15b9152f1849e9021046d0be1b3883ec621df07bbd22cbc` |
| published at | `2026-09-01T05:23:14Z` |
| publish message id | `21442356616232809` |

Published **straight to `traces`**, not through the collector (W2.20): the payload cannot
carry attributes because it cannot be parsed, so the markers have to come from the
publisher. Over the REST API with base64, not as a command argument — the bytes are not
valid UTF-8 and a shell path would have changed them.

## 3. Triage archive — F2C-07's enumeration, and nothing else

| Field | Value |
| --- | --- |
| `message_id` | `21642212302575522` |
| `publish_time` (onto `traces-dlq`) | `2026-09-01T05:25:02Z` |
| delivery attempt count | **5** |
| `plumbline_drill` | `f2-dod4` |
| `plumbline_drill_published_at` | `2026-09-01T05:23:14Z` |
| payload size | 96 bytes |
| payload SHA-256 | `7597adc77eabc3a9d15b9152f1849e9021046d0be1b3883ec621df07bbd22cbc` |

Read without acking. No payload bytes are recorded here, decoded or otherwise (W2.20).

**The digest matches what was published, byte for byte.** That is the assertion the archive
exists to make and it is not decorative: had the fixture been passed through a shell
argument it would have been re-encoded, and the drill would have dead-lettered a
*differently* corrupted message while reading exactly like this document.

**Five attempts is `maxDeliveryAttempts` on `traces-push`** — W3.3's floor, observed
executing against a message published for the purpose rather than against an accident.

## 4. The alert

| | |
| --- | --- |
| policy | *traces-dlq has undelivered messages*, enabled |
| condition | `num_undelivered_messages` `COMPARISON_GT` 0, duration 60s |
| bound channel | `17645137777150770481`, email, proven to deliver on 2026-09-01 |
| metric observed | 0 → **1** at `05:28:00Z` |

The condition is met on the metric the policy watches. **Arrival of the alert email is
confirmed by the person holding the inbox**, as it was for the channel test — and this time
the notification carries no marker of ours, so attribution rests on the thirty-minute
separation from `04:48:39Z` and on this document's timestamps.

## 5. What the drill did not prove

- **Not replay.** The message is still in the queue. Replay is manual in v0.1
  (architecture §3.4) and is not part of DoD 4.
- **Not that a real poison message would look like this.** This one was constructed and
  published deliberately, with markers a genuine failure would not carry. The seven
  dead-letters from the failed first delivery are the accidental case, and they are archived
  separately — worth reading beside this one for exactly that contrast.
- **Not that the alert is timely.** The depth metric is a sampled gauge and lags by minutes
  (W3.22); the gap between the dead-letter at `05:25:02Z` and the metric moving at
  `05:28:00Z` is the sampler, not the pipeline.
