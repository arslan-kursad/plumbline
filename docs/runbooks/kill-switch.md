# Runbook — billing kill-switch

**Status:** configuration delivered (F0 W4/W5); **two live-fires attempted, both
failed, each on a different missing permission** (§4). The F2 entry gate #33 stays
open until billing has been observed detaching at the API.

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
- The budget subtracts **Free Tier credits only** — see "Spend basis" below. A
  promotional credit must not mask spend; Always Free must not be mistaken for it.
- A cost update below the smallest reported amount is not visible to the
  function. In practice the first non-zero report fires it.

### Spend basis

The budget measures gross cost minus Free Tier credits only
(`INCLUDE_SPECIFIED_CREDITS` with `credit_types = ["FREE_TIER"]`). Promotional
credits — the Free Trial and marketing grants, which Cloud Billing groups under
`PROMOTION` — are **not** subtracted, so spend beyond the Always Free tier is
visible immediately even when a promotional credit is paying for it. Free Tier
usage nets to zero and does not trigger the switch.

Always Free is a credit against a non-zero gross cost line, not an absence of
charge. Excluding all credits — the first implementation — would make the budget
report spend during entirely free operation, and this chain detaches billing on
any reported spend. See ADR-0004 Amendment 1.

**Currency.** The budget's currency is not set in Terraform. The Budget API
rejects a create whose currency differs from the billing account's, and this
account does not bill in the currency the configuration was first written with;
inheriting the account's currency is both correct and portable. The synthetic
live-fire message below carries the account's currency for realism only — the
function compares `costAmount` against zero and never reads `currencyCode`, so a
mismatch there changes nothing.

**Verification A — documented behaviour. Performed once, after the first apply.
NOT YET DONE.**

Billing → Reports → clear the savings and credit filters. A non-zero usage cost
alongside a net total of zero confirms that Free Tier is credit-implemented, which
is the premise the spend basis rests on.

**Timing matters and is easy to get wrong.** An empty project produces no usage
line at all, so both figures read zero and the check confirms nothing. Run it
*after* `terraform apply`, once the kill-switch function has been built and
deployed — the Cloud Build run, the Artifact Registry storage and the function's
own invocations are free-tier usage, which is exactly the shape this verification
needs. Billing data lags by up to a day, so this is a next-morning step, not a
same-minute one.

Record the date and the observed figures here:

> Not yet executed. There is no billing account yet. Until this is recorded, the
> spend basis rests on Google's documentation alone — which states that free-tier
> services apply credits to implement the free usage — and not on an observation
> of this account.

If the observation contradicts the premise, stop: the amendment is withdrawn, not
patched.

**Verification B — empirical. F2, with services running.**

Capture a real budget notification from `billing-alerts` while Cloud Run services
are serving traffic, and assert `costAmount = 0.00`. Archive the redacted payload
next to the live-fire evidence. This is the only check that covers the
budget → notification segment; the live-fire does not reach it. Registered as an
F2 acceptance criterion.

## 2. Human prerequisites (F0 spec W4, human-only)

1. Create the GCP project and link a billing account.
2. Hold **Billing Account Administrator** on that billing account — the budget is
   a billing-account-level resource — and Owner (or equivalent) on the project.
