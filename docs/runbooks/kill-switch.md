# Runbook — billing kill-switch

**Status:** configuration delivered (F0 W4/W5); **live-fire not yet executed**.
F0 acceptance criterion 7 stays open until §4 of this runbook is filled with
observed evidence.

The chain, its rationale, and why it is deliberately the *last* control are in
[ADR-0004](../adr/ADR-0004-zero-cost-guardrails-kill-switch.md) §2 and §5.
Configuration: [`infra/terraform/killswitch.tf`](../../infra/terraform/killswitch.tf),
function source: [`infra/functions/billing-killswitch/`](../../infra/functions/billing-killswitch/).

```
budget (every cost update) --> Pub/Sub topic billing-alerts --> Cloud Function
      --> projects.updateBillingInfo with an empty billing account
```

## 1. What actually triggers it

The budget threshold is **not** the trigger. The budget publishes a notification
to `billing-alerts` on every cost update (roughly every 20–30 minutes) via
`all_updates_rule`, and the function detaches billing whenever the reported
`costAmount` is strictly greater than zero. This is what "alert at any spend
above $0" (F0 spec W4, ADR-0004 §5) means in an API that has no zero threshold.

Consequences, stated rather than discovered later:

- Cost reporting is not instantaneous. Google's own documentation describes
  budget data as delayed; the window between the first billable byte and the
  notification carrying it is real and is not controlled by this project. The
  kill-switch bounds the loss, it does not make it zero.
- Credits are excluded from the budget filter (`EXCLUDE_ALL_CREDITS`). A free
  trial credit must not mask spend: the project's claim is $0.00 gross.
- A cost update below the smallest reported amount is not visible to the
  function. In practice the first non-zero report fires it.

## 2. Human prerequisites (F0 spec W4, human-only)

1. Create the GCP project and link a billing account.
2. Hold **Billing Account Administrator** on that billing account — the budget is
   a billing-account-level resource — and Owner (or equivalent) on the project.
3. Enable the two APIs Terraform itself needs before it can enable anything
   else — on a fresh project the first plan fails without them, and the error
   reads like a bug in the configuration:

   ```bash
   gcloud services enable cloudresourcemanager.googleapis.com serviceusage.googleapis.com \
     --project "$PROJECT_ID"
   ```

4. Run `infra/terraform/bootstrap`, then the root module
   (see [`infra/terraform/README.md`](../../infra/terraform/README.md)).
5. Before the first apply, confirm the pinned function runtime still exists:
   `gcloud functions runtimes list --region us-central1`. The value is
   `var.killswitch_runtime` and is coupled to the function's `go.mod`.

## 3. Live-fire procedure (mandatory before F0 closes)

The test publishes a synthetic budget notification and observes billing detach.
It is a real detach, not a simulation — an untested kill-switch is a comfort
object (ADR-0004 §5).

```bash
PROJECT_ID=...        # the project under test
BILLING_ACCOUNT=...   # 012345-6789AB-CDEF01, needed to re-attach afterwards

# 0. Record the starting state.
gcloud beta billing projects describe "$PROJECT_ID"

# 1. Publish a synthetic notification carrying non-zero cost.
gcloud pubsub topics publish billing-alerts \
  --project "$PROJECT_ID" \
  --message '{"budgetDisplayName":"plumbline zero-spend","alertThresholdExceeded":1.0,"costAmount":0.01,"budgetAmount":1.0,"currencyCode":"USD","costIntervalStart":"LIVE-FIRE"}'

# 2. Watch the function decide.
gcloud functions logs read billing-killswitch \
  --project "$PROJECT_ID" --region us-central1 --limit 50

# 3. Confirm the outcome at the API, not only in the logs.
gcloud beta billing projects describe "$PROJECT_ID"   # billingEnabled: false
```

Expected log lines, in order: `budget notification received` →
`spend reported; detaching billing account` → `billing detached`.

A second publish while billing is already detached must log
`billing already detached; nothing to do` and change nothing. Run it: idempotence
under redelivery is part of the contract, and Pub/Sub delivers at least once.

### Evidence to archive in §4

1. Function log output for the firing (`gcloud functions logs read`), redacted of
   nothing — it contains no secrets by construction.
2. `gcloud beta billing projects describe` before and after, showing
   `billingEnabled` flipping to `false`.
3. A screenshot of the billing page showing the project detached.
4. The date, the project ID, and the operator.

The repository is public: the evidence carries a project ID and a billing account
ID. Neither is a secret — a billing account ID is not a credential — but the
screenshot must not include unrelated projects, invoices, or personal contact
details. Crop before committing.

## 4. Live-fire evidence

> Not yet executed. This section is filled by the operator immediately after the
> test; F0 acceptance criterion 7 and the F0 completion note both point here.
> Leaving it empty while claiming F0 complete would be exactly the silent
> degradation this project rejects.

## 5. Re-attach procedure (manual, human-only)

The kill-switch identity holds `roles/billing.projectManager` **on the project**
only. It can detach and cannot re-attach — deliberate: re-attaching spend is a
decision a human makes.

```bash
gcloud beta billing projects link "$PROJECT_ID" --billing-account "$BILLING_ACCOUNT"
gcloud beta billing projects describe "$PROJECT_ID"   # billingEnabled: true
```

Requires Billing Account Administrator (or Billing Account User) on the billing
account. After re-attaching:

- Re-run `terraform plan` in `infra/terraform`. Detaching billing disables
  billing-dependent APIs; some resources may need a re-apply.
- Confirm the budget still exists and still points at the topic. A kill-switch
  that fired once and left the chain broken is a kill-switch that fires only once.
- Record the incident in `docs/` per the architecture §7 escape hatch.

## 6. BigQuery custom query quota

Set by `infra/terraform/quota.tf` as a Cloud Quotas preference on
`QueryUsagePerDay`, project-scoped.

| Item | Value |
| --- | --- |
| Metric | `bigquery.googleapis.com` `QueryUsagePerDay` (project-level) |
| Unit | MiB per day |
| Chosen value | **20480 MiB = 20 GiB/day** (`var.bigquery_daily_query_quota_mib`) |
| Google default | 200 TiB/day |
| Free query tier | 1 TiB/month |

Arithmetic: 20 GiB/day over a 31-day month is 620 GiB, about 60% of the monthly
free tier, leaving headroom for Looker Studio and eval runs in the same month.
The variable's validation refuses anything above 33825 MiB/day, the point at
which a full month at the daily limit would leave the free tier.

This is a prevent-class control (ADR-0004 §1): the query is refused, no bytes are
billed, nobody has to notice. The kill-switch is report-and-stop, and it is later
in the chain.

Verify after apply, and record what the console reports:

```bash
gcloud services quota list \
  --service=bigquery.googleapis.com \
  --consumer=projects/"$PROJECT_ID" \
  --filter="QueryUsagePerDay"
```

If the effective limit does not read 20 GiB/day, the unit assumption in
`quota.tf` is wrong and the value must be corrected there — not worked around by
raising the variable.

## 7. Known limits of this control

- **Detach is project-wide.** Firing during F4's 14-day continuous-ingest window
  ends that window; the ingest evidence restarts (ADR-0004 consequences).
- **The function lives inside the envelope it protects.** If the project is so
  broken that Cloud Functions cannot run, the kill-switch cannot run either. The
  quota and the Terraform-level limits are the controls that do not depend on
  anything executing.
- **Reporting delay bounds the loss, it does not eliminate it.** See §1.
