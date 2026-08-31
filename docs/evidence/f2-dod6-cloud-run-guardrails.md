# DoD 6 — Cloud Run guardrails: state and control

**Measured:** 2026-08-31 · **Directive item:** F2C-04b (F2 completion directive v1.1)
**Nothing here is inherited from an earlier run** (spec §7.2 CN4). Both readings were
taken on the date above, against `plumbline-19458`.

DoD 6 makes two claims that had been carried by one piece of evidence:

1. the deployed services are inside the guardrails, and
2. the plan-diff guard actually evaluates them.

A plan-derived reading cannot carry (1) — it says what Terraform intended — and a plan
with no Cloud Run delta cannot carry (2), because there is no attribute to check. So the
two are measured separately and by different means.

## 1. State — read from the API, not from a plan

`gcloud run services describe <svc> --region us-central1 --format=json`, fields taken
from the returned resource:

| Service | region | min | max | cpu | memory | ingress |
| --- | --- | --- | --- | --- | --- | --- |
| `collector` | `us-central1` | 0 | 2 | 1 | 512Mi | `all` |
| `ingestion-worker` | `us-central1` | 0 | 2 | 1 | 512Mi | `internal` |

Against the invariants in `CLAUDE.md` and architecture §7 — `min_instances = 0`,
`max_instances <= 2`, region `us-central1`, smallest instance size — both services hold.
The ingress values are the ones the plan guard's posture map requires: `collector` public,
`ingestion-worker` internal only.

**`analytics-api` does not exist.** The directive lists it among the three services to
read; `gcloud run services describe analytics-api` returns
`Cannot find service [analytics-api]`. It is F3's service and architecture §7 already
records that its first pull request will be red by design, both per-service assertions
denying a service absent from their map. Recorded here rather than skipped, because an
unread row and an absent service are different facts.

## 2. Control — the guard rejects, demonstrated

A guard that has never refused anything is an unproven control. The same mutation
technique that turned F2C-01 from *a test exists* into *the test discriminates* was
applied here.

`infra/terraform/cloudrun.tf` was changed to `max_instance_count = 3` on a probe branch,
CI was dispatched, and the plan job failed. Verbatim:

```
plan guard: asserted
  google_cloud_run_v2_service.collector: min_instance_count=0, max_instance_count=3
  google_cloud_run_v2_service.collector: ingress=INGRESS_TRAFFIC_ALL
plan guard: 1 violation(s)
  google_cloud_run_v2_service.collector: max_instance_count is 3, must be set and at most 2
```

Run `33390722393`, job `terraform plan (wif)`, exit code 1. The probe branch
`probe/guard-discriminates` was **never merged, never applied**, and was deleted after
the run; the plan job is read-only and no `apply` was involved.

The first two lines matter as much as the third: `plan guard: asserted` names the
attributes it read, so the rejection is attributable to evaluation rather than to the job
falling over for some other reason.

## 3. What the earlier reading meant

On run `33389628924` (#82) the guard printed
`plan guard: nothing in this plan carries a checked attribute`. That plan touched only a
BigQuery view, so no Cloud Run resource appeared in it. The line is the guard behaving
correctly on a plan with nothing in scope — not a gap, and not evidence of evaluation
either. It is the reason DoD 6's control claim needed §2 above rather than a sentence
quoting a clean plan.