3. Authenticate **twice**. `gcloud auth login` signs the CLI in; Terraform's
   Google provider reads Application Default Credentials, which is a separate
   store:

   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud auth application-default set-quota-project "$PROJECT_ID"
   ```

   The third command is not optional decoration. ADC without a quota project
   makes client libraries bill quota to no project, and the symptom is an
   "API not enabled" or "quota exceeded" error naming a service that is plainly
   enabled. `gcloud` prints the warning at login and it is easy to scroll past.

4. Enable the two APIs Terraform itself needs before it can enable anything
   else — on a fresh project the first plan fails without them, and the error
   reads like a bug in the configuration:

   ```bash
   gcloud services enable cloudresourcemanager.googleapis.com serviceusage.googleapis.com \
     --project "$PROJECT_ID"
   ```

5. Run `infra/terraform/bootstrap`, then the root module
   (see [`infra/terraform/README.md`](../../infra/terraform/README.md)). Both are
   run **from their own directory**; the modules are separate root modules, not a
   parent and a child.
6. Before the first apply, confirm the pinned function runtime still exists:
   `gcloud functions runtimes list --region us-central1`. The value is
   `var.killswitch_runtime`, currently `go126`; the function's `go.mod` requires
   Go 1.25, so raising the runtime is safe and lowering it below that is not.
   Support window as published: `go126` deprecates Feb/Mar 2027 and is
   decommissioned Aug/Sep 2027 — the calendar this pin has to be revisited by.

### If the first apply fails

Three failures are predictable enough to name, because each one's error message
points somewhere other than its cause.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Service account ...-compute@developer.gserviceaccount.com was not found` | Cloud Build's default identity is the default *compute* service account, which only exists once the Compute Engine API has been enabled. This configuration avoids it by naming its own build identity (`killswitch-build`); if the error still appears, something is falling back to the default. | Confirm `build_config.service_account` is set on the function. Enabling `compute.googleapis.com` also fixes it, at the price of a default VPC this project has no use for — prefer the named identity. |
| Build fails on permissions after the identity exists | The build identity was created in the same apply that used it, and IAM propagation lags. | Re-run `terraform apply`. The configuration already orders the grants before the function; propagation delay is not something ordering can fix. |
| An "API not enabled" or quota error naming a service you can see is enabled, with a `consumer` project number that is not yours | The provider is not sending a quota project, so the request is attributed to the project owning the OAuth client. Setting the ADC quota project does not fix this on its own — the provider only sends it when `user_project_override` is set, which `versions.tf` now does. | If it reappears, check that `user_project_override` and `billing_project` are still in the provider block, and that the caller has `roles/serviceusage.serviceUsageConsumer`. |
| The same error with **your own** project as `consumer` | The API really is disabled. | It should be in `apis.tf`; add it there rather than enabling it by hand. |
| `The caller does not have permission` on `google_billing_budget` | The budget is a billing-account-level resource, and project Owner does not reach it. | The operator needs Billing Account Administrator on the billing account, not only on the project (§2). |

None of these are cost events. They are first-apply friction, and they are written
down so the first apply is not also a research session.

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
  --message '{"budgetDisplayName":"plumbline zero-spend","alertThresholdExceeded":1.0,"costAmount":0.01,"budgetAmount":1.0,"currencyCode":"TRY","costIntervalStart":"LIVE-FIRE"}'

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

### Attempt 1 — 2026-08-21 — **FAILED, and this is the point of the test**

Billing did **not** detach. The function received the notification, decided
correctly, and was refused by the API:

```
11:05:13 INFO  budget notification received budget="plumbline zero-spend"
               cost=0.01 currency=TRY threshold_exceeded=1 interval_start=LIVE-FIRE
11:05:14 ERROR cannot read billing info and retrying will not help
               error="googleapi: Error 403: The caller does not have permission"
```

`gcloud beta billing projects describe plumbline-19458` reported
`billingEnabled: true` before and after. Earlier in the same log, at 10:52, a real
budget notification with `cost=0` had logged `no spend reported; billing left
attached` — the path that never touches the billing API, which is why nothing had
gone wrong until now.

**Cause:** detaching is authorized on both sides of the association, and the
identity held only the project side. `billing.resourceAssociations.delete` exists
in exactly one predefined role, Billing Account Administrator, grantable only on
the billing account. Fixed and explained in ADR-0004 Amendment 2, including what
the extra authority costs.

**What the attempt proves, beyond the defect:** the error classification worked —
a 403 is not retryable, so the function logged the reason and acked instead of
starting a redelivery loop, and the cause was legible in the first log line
anyone read. A control that fails loudly is the difference between this being a
morning's work and a discovery made during an incident.

### Attempt 2 — 2026-08-21 — **FAILED, same error, different cause**

The Amendment 2 grant was applied and verified live on the billing account —
against the billing account's own IAM policy, not against Terraform state:

```
roles/billing.admin  serviceAccount:killswitch-fn@plumbline-19458.iam.gserviceaccount.com
```

Billing still did not detach:

```
20:17:49 INFO  budget notification received budget="plumbline zero-spend"
               cost=0.01 currency=TRY threshold_exceeded=1 interval_start=LIVE-FIRE-2
20:17:49 ERROR cannot read billing info and retrying will not help
               error="googleapi: Error 403: The caller does not have permission"
20:18:33 INFO  budget notification received ... interval_start=LIVE-FIRE-2-REDELIVERY
20:18:33 ERROR cannot read billing info and retrying will not help
               error="googleapi: Error 403: The caller does not have permission"
```

`gcloud beta billing projects describe plumbline-19458` reported
`billingEnabled: true` throughout.

**Cause:** the function's *first* call is `Projects.GetBillingInfo`, and reading a
project's billing info needs `resourcemanager.projects.get` on the project. The
identity's entire project-level permission set was:

