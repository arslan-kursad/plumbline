# Billing readout — the reads the deny-list rewrite unblocked

**Read:** 2026-09-05 · **Lane:** A · **Repo:** `main @ 0e3f595`
**Project:** `plumbline-19458` · **Task:** [`completion-plan.md`](../specs/completion-plan.md) W0-2, W0-3
**Precondition that made it possible:** the Lane A deny-list rewrite
([`lane-a-denylist-rewrite.md`](../proposals/lane-a-denylist-rewrite.md)) applied by the
maintainer on 2026-09-05.

> **What this closes and what it does not.** Two of DoD 1's five facts were open on one
> refused API call; both are now measured live and both hold. The cost-attribution question
> underneath `#74` and ADR-0009 §1.4 is **not** closed here, and §4 states why it cannot be
> closed by any command — it is a console read, not a permission problem.

The billing account id is held as a repository secret and is written nowhere in this file;
every command below is shown with it elided.

---

## 1. DoD 1 fact 4 — billing attached, in the present tense

```
$ gcloud billing projects describe plumbline-19458
billingAccountName: billingAccounts/<elided>
billingEnabled: true
name: projects/plumbline-19458/billingInfo
projectId: plumbline-19458
```

**Holds, read 2026-09-05.** [`f2-dod1-five-facts.md`](f2-dod1-five-facts.md) recorded this
fact as *"held on 2026-08-21, then went false five times"* and left its current value
unread, because the read was refused. The last unbroken re-attach it records is
2026-08-25 ~12:11; this read is eleven days later and the state has not moved since.

**The fact is a state claim and stays one.** Nothing here promises it will be true
tomorrow — the F2 spec's Amendment 2 rewrote fact 4 into the present tense for exactly
that reason, and a closing note citing this file must cite its date with it.

## 2. DoD 1 fact 5 — ADR-0004 Amendment 4's credit filter is live

```
$ gcloud billing budgets list --billing-account=<elided> \
    --format='table(displayName,amount.specifiedAmount.units,
                    amount.specifiedAmount.currencyCode,
                    budgetFilter.creditTypesTreatment,budgetFilter.creditTypes,
                    notificationsRule.pubsubTopic,thresholdRules[].thresholdPercent)'

DISPLAY_NAME                UNITS  CURRENCY  CREDIT_TYPES_TREATMENT  CREDIT_TYPES  PUBSUB_TOPIC                                    THRESHOLD
plumbline zero-spend        1      TRY       INCLUDE_ALL_CREDITS                   projects/plumbline-19458/topics/billing-alerts  [1.0]
plumbline gross-cost alert  100    TRY       EXCLUDE_ALL_CREDITS                                                                   [0.5, 1.0]
```

**Holds, read at the API rather than from state.** `plumbline zero-spend` carries
`INCLUDE_ALL_CREDITS` and an **empty** `creditTypes` list — Amendment 1's enumerated filter
is absent from the deployed object, not only from the repository. Gate H forbids it in
Terraform; this is the other half, and until today only the repository half had been read.

**Three further facts fall out of the same reading, each of which had been asserted from
configuration rather than measured:**

