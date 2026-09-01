# F2C-05 — pre-arm flight check, Wave 4

**Measured:** 2026-09-01 · **Directive item:** F2C-05 (v1.7), Decision 17
**Repo commit at check time:** `b9168b18b080865e275866743936af62514fecfc`
**Plan read from:** CI run [`33460053493`](https://github.com/arslan-kursad/plumbline/actions/runs/33460053493), job `terraform plan (wif)`
**Nothing here is inherited from an earlier run** (spec §7.2 CN4).

Run immediately before dispatch, which is the only time it means anything: two of its three
checks read state that decays.

> **Correction, 2026-09-01, after the dispatch this document cleared.** Section 1 checked
> the wrong object and section 4's verdict was wrong because of it. The pin is
> `var.image_tag`, a value **in the repository** (`infra/terraform/variables.tf`); it was
> still `6a504b4` and bumping it is a reviewed pull request, by design. What section 1
> verified is that images exist for current `main` — necessary, and not the check.
> Wave 4's first dispatch (run `33460547748`) was refused by the plan job's Artifact
> Registry guard. Nothing was applied and no approval was requested. Recorded here rather
> than rewritten: W3.14.
>
> **The plan is no longer one resource.** Bumping `image_tag` necessarily updates both
> Cloud Run services, because the pin is what resolves their images. Measured 2026-09-01,
> both services are running `6a504b4` — the tag Artifact Registry has already collected;
> the revisions survive because Cloud Run holds a digest, not the tag. The re-planned diff
> is three in-place updates and no creations or destroys:
>
> ```
> # google_bigquery_table.spans_deduped   will be updated in-place
> # google_cloud_run_v2_service.collector will be updated in-place
> # google_cloud_run_v2_service.worker    will be updated in-place
> ```
>
> Not treated as a Class 3 scope escape: Wave 4 declares activities rather than a resource
> set (spec §Wave 4), all three resources are already Terraform-owned and were applied by
> earlier waves, and there is no alternative — the one-resource plan is unreachable because
> the guard refuses the collected tag. It is also the better outcome: DoD 7b's exam is
> served by current code rather than by an image whose tag no longer exists. The reviewer
> sees this diff at the approval gate, which is where it belongs.

## 1. Pin — re-derived, not confirmed

Decision 17 stops the directive from naming a SHA, because naming one is how the check
failed twice (A2.13, then again on 2026-08-31 when `6a504b4` had already been collected).
The pin is derived from current `main` at check time.

| Image | Tag `b9168b18…` |
| --- | --- |
| `plumbline/collector` | present |
| `plumbline/worker` | present |

The repository is `plumbline` and the second image is `worker`. `ingestion-worker` is the
Cloud Run **service** name; the directive asked for it as an image until Amendment 7.

## 2. IAM at apply — there is nothing to enumerate, and that is the finding

F2C-05 asks for every `setIamPolicy` call in the plan, each verified against the apply
identity by reading the API. The plan contains none.

```
# google_bigquery_table.spans_deduped will be updated in-place

Plan: 0 to add, 1 to change, 0 to destroy.
```

**Wave 4 was a one-resource apply at the time of this reading.** Its entire content was
#61's corrected view definition; after the pin bump it is three, per the correction above.
The pipeline it exercises — collector, worker, topics, subscriptions, dead-letter policy —
was applied by Waves 1 through 3 and was read live on 2026-08-31
([`f2-state-readout`](f2-state-readout-2026-08-31.md)). Zero IAM resources appear in the
change set; the 41 IAM addresses in the job log are refresh lines for resources that
already exist.

The single change needs `bigquery.tables.update`. Read from the IAM API rather than
assumed:

```
gcloud projects get-iam-policy plumbline-19458 \
  --flatten='bindings[].members' --filter='bindings.members:ci-deploy@' \
  --format='value(bindings.role)'
→ ... roles/bigquery.dataOwner ...

gcloud iam roles describe roles/bigquery.dataOwner
→ includes bigquery.tables.get, bigquery.tables.update, bigquery.tables.updateData
```

`ci-deploy@` holds it. **No grant is missing, and none is requested.**

## 3. What this does not say

It does not say the apply will succeed. Five of this phase's permission defects surfaced at
apply and none at review (W2.11), and the reason this check exists is that review is the
cheaper place to find the sixth. It says there is no sixth *of that kind* in this plan —
which is a narrow claim, because this plan changes one view.

It also does not make Wave 4 the moment the pipeline goes live. That already happened. What
Wave 4 unblocks is querying the views at all: under the deployed two-column window a
partition-filtered read is refused outright (#61, measured 2026-08-31), so DoD 3 cannot be
evidenced until this applies.

## 4. Verdict

~~**Clear to dispatch.**~~ **Withdrawn** — see the correction at the top. The check was
clear on IAM and on image *availability*, and silent on the pin that is actually applied.
Section 2's finding stands unchanged: the plan carries no `setIamPolicy` call and
`ci-deploy@` holds the one permission the single change needs.

The `gcp-production` approval remains Lane C and was never reached.
