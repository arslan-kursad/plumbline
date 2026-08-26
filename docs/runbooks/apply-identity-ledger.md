# Ledger — what the apply identity can actually do

**Status:** opened 2026-08-26 (F2 directive W3C.6). A record, not an action: every
narrowing listed here is a `terraform apply`, and applies are gated.

`ci-deploy@` is the only identity that mutates this project through the gated
path. This file states, per grant, **what the wave that requested it needed** and
**what it actually covers**, because those two are not the same and the gap is
where a permission stops being least privilege without anybody deciding that it
should.

## Why this exists, and it is not a hypothetical

Wave 3 requested four new IAM operations — create a subscription, set subscription
IAM, set topic IAM, bind a Cloud Run invoker — and **none of them failed**. That
broke a streak: W2.11 counted five permission defects in this phase, every one
surfacing at apply and none at review.

The tempting reading is that review improved. It did not: review was not
exercised, because nothing was missing to find. The grants were already there,
and both of them were granted for something else:

- W2.7 granted `actAs` on `pubsub-push@` — for a subscription that did not exist
  and would not exist for another wave.
- W2.11 widened `roles/pubsub.editor` to `roles/pubsub.admin` on **topic**
  grounds, because `pubsub.topics.setIamPolicy` is in admin and not editor. Admin
  also carries `pubsub.subscriptions.create` and `pubsub.subscriptions.setIamPolicy`,
  which is what Wave 3 silently used.

**Wave 3's clean apply is therefore an argument for narrowing, not against it.**
A wave that needs no new permission is a wave whose permissions were granted
early and broadly, and the evidence for that is exactly the absence of the
failures the previous five waves produced.

## The ledger

Grants are in [`infra/terraform/wif.tf`](../../infra/terraform/wif.tf) unless
noted. "Narrow at F2 exit?" is a proposal for the exit review, not a decision.

| Grant | Principal | Scope | Wave that motivated it | What that wave needed | What it actually covers | Narrow at F2 exit? |
| --- | --- | --- | --- | --- | --- | --- |
| `roles/iam.serviceAccountUser` (`actAs`) | `ci-deploy@` | per service account: `collector@`, `ingestion-worker@`, `pubsub-push@` (`cloudrun.tf`) | W2.7 (Wave 2) | Deploy two Cloud Run services running as `collector@` and `ingestion-worker@` | Also `pubsub-push@`, **granted against a resource that did not exist at grant time** — no subscription would use it until Wave 3. It is per-account rather than project-wide, which is the deliberate part: the kill-switch's identity is out of reach | **No.** Already the narrowest useful shape, and the early third entry was a stated Wave 3 preparation rather than drift. Worth keeping as the example of doing this deliberately |
| `roles/pubsub.admin` | `ci-deploy@` | project | W2.11 (Wave 2) | `pubsub.topics.setIamPolicy` on `traces`, which `roles/pubsub.editor` lacks | Every Pub/Sub verb on every topic and **every subscription**, including create, delete and `setIamPolicy`. Wave 3 used three of those without a new grant. It also covers `billing-alerts` and the kill-switch's Eventarc subscription | **Candidate.** A custom role of editor + `topics.setIamPolicy` + the three subscription verbs was considered at W2.11 and rejected as ceremony, on the grounds that this identity already holds project IAM administration. That reasoning still holds and is the strongest argument against narrowing anything here — see the caveat below |
| `roles/iam.serviceAccountTokenCreator` | Google's Pub/Sub service agent | project (`killswitch.tf`) | F0 kill-switch | Eventarc mints an OIDC token to invoke the kill-switch function | Minting tokens as **any** service account in the project, including `pubsub-push@`. W3.4 found it redundant: `roles/pubsub.serviceAgent`, Google's automatic and non-removable grant, already carries `iam.serviceAccounts.getOpenIdToken` | **Candidate, and the cleanest one** — it is a grant this project made for a capability it cannot withhold. Removing it changes nothing that is reachable, so the test is whether Eventarc still invokes the function. Needs an apply and its own verification |
| `roles/resourcemanager.projectIamAdmin` | `ci-deploy@` | project | W1.5 (Wave 1) | Create the per-component IAM bindings each wave adds | Granting **itself** any project role at any time, including reaching the function-source bucket that A2.11 keeps it out of | **No, and the honesty matters more than the row.** A2.11 already records that the kill-switch separation is a convention this repository keeps, not something Google enforces, precisely because of this grant. Narrowing it would mean Terraform could no longer manage IAM, which is most of what the gated path does |
| `roles/storage.objectAdmin` | `ci-deploy@` | the state bucket only | F0 / W1.5 | Write Terraform state and its lock | The state bucket and nothing else. Explicitly not the function-source bucket, which is what A2.11's 403 proved is real | **No.** This one is already the shape the others should be |
| `roles/billing.viewer` | `ci-deploy@` | billing account | W1.5 | `terraform plan` refreshes the budget | Reading the billing account. Write is absent by design, which A2.9 confirmed at apply when the budget update failed 403 | **No.** The boundary is load-bearing and has been exercised |
| `roles/viewer`, `roles/iam.securityReviewer` | `ci-deploy@` | project | F0 / W1.5 | Refresh every resource in state during a plan | Reading everything in the project | **No.** A plan blind to a resource is a plan blind to drift |
| `roles/bigquery.dataOwner`, `roles/datastore.owner`, `roles/artifactregistry.admin`, `roles/monitoring.editor`, `roles/run.admin`, `roles/iam.serviceAccountAdmin`, `roles/serviceusage.*` | `ci-deploy@` | project | Waves 1–2 | Create and update the resources of each wave | Full administration of each service. `bigquery.dataOwner` was chosen over `dataEditor` on measurement, not preference: `dataEditor` creates a dataset and cannot update one | **Review as a set**, not individually. Each is the smallest predefined role that does its wave's job; the aggregate is close to project editor |

## The caveat that has to be read with the table

Narrowing anything here is worth less than it looks while
`roles/resourcemanager.projectIamAdmin` stands, because that grant lets this
identity restore any role it lost. A2.11 states the same thing about the
kill-switch boundary and calls it a convention rather than a control, which is
the accurate description.

That is an argument about what narrowing *buys*, not an argument against doing
it. A convention this repository keeps still means a routine apply cannot reach
what it should not by accident, and reaching it would take a visible, reviewable
IAM change. What it must not become is a claim that the boundary is enforced.

## What would actually change the picture

Removing standing apply roles altogether — the identity holds nothing until a
wave grants it, and the grant is revoked at wave close — is the design that makes
this table short. It needs a break-glass path so an operator is not locked out
mid-incident, and that path is unwritten. This ledger is the input to that work,
not a substitute for it.

## Rules for this file

- One row per grant. A grant with no row is a grant nobody stated a reason for.
- The "what it actually covers" column is filled from the role definition —
  `gcloud iam roles describe` — not from what the wave intended. W2.11 and W3.4
  were both settled that way, and both times the intended and actual differed.
- No row is edited to match a narrowing that has not been applied. A ledger that
  describes the intended state rather than the live one is the failure mode
  architecture §6.1 has already had corrected twice (W2.5, W3.7).