```
eventarc.events.receiveAuditLogWritten
eventarc.events.receiveEvent
logging.logEntries.create
logging.logEntries.route
resourcemanager.projects.createBillingAssignment
resourcemanager.projects.deleteBillingAssignment
```

Project Billing Manager grants exactly the last two. Billing Account Administrator
grants `resourcemanager.projects.get` against the **billing account**, which is a
different resource from the project being read. So the identity could detach
billing and could not find out whether it needed to.

Fixed by a one-permission custom role (ADR-0004 Amendment 3), not by
`roles/browser`: this identity already holds administrator rights over the billing
account and should not also collect project IAM reads.

**What this attempt cost, and what it bought.** Amendment 2 quoted this same error
line and diagnosed the *detach* rather than the *read* — the two-sided
authorization story was true and was not the failure in front of it. One live-fire
per permission defect is an expensive way to find them; it is also the only way
that has found any of them. Configuration review passed this identity twice.

### Attempt 3 — pending

> Not yet executed. Re-run §3 after the Amendment 3 custom role is applied. Both
> known permission defects are now fixed: the read (Amendment 3) and the delete
> (Amendment 2). The F2 entry gate #33 stays open until billing has been observed
> detaching at the API.

**What this test does not cover.** The live-fire publishes a synthetic message and
exercises Pub/Sub → function → detach. It says nothing about how the budget
computes the cost figure the function reads: a spend-basis defect sits upstream of
the boundary this test starts at, and a green live-fire is not evidence against
one. That segment is covered by Verification B in §1, in F2.

## 5. Re-attach procedure (manual, human-only)

### Triage first — a fire is not self-evidently a true positive

Before re-attaching, establish which case you are in:

1. Read the function's logged decision inputs: reported cost, currency, the
   threshold flag, and the cost interval. (`budgetAmount` is not logged on
   purpose — it is a constant of `infra/terraform/killswitch.tf`, so the
   configuration is the better source than a log line.)
2. Compare against the billing report for the same interval **with credits
   applied**.
3. Net cost above $0.00 → **true positive.** Find and remove the paid resource
   before re-attaching, or the switch fires again.
4. Net cost of $0.00 → **false positive**, most likely credit-application lag
   (ADR-0004 Amendment 1, residual risk). Record the payload: it is the input to
   the F2 decision between an epsilon threshold and a two-update confirmation
   rule. Do not invent either mitigation on the spot.

### Re-attaching

Re-attaching is a human step by procedure, not by permission. The kill-switch
identity holds Billing Account Administrator on the billing account — the only
role that can delete a billing association, and it can create one too
(ADR-0004 Amendment 2). What stops the function re-attaching is its code: one
write call, with an empty billing account name, against one project.

An earlier version of this runbook claimed the identity was incapable of
re-attaching. It is not, and the difference matters when reasoning about what the
control actually guarantees.

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

**Assumption, stated so it is not silently outgrown:** the 1 TiB/month free query
allowance is per *billing account*, not per project. This quota is per project. A
second project on the same billing account would consume the same allowance while
this quota kept reporting compliance, so the headroom above is a property of this
billing account having one project in it.
The variable's validation refuses anything above 33825 MiB/day, the point at
which a full month at the daily limit would leave the free tier.

This is a prevent-class control (ADR-0004 §1): the query is refused, no bytes are
billed, nobody has to notice. The kill-switch is report-and-stop, and it is later
in the chain.

**Applied and verified on 2026-08-21.** The Cloud Quotas API reports
`granted_value = 20480` against `preferred_value = 20480` for `QueryUsagePerDay`,
with `reconciling = false` — so the unit assumption above holds: the value is MiB
per day, and the effective limit is 20 GiB/day rather than 20 GiB in some other
unit or a request still being processed.

Re-verify after any change, and record what the console reports:

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
- **Deploying the function creates storage this configuration does not own.**
  A Gen2 function is built by Cloud Build into an auto-created `gcf-artifacts`
  Artifact Registry repository. That repository is not a Terraform resource here,
  it accumulates an image per deploy, and Artifact Registry's free allowance is
  0.5 GB. One small function redeployed occasionally stays well inside it; nothing
  in F0 enforces that. F2 owns Artifact Registry and its keep-last-2 cleanup
  policy (architecture §8), and the same policy has to cover `gcf-artifacts` — not
  only the repository this project creates for its own images.
- **On a trial billing account the switch fires anyway.** Promotional credits are
  not subtracted from the budget's spend (§1), so the first spend beyond Always
  Free detaches billing even if a trial credit would have paid for it. That is the
  intended behaviour — the project's claim is $0.00 gross — but it does mean trial
  credit cannot be spent while the kill-switch is armed.