| Claim | Where it was asserted | Measured here |
|---|---|---|
| Exactly one budget publishes to `billing-alerts` (ADR-0004 Amendment 4 D3, restated in Amendment 5 D3; the plan guard asserts it at plan time) | plan guard | **holds live** — `zero-spend` binds the topic, `gross-cost alert` has no binding |
| The gross-cost alert is 100 TRY with two thresholds (Amendment 5 D3's early-warning tier: emails at 50 % and 100 %) | ADR-0004 Amendment 5 | **holds live** — 100 TRY, `[0.5, 1.0]` |
| The account bills in TRY, and the budget inherits it (Amendment 5 D1) | `killswitch.tf` comment | **holds live** — `currencyCode: TRY` on both budgets and on the account |

**And the function's threshold, re-read the same day**, because
[`f2-detach-threshold-200-applied.md`](f2-detach-threshold-200-applied.md) is dated
2026-09-02 and a value read three days ago is a value that has had three days to move:

```
$ gcloud functions describe billing-killswitch --region us-central1 --project plumbline-19458 \
    --format='value(serviceConfig.environmentVariables,updateTime,serviceConfig.revision)'
DETACH_THRESHOLD=200;LOG_EXECUTION_ID=true;TARGET_PROJECT_ID=plumbline-19458
2026-09-02T09:22:01.148214741Z    billing-killswitch-00003-yoh
```

Unchanged at the moment of the read: same value, same revision, same update time.
**Still configured rather than proven** — ADR-0004 Amendment 5's Verification section is
unmoved by any of this, and the three-step live fire at `200.00` is
[`completion-plan.md`](../specs/completion-plan.md) W1-8.

> **Superseded within the hour, and recorded rather than left to look current.** The
> maintainer redeployed the function at `2026-09-05T11:00:53Z` to carry `grpc v1.83.1`,
> so the revision is now `00004-don` and the update time has moved
> ([`f2-killswitch-grpc-1831-redeploy-2026-09-05.md`](f2-killswitch-grpc-1831-redeploy-2026-09-05.md)).
> **`DETACH_THRESHOLD` is unchanged at `200` across that redeploy**, which is the part this
> section asserts. The two rows above are true for the time they name and false as a
> present-tense claim about the revision — which is the whole reason this project stamps a
> reading with its clock rather than filing it as a fact.

## 3. No drift between the deployed budgets and Terraform

`killswitch.tf`'s `zero_spend` resource declares `credit_types_treatment =
"INCLUDE_ALL_CREDITS"`, `threshold_percent = 1.0`, `spend_basis = "CURRENT_SPEND"`, an
`all_updates_rule` bound to `google_pubsub_topic.billing_alerts`, and an amount of
`var.budget_amount` in the account's inherited currency. Every one of those matches the
reading above.

**The budget's amount is 1 TRY and that is not the trigger.** The function compares
`costAmount` against its own `DETACH_THRESHOLD`; `thresholdExceeded` is ignored (ADR-0004
Amendment 1, unchanged by Amendment 4). The 1 TRY amount only scales a threshold rule
nothing reads. Recorded because a reader meeting `UNITS 1` beside a 200 TRY ceiling will
otherwise assume one of the two is wrong.

## 4. What is still not readable, and it is not a permission problem

**`#74` and ADR-0009 §1.4 disagree about which credit absorbs this project's usage**, and
settling it needs cost broken down by credit type. That read is **not available from any
command**:

- The Cloud Billing API exposes accounts, projects, budgets and IAM. It exposes **no
  cost-query surface**; `gcloud billing` has no verb that returns a cost figure.
- Cost broken down by SKU and credit type is available in two places only: the Cloud
  Billing **console** Reports page, and a **BigQuery billing export**.
- **No billing export exists.** `bq ls --project_id plumbline-19458` returns one dataset,
  `plumbline`, read 2026-09-05. Creating one is a resource outside the Terraform allowlist
  and would itself consume the storage the cost claim is about.

**So the remaining half of W0-3 is a console read and always was.** The deny-list rewrite
did not fail to unblock it; it was never blocked by the deny-list. Recorded plainly because
"Lane A cannot read it" and "no API returns it" are different facts, and this project has
already paid once for treating a tooling limit as a permission limit.

Two figures therefore remain transcribed rather than measured, and both carry ADR-0009's
own warning: the credit's remaining balance (₺13,987.54, `#74`) and its expiry
(2026-10-05). Promotional credit balances have no API surface either.

## 5. A finding in a live file, raised rather than fixed here

`infra/terraform/variables.tf`'s `budget_amount` description reads, of the kill-switch
function: *"the function detaches billing whenever reported cost is **strictly greater
than zero**."*

That is **Amendment 1's trigger**. It was falsified in production on 2026-08-22, replaced by
Amendment 4 with a threshold, and the threshold was moved to the 200 TRY ceiling by
Amendment 5. The description has never been edited, so a live configuration file states a
rule the project replaced twice — the same shape as *"the corrected credit filter"* in the
completion note's §5 identifier rule, this time in Terraform rather than in a spec.

**Not fixed in this change.** It is discovered work outside the active task, and `CLAUDE.md`
routes that to an issue rather than into the branch that found it.

## 6. Provenance

Every command in this file was run on 2026-09-05 from Lane A against `plumbline-19458`,
after the deny-list rewrite was applied. `gcloud billing accounts list`,
`gcloud billing projects describe`, `gcloud billing accounts describe`,
`gcloud billing budgets list`, `gcloud functions describe` and `bq ls` are all read-only and
none mutates. The Terraform comparison in §3 is a read of
`infra/terraform/killswitch.tf` and `variables.tf` at `main @ 0e3f595`.

No line here is admissible as evidence in a closing note without its date; the two facts in
§1 and §2 are present-tense claims about a system that has changed under them before.
