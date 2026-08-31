# State readout — live GCP state, read in one pass

**Measured:** 2026-08-31T17:24:44Z · **Directive item:** Decision 5 (F2 completion
directive v1.7) · **Repo commit at read time:** `9970374`
**Nothing here is inherited from an earlier run** (spec §7.2 CN4). Every value below came
from the API on the timestamp above, against `plumbline-19458`.

Produced by [`scripts/state-readout.sh`](../../scripts/state-readout.sh). The tool is the
evidence, not this file: it records the command beside each reading, so any line here can
be re-derived by re-running it. What this file adds is the reading of the readings.

## What this does not prove

It is a snapshot of configuration and depth. It says nothing about whether the pipeline
*works* — no message has been published to `traces`, DoD 7b is unexercised, and a
correctly configured dead-letter policy is not a demonstrated one. Those are F2C-11 and
F2C-13/14.

## 1. Cloud Run — inside the guardrails

| Service | region | min | max | cpu | memory | ingress |
| --- | --- | --- | --- | --- | --- | --- |
| `collector` | `us-central1` | 0 | 2 | 1 | 512Mi | `all` |
| `ingestion-worker` | `us-central1` | 0 | 2 | 1 | 512Mi | `internal` |
| `billing-killswitch` | `us-central1` | unset | 1 | 0.1666 | 256Mi | `internal` |

The two pipeline services hold `CLAUDE.md`'s invariants — `min_instances = 0`,
`max_instances <= 2`, region `us-central1`. `billing-killswitch` carries no `minScale`
annotation at all, which is the same posture by absence rather than by value; it is
recorded as unset rather than as 0, because a field that is not there and a field that
reads 0 are different facts.

## 2. Pub/Sub — the dead-letter path is configured

| Property | Value |
| --- | --- |
| `traces-push` dead-letter topic | `projects/plumbline-19458/topics/traces-dlq` |
| `traces-push` max delivery attempts | `5` |
| `traces-push` ack deadline | `60s` |
| `traces-push` retry backoff | `10s` → `600s` |
| `traces-push` OIDC token on push config | present |
| `traces-dlq-pull` dead-letter policy | none — correct; a DLQ that dead-letters is a loop |

Five attempts is the floor W3.3 settled, read back here rather than carried from it.

## 3. Undelivered depth — zero, and that is a precondition rather than a result

| Subscription | `num_undelivered_messages` |
| --- | --- |
| `traces-push` | 0 |
| `traces-dlq-pull` | 0 |

Read from Monitoring v3, because `gcloud alpha monitoring` is denied and the GA surface
carries no time-series read. Stage 3 step 12 asks for DLQ depth 0 before the drill; this
is that reading taken early, and it will need re-taking after first delivery — a zero
today does not survive a delivery.

## 4. Artifact Registry — the pin, and why it is no longer written down

Nine tags on each of `collector` and `worker`, identical sets, current `main`
(`99703747`) present. **`6a504b4` is absent from both** — the SHA the directive asked
F2C-05 to confirm until Amendment 7. This is A2.13 recurring, and it is why Decision 17
re-derives the pin at dispatch instead of carrying one.

The repository holds one repository, `plumbline`, and two images: `collector` and
`worker`. The directive had been asking for `ingestion-worker`, which is the Cloud Run
service name and not an image name.

## 5. BigQuery — the view is still the two-column form, and #61 is still open

Deployed `spans_deduped`, read from the API:

```
ROW_NUMBER() OVER (
  PARTITION BY trace_id, span_id
  ORDER BY ingest_time DESC
)
```

The repo's `analytics/sql/002_spans_deduped.sql` carries the three-column window. #82
merged the fix and did not deploy it, exactly as the closure note says.

**The row-count reading fails, and the failure is the evidence.** Decision 5's last
reading counts rows by `synthetic` and by run id over an explicit partition window,
against `spans_deduped`. Verbatim:

```
Error in query string: Error processing job
'plumbline-19458:bqjob_r7d8fe20da1055997_000001a058d76f86_1': Cannot query over
table 'plumbline-19458.plumbline.spans' without a filter over column(s)
'start_time' that can be used for partition elimination
```

This is #61 measured live against the cloud view for the first time. The cause is the one
`002_spans_deduped.sql` already states: a predicate may only be pushed below a window
function when it references the columns the window partitions on, so with the two-column
window the outer `start_time` filter cannot reach the inner scan of `spans`, and
`require_partition_filter` refuses the query. **The views cannot be queried at all today.**

The reading is left failing rather than routed around. Querying the base table instead
would return a number, and it would answer a different question: DoD 3 is a claim about
rows arriving *through the views*. This makes the reading #61's closure probe — it
succeeding against the cloud view is what Stage 3 step 11 asks for.

## 6. What the tool cannot read, named

| Reading | Blocked by | Lane | Needed by |
| --- | --- | --- | --- |
| Gross period cost | `Bash(gcloud billing:*)` in `.claude/settings.json`, correctly | C | Decision 16, the two-day spend escape hatch |

This is the only one. Every other reading Decision 5 enumerates was taken from Lane A,
which is the measurement that retired the proposed CI workflow.

## 7. Redaction

The artefact is redacted before it is emitted, and the tool refuses to print anything if a
sensitive form survives. The rule is the domain shape: service accounts pass because they
name a role rather than a person and are already throughout `docs/`; every other address
becomes `<redacted-user-principal>`. The shape rules are imported from
`scripts/ci/scrub_plan.py` rather than restated, so a second copy cannot drift from the
first.

The project IAM policy is read in full and is the reason this matters — it carries the
maintainer's own account, which is not in this repository and does not enter it here.
