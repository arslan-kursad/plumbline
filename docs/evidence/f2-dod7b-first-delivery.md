# DoD 7b — first push delivery: exercised, and it failed at branch A

**Measured:** 2026-09-01 · **Directive item:** F2C-11, Stage 3 step 10
**Outcome:** the exam was taken. A real Google-signed token was minted and **refused by
Cloud Run before the worker saw it.** Per the directive, a failed exam closes on *the error
tree branch named*, not on a retry: this is
[`wave4-first-delivery.md`](../runbooks/wave4-first-delivery.md) **branch A — wrong
audience or wrong push identity.**

## Timeline, from logs

| Time (UTC) | Event | Source |
| --- | --- | --- |
| 02:32:33 | message published to `traces` | DLQ attribute `…SourceTopicPublishTime` |
| 02:32:44 – 02:33:03 | five payloads accepted by the collector, `export accepted`, HTTP 200 | Cloud Run request log |
| 02:33:48 – 02:34:11 | push delivery refused: *"The request was not authorized to invoke this service. The access token could not be verified."* | `ingestion-worker` logs |
| 02:34:23 | dead-lettered after five attempts | `traces-dlq-pull` |

## The cause, measured rather than reasoned

| Reading | Value |
| --- | --- |
| subscription push identity | `pubsub-push@plumbline-19458.iam.gserviceaccount.com` |
| subscription OIDC audience | `plumbline-ingestion-worker` |
| worker `roles/run.invoker` | held by `pubsub-push@` — **correct** |
| worker ingress | `internal` — correct, and not the cause |
| worker `run.googleapis.com/custom-audiences` | **ABSENT** |

**Two audience checks exist and only the second was configured.** Cloud Run authenticates
the request itself, before the container, and validates the token's `aud` against the
service URL unless the service declares custom audiences. The worker declares none, so a
token carrying `plumbline-ingestion-worker` is refused at the platform. The worker's *own*
validator checks the same value from its `PUSH_OIDC_AUDIENCE` environment variable — and
never ran, because the request never arrived.

The IAM binding, the push identity, the endpoint path and the ingress posture are all
correct. Nothing in the Terraform plan is wrong. What is missing is a platform contract
that no plan expresses.

## Why review could not have caught this, and 7a could not either

Wave 3 established the push transport and **applied cleanly on the first attempt** — W3.8
recorded that as the first time in the phase a permission did not announce itself at apply.
That clean apply is exactly what this defect looks like from the inside: the subscription
exists, the binding exists, the audience matches the worker's expectation. Every artefact
agrees with every other artefact.

**This is the argument for splitting DoD 7 into 7a and 7b, cashed out.** "Push transport
established" was true. "Push transport exercised" was false, and only a real delivery could
tell them apart. It is the phase's sixth permission-shaped defect and the first that a plan
reading could not have found.

## Side effects, recorded rather than tidied away

- **The DLQ is no longer empty**, and what is in it is not the poison fixture. The drill
  (F2C-13/14, DoD 4) requires a drained queue and unambiguous attribution, so it is blocked
  until these are drained.
- **The dead-letter path is now proven working**, which was not the intent and is worth
  keeping: five delivery attempts — W3.3's floor, live for the first time — then
  dead-lettered with attributes intact (`api_key_id=wave4-e2e`, `source_dialect=claude-code`,
  `content_encoding=gzip`, `…SourceDeliveryCount=5`). Read without acking, per the runbook.
- **`plumbline.spans` holds zero rows.** Nothing normalized, so DoD 3 is untouched and
  still open.
- **Two API keys are now orphaned.** `wave4-e2e` had its plaintext deleted before use;
  `wave4-e2e-2` was shredded after the failed run. Both need revoking per `api-keys.md` §4.

## The fix

`custom_audiences = [local.push_oidc_audience]` on the worker service. It requires an
apply, and therefore a `gcp-production` approval — the exam cannot be retaken until then.
