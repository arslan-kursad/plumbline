# F2 — Minimal GCP Footprint: Work Package Spec

**Version:** 0.2 · **Status:** Approved on handoff (2026-08-21), Amendment 1 proposed
2026-08-30 · **Date:** 2026-08-21
**Phase budget:** ~15 h · **Executor:** Claude Code (graduated mode, §2) + maintainer (§9)
**Predecessor:** F1 complete ([`F1-completion-note.md`](F1-completion-note.md)); the
claude-code capture (#10) is still open and stays non-blocking — it gates F4's
detection-fidelity claim, not this phase.

---

## 1. Purpose

Deploy the minimal cloud footprint: Terraform for Pub/Sub, BigQuery, Firestore,
Artifact Registry and two Cloud Run services (`collector`, `ingestion-worker`), with a CI
pipeline that builds distroless images and deploys through Workload Identity Federation.

The phase exits when OTLP sent from a local machine lands in cloud BigQuery and is
queryable through the views, with the bill at $0.00 and the kill-switch **proven working
before any service exists**.

`analytics-api` is **not** deployed in F2. The Brief names two services here; the eval
engine that justifies the third is F3.

## 2. Governance mode: graduated (delta from F1)

F1's autonomy precondition — zero blast radius — does not hold. F2 mutates cloud state
and can, in failure modes, cost money. The response is not per-decision conversational
confirmation, which is the failure mode the F1 model was built to remove; it is moving
the confirmation to an enforcement point.

**Lane A — autonomous, identical to F1's rules.** Everything that lives only in the
repository: Terraform source, CI workflows, Dockerfiles, Firestore adapter code, real
OIDC validation, runbooks, SQL and view definitions, the decision log. Self-merge once
CI is green and Gates A–F pass. Merging Terraform *code* mutates nothing; only `apply`
does, and `apply` is not in this lane.

**Lane B — human-armed apply waves.** Every cloud mutation happens through the CI deploy
workflow, which targets a GitHub Environment (`gcp-production`) carrying a
required-reviewer protection rule. Claude Code prepares a wave — pull requests merged,
plan output attached to the wave issue — the maintainer approves the environment gate
once, CI applies, Claude Code verifies and records. One click per wave, five waves (§6).
No `terraform apply` from any other path: a local apply by anyone is a process violation,
and drift suggesting one happened is raised, not absorbed.

**The rule binds from Wave 1, and the reason is a fact rather than a preference.** F0
shipped exactly one CI identity, `ci-readonly`, and made it provably incapable of
deploying — `infra/terraform/wif.tf` documents the `ci-deploy` identity as F2's to create
and deliberately does not create it. So the first mutation of this phase cannot come from
CI: the identity CI would use does not exist, and creating it is itself a mutation.
Whatever the governance model says, that first apply comes from a human's own credentials,
exactly as every F0 apply did. Wave 0 is that apply and is scoped to it (§6). From Wave 1
onward the CI path exists and the rule is absolute.

**Lane C — human only.** Billing-console actions (confirming the detach, re-attaching,
the Verification A observation), API key plaintext custody, and anything touching the
billing account outside Terraform.

**Mechanical precondition (W0a).** The environment protection rule must exist before the
first wave is armed. Claude Code opens the setup steps as a checklist in the Wave 0
issue; the maintainer configures it under Settings → Environments. It is a manually
managed GitHub setting, so it lands in
[`repository-settings.md`](../runbooks/repository-settings.md) with its read-back
evidence — the inventory rule, and the reason that file archives reads rather than the
commands that were run.

### Stop rules (hard)

- **A second kill-switch live-fire failure halts the phase.** No wave beyond 0 is
  prepared until the failure is analysed, fixed, and a successful live-fire archived.
  Deploying services under a known-broken kill-switch is a cost-invariant violation by
  construction.
- **Any billed cost stops every further wave.** Billing Reports showing gross cost not
  fully credit-offset, or a budget notification carrying `costAmount > 0.00`, activates
  the two-consecutive-day incident-note escape hatch (architecture §7).

## 3. Entry gates

| Gate | Content | Satisfied by |
| --- | --- | --- |
| **G1** (#33) | The kill-switch is proven working | Wave 0: the merged permission fix applied, live-fire succeeds, evidence archived, billing re-attached, #33 closed. **No application service deploys before G1.** |
| **G2** (#44) | ADR-0006's two F2 obligations | Before Wave 3: the DLQ runbook states that dead-lettered messages may carry personal data and are never pasted into public issues, and DLQ retention is set explicitly in Terraform with its rationale in the commit. Ordering is verifiable from merge and apply history. |

G1 is remediated *inside* F2 as Wave 0. The gate blocks the service footprint, not the
remediation work that clears it.

## 4. Decisions resolved on handoff

Settled, not open. Each is restated in [`F2-decision-log.md`](F2-decision-log.md) with
its reversibility class.

### D1 — Apply gating through a GitHub Environment protection rule
As described in §2. Chosen over per-decision chat confirmation, which kills velocity and
reintroduces the failure mode the F1 model fixed, and over auto-apply on merge, which
would make self-merge a cloud mutation. The approval artefact is the environment review
itself: auditable, timestamped, in-platform, and not a sentence in a transcript.

### D2 — Cloud verification traffic is constructed fixtures, `synthetic=true`
All traffic sent to the cloud collector during F2 uses the F1 constructed corpus with
resource attribute `synthetic=true`. Never a real capture: the claude-code fixture
carries the maintainer's real personal data (`user.email`, host paths), and shipping it
through cloud Pub/Sub before F4's dogfooding governance is unnecessary exposure. The
walled-off-synthetic flag (architecture §4.1) already gives the clean mechanism.

Consequence, stated here and repeated in the completion note: **F2 proves the pipe, not
real-source fidelity.** Real-source ingest is F4's claim, and #42 already carries the
re-validation of the constructed corpus against real emitters.

### D3 — Secret Manager (architecture Open Question 2) resolves toward secret-free
The hashed-registry design leaves the collector with no secret to hold: it reads hashed
keys from Firestore under its own service account identity, and the worker and CI
authenticate through service accounts and WIF. Default resolution: **no Secret Manager**,
collector secret-free by construction.

If implementation surfaces a genuine secret with no identity-based alternative, Claude
Code records it prominently in the decision log and proposes Secret Manager scoped to
that one item at the next wave boundary — not silently, and not by adding it to a wave
already armed. Architecture §6.3 and Open Question 2 are updated to match (Lane A edit,
cited to this spec).

### D4 — One definition of the view logic
F1 created `spans_deduped` and `spans_real` DDL under
[`analytics/sql/`](../../analytics/sql) for the local stand-in. The cloud views are
Terraform-owned `google_bigquery_table` view resources — and the SQL is **not**
duplicated. Terraform reads the same files.

A drifted copy of the dedup rule between local and cloud is exactly the class of silent
divergence golden tests exist to prevent; here the prevention is structural rather than
test-based, because there is only one file to change.

**Mechanism, which is not free and is decided in Wave 1 rather than assumed.** The files
are executable DDL — `CREATE OR REPLACE VIEW ... AS SELECT` with two-part names — while
the Terraform view resource takes the query body alone, and the cloud reference needs the
project. Whatever mechanism carries that gap (a template with the DDL prologue and the
dataset reference parameterised, or a body file the DDL wraps), the invariant it must
satisfy is fixed: **exactly one place states the dedup rule, and a change there reaches
both targets.** A mechanism that requires editing two files is a failed implementation of
this decision, not a variation of it.

### D5 — API keys through a CLI tool, plaintext in human custody
[`tools/keyctl`](../../tools) (Go) generates a key, prints the plaintext **once**, and
writes only the hash and metadata to Firestore `api_keys`. The maintainer runs it
(Lane C) after Wave 1. Plaintext never enters the repository, CI logs, chat, or the issue
tracker.

The tool emits the format the collector already enforces — `plb_<environment>_<32
lowercase hex>`, sixteen random bytes, with `live` as the issued marker in the cloud
(`collector/internal/auth`: `IssuedEnvironments`; Gate F, issue #19) — and writes the
registry document shape the F1 `KeyRegistry` reads. A key the collector's own shape check
would reject is a defect in this tool, and its tests assert the shape rather than
describing it.

Terraform-seeding of keys is rejected: state would then hold material derived from a
show-once secret workflow, and Terraform cannot model "display once".

### D6 — Permissions and the allowlist grow per wave, least privilege
The CI service account gains only the roles a wave requires, added in that wave's
Terraform and enumerated in that wave's issue. A single up-front broad grant is rejected.
The plan-diff guard must pass at every wave boundary and is never loosened wholesale.

**How this reads against architecture §7.1 as it already stands.** The allowlist table
already carries every resource type F2 introduces, each marked `F2`, authored ahead of
this phase. Removing those rows to re-add them wave by wave would be churn that improves
nothing: the guard is type-level, and the types were argued for when they were written
down. What D6 binds in practice is therefore (a) IAM role grants, which genuinely grow
per wave and are enumerated per wave, and (b) any resource type **not** already in the
table — which arrives as a spec change with a changelog entry, exactly as §7.1 says.
Two rows describe more than F2 builds (`google_cloud_run_v2_service` names
`analytics-api`, `google_bigquery_table` names `eval_results`); both are F3's, and F2
creating either would be an out-of-scope violation the type check cannot catch.

## 5. Out of scope (hard)

- `analytics-api` deployment, the eval engine, judges, the Scheduler nightly batch — F3.
- Editing [`docs/eval-plan.md`](../eval-plan.md) — standing prohibition; the Freeze A
  executor closes #36.
- Real-source ingest (Adjudicator, Apartment Triage, live Claude Code sessions) — F4.
- Load generator, dashboards, SPA — F4.
- Any paid feature, any region other than `us-central1`, exactly-once subscriptions.
- Flipping any ADR to `Accepted`.
- Local or manual `terraform apply` outside the gated CI path.

## 6. Work items

Five apply waves and one repository lane that runs throughout. A wave is prepared in
Lane A, armed by the maintainer once, then verified and recorded.

### Wave 0 — Kill-switch remediation and live-fire (satisfies G1)

- **W0a** — Environment `gcp-production` protection configured by the maintainer from the
  checklist in the wave issue, then recorded in `repository-settings.md` with read-back
  evidence.
- **W0b** — Confirm the merged-but-unapplied state. **Measured rather than assumed:** the
  authenticated CI plan of 2026-08-21
  ([run 32518317749](https://github.com/arslan-kursad/plumbline/actions/runs/32518317749),
  job `terraform plan (wif)`) reports **1 to add, 0 to change, 0 to destroy** — only
  `google_billing_account_iam_member.killswitch_billing_admin`, granting
  `roles/billing.admin` to `killswitch-fn@`. The directive expected the Amendment-1 credit
  filter to be pending as well; it is not, because it is already applied, and a plan that
  refreshes the budget through the CI identity's `billing.viewer` grant would have shown
  drift if the live filter differed from the configuration. The wave applies **one
  resource**, not two. Anything else appearing in the plan is investigated before it is
  applied, never applied around.

  **The plan is `-target`ed, and that is a consequence of Lane A rather than a shortcut.**
  Lane A merges Terraform for later waves into `main` because merging mutates nothing —
  and it means `main` now describes more infrastructure than Wave 0 applies. An untargeted
  apply from a laptop would create Wave 1's BigQuery resources outside the gated path, which
  is the one thing the phase forbids from Wave 1 on. So Wave 0 names its single resource:

  ```
  terraform plan -target=google_billing_account_iam_member.killswitch_billing_admin -out plan.tfplan
  ```

  Targeting is normally a smell, and this is the case it exists for: applying one
  deliberately chosen resource while later waves sit merged in the same configuration.
  Terraform prints `Resource targeting is in effect` — that warning is the wave's receipt,
  not a problem to suppress.
- **W0c** — Apply, from the maintainer's own credentials, in `infra/terraform` — the path
  #33 already specifies, and the only path that exists before `ci-deploy` does (§2). The
  pending change is billing-account-scoped, which is the one scope the CI identity is
  argued out of holding in Wave 1. Live-fire per
  [`kill-switch.md`](../runbooks/kill-switch.md) §3: publish the synthetic alert to
  `billing-alerts`, watch the function decide, confirm `billingEnabled: false` **at the
  API and not only in the logs**, publish a second time to prove idempotence under
  redelivery. The maintainer confirms on the billing console (Lane C) and re-attaches.
  Evidence — function logs, before/after `describe`, cropped screenshot, date and
  operator — archived in runbook §4 as Attempt 2. Close #33.
- **W0d** — Runbook updated with the Attempt-2 transcript and the current triage
  sequence.

*Why this wave is not a CI apply:* see §2. The bootstrapping fact is stated where the
governance rule is, so a reader does not find the rule and this wave contradicting each
other with no explanation between them.

*Why the live-fire precedes every service:* a detach with services running would disrupt
them. With none deployed the test has no side effects, which is the only window in the
project's life where that is true.

### Wave 1 — Deploy path, data stores, transport skeleton, registry

This wave builds the mechanism D1 rests on, because Wave 0 could not use it.

- **W1a — the identity, applied by the maintainer (Lane C, targeted).** The same
  bootstrapping fact as Wave 0, one step further on: an apply performed *by* `ci-deploy`
  cannot be the apply that *creates* `ci-deploy`. So the identity, its Workload Identity
  binding and its role grants are applied locally and targeted at those resources, and
  every apply after it goes through the gate. This is the last local apply of the phase,
  and the spec says so here so that a later one has nothing to appeal to.

  ```
  terraform plan -target=google_service_account.ci_deploy \
    -target=google_service_account_iam_member.ci_deploy_wif \
    -target=google_project_iam_member.ci_deploy \
    -target=google_billing_account_iam_member.ci_deploy_billing_viewer \
    -target=google_storage_bucket_iam_member.ci_deploy_state -out plan.tfplan
  ```

  Then the repository variable `GCP_DEPLOY_SERVICE_ACCOUNT` is set to the new identity's
  email — the deploy workflow's preflight refuses without it, which is how the first
  dispatch already failed on purpose.

- **`ci-deploy` and the deploy workflow.** The identity `infra/terraform/wif.tf` describes
  and refuses to create: a separate service account whose principalSet requires the branch
  as well as the repository, so a pull request cannot obtain deploy credentials even from
  this repository. The workflow is `workflow_dispatch` only — a wave is armed
  deliberately, never by a merge — with a plan job whose output is the reviewable diff and
  an apply job carrying `environment: gcp-production`.
- **What the deploy identity may hold, decided here and not drifted into.** Two scopes are
  in question and they are not the same question. *Project scope:* growing the identity's
  own grants per wave (D6) requires project IAM administration, which makes the identity
  project-admin-equivalent; the control is then the environment gate and the plan guard,
  not the role list, and saying otherwise would be the kind of claim ADR-0004 Amendment 2
  had to withdraw. *Billing-account scope:* `wif.tf` already names the cleaner shape —
  billing-account-scoped resources in their own state, so no CI identity reads or writes
  across that boundary — and names F2 as where that conversation happens. It happens in
  this wave, with the decision and its cost in the log either way.
- **BigQuery**: dataset `plumbline` and table `spans` exactly per architecture §4.1 —
  daily partitioning on `start_time`, clustering `(trace_id, span_id)`,
  `require_partition_filter = true`. Views per D4. Confirm the F0 project-level query
  quota still reads 20 GiB/day (runbook §6 carries the command and the unit assumption
  it verifies).
- **Firestore**: native mode, `us-central1`, with the `api_keys` collection conventions
  documented. `tools/keyctl` implemented in Lane A; the maintainer provisions the first
  key after the apply (Lane C, D5).
- **Pub/Sub**: topics `traces` and `traces-dlq`, topic retention **off** on both; the DLQ
  **pull** subscription with retention set explicitly and its rationale in the commit
  (G2 material); a Monitoring alert policy on `num_undelivered_messages > 0` with a free
  notification channel. **The main push subscription is not created in this wave** — it
  needs the worker URL and G2.
- **Artifact Registry**: repository `plumbline` with a keep-last-2 cleanup policy — *and*
  the same policy covering `gcf-artifacts`, the repository Cloud Build auto-creates for
  the kill-switch function. Runbook §7 assigns that to F2 explicitly: it accumulates an
  image per function deploy against a 0.5 GB free allowance, and nothing in F0 enforced
  it. It is not a Terraform-owned repository today, so the wave issue records which
  mechanism was used to reach it and what that costs.
- **Gate B coverage**: `tools/keyctl` is Go source outside the declared scan roots, so
  Gate B's coverage check fails the moment it lands. The fix is to add `tools` to
  `SOURCE_ROOTS` in `scripts/ci/invariant-gates.sh` — a deliberate, visible widening of
  what the gate scans, which is precisely the shape ADR-0004 §3 intends. It is never
  fixed by narrowing the check or excluding the path.
- **WIF roles** grown per D6 and enumerated in the wave issue.

### Wave 2 — Images and services

Lane A prerequisites, all merged before the wave is armed:

- Distroless Dockerfiles for the collector and the worker.
- **Real OIDC push validation replacing the F1 stub.** Removal is verified mechanically —
  `StubPushAuthenticator` and its marker string are gone from the tree — not asserted in
  a pull request description. The F1 decision log W5.2 records why the stub announces
  itself; this is the phase where the announcement stops being needed.
- A Firestore-backed `KeyRegistry` adapter behind the F1 interface.
- CI: build → distroless → push to Artifact Registry through WIF. The build lane may run
  before the wave; the push needs the wave's roles.

Terraform in the wave:

- Cloud Run `collector` — public ingress, because agents send from outside the project;
  the API key layer is the authentication boundary, and architecture §6.2's approximate
  per-instance rate limit is the known limitation that comes with it.
- Cloud Run `ingestion-worker` — unauthenticated invocations disabled, the push service
  account created now and bound as sole invoker in Wave 3. **Ingress is verified, not
  assumed:** architecture §6.1 says `ingress=all` is avoided for the worker, and whether
  a Pub/Sub push subscription reaches a Cloud Run service under internal ingress is a
  property of the platform, checked against current Google documentation at wave time
  and recorded in the wave issue with the setting that was chosen. Guessing this wrong
  produces either an open endpoint or a silently undelivered subscription.
- Both services: `min_instances = 0`, `max_instances <= 2`, smallest viable CPU and
  memory, `us-central1`, dedicated service accounts per architecture §6.1 with
  table-scoped and collection-scoped grants.
- **The F0 plan-diff guard becomes load-bearing here.** It must be shown to actually
  evaluate these resources — the wave issue carries guard output naming the Cloud Run
  addresses, not an assumption that a guard which has only ever seen a Cloud Function
  reads `template.scaling` correctly. Its region assertion covers `location` and `region`
  keys; Firestore's `location_id` is outside that, which is recorded rather than assumed
  away.

### Wave 3 — Wiring (gated by G2)

- Precondition recorded in the wave issue: #44's obligations are in `main` — runbook
  language and the retention rationale — **before** this wave is armed.
- Terraform: the OIDC push subscription from `traces` to the worker URL, the push service
  account as sole `roles/run.invoker`, maximum delivery attempts 5, dead-lettering to
  `traces-dlq`.
- Close #44 with links to the merged artefacts and this wave's apply, which is what makes
  the ordering claim checkable rather than narrated.

### Wave 4 — Cloud end-to-end and the verifications

- **`make e2e-cloud`** (Lane A, merged before arming): sends the constructed corpus
  (D2, `synthetic=true`) from the local machine to the cloud collector with the
  provisioned key, polls the BigQuery views with partition-filtered queries only, diffs
  against the golden expectations, sends the poison fixture, and asserts both DLQ
  delivery and the alert firing. Runbook-driven and re-runnable.
- **Idempotence is asserted, not assumed:** run it twice and show row counts through the
  views stay stable. That is the dedup property ADR-0002 rests on, and a replay is the
  cheapest test of it available.
- **DLQ triage rehearsal:** follow the #44 runbook once against the real poison message.
  Inspect without exposing content; archive the transcript with content elided. The
  repository and its issue tracker are public, which is the whole reason the obligation
  exists.
- **Verification B (asynchronous, #18):** with services deployed and the e2e run
  generating genuine free-tier usage, observe a budget notification carrying
  `costAmount = 0.00`. Function logs are sufficient evidence. Watch window: up to 7 days
  from the Wave 4 apply. **If the window passes without a qualifying notification, F2
  does not close silently** — the gap is escalated as an ADR-0004 residual-risk finding.
- **Credit-lag observation — starts here, does not finish here:** the procedure is
  documented under `docs/runbooks/`, naming what to record (Billing Reports gross versus
  credited cost, dates, observed lag), the cadence, and where the series accumulates.
  The first data point is captured in F2; the series continues through F3 and F4 per the
  Amendment-1 deferral, because choosing between an epsilon threshold and a two-update
  confirmation rule before observing real sequences would substitute a guess for a
  measurement.

### W-repo — Lane A, throughout

- [`F2-decision-log.md`](F2-decision-log.md) maintained as F1's was: entries written when
  the decision is made, not reconstructed at phase close.
- Architecture updates: §6.3 and Open Question 2 resolved per D3; §8 moved from planned
  to deployed state where that becomes fact. Version bump per repository convention.
- F2 completion note at close: DoD evidence links, D2's scope statement in plain words,
  and the deferred items.

## 7. Definition of Done

1. **G1**: #33 closed — post-fix live-fire succeeded, evidence archived, billing
   re-attached, the corrected credit filter live.
2. **G2**: #44 closed with ordering evidence — runbook and retention merged before the
   push subscription existed.
3. Constructed-fixture OTLP sent from a local machine lands in cloud BigQuery; rows are
   correct through `spans_deduped` and `spans_real` under partition filters; every row
   carries `synthetic = true`.
4. A poison message reaches the cloud DLQ, the undelivered-messages alert fired, and the
   triage rehearsal transcript is archived with content elided.
5. Every cloud resource is Terraform-owned, the final `terraform plan` is clean (drift is
   a bug), and zero resources were created outside the gated CI path.
6. Cloud Run configurations are inside the guardrails, and the plan-diff guard is shown
   to actually evaluate them.
7a. **Push transport established.** The `traces` → `ingestion-worker` OIDC push
   subscription exists with audience `plumbline-ingestion-worker`, max delivery attempts 5,
   dead-lettering to `traces-dlq`, and `pubsub-push@` as sole `roles/run.invoker` on the
   worker. No stub endpoint. Verified by reading the live resource configuration from the
   API, not from the plan. **Satisfied** — Wave 3, run `32969025343`.

7b. **Push transport exercised.** The worker's OIDC validator has accepted a real
   Google-signed token from a delivery originating in the `traces` topic, and the resulting
   span is present in `plumbline.spans`. **Open** — owner: Wave 4, first delivery. F2 does
   not exit with 7b open.

   No message was published to `traces` during Wave 3, and that was a choice rather than an
   oversight: publication is irreversible, it lies outside the gated path, and a message
   landing in the dead-letter queue now would consume the triage rehearsal criterion 4
   specifies against Wave 4's own poison fixture.
8. Verification B satisfied inside the watch window, or escalated. Never skipped (#18).
9. The credit-lag procedure is live with at least one data point.
10. Billing Reports for the period are fully credit-offset at $0.00 billed; the September
    boundary check absorbs the pending F0 criterion 11 (#17).

    > *Items 8–10 are evaluated against billed cost while a promotional trial credit is
    > active. They establish that the period was fully credit-offset. They do **not**
    > establish that gross cost is zero, and are not evidence for the project's zero-cost
    > claim. That claim is carried by item 13.*
11. The decision log is complete: every Lane-A decision of consequence recorded with
    rationale and reversibility class.
12. Gates A–F green throughout, and no gate, allowlist or protection rule loosened beyond
    D6's per-wave additions.

13. **Verification C — post-credit confirmation.** After the promotional trial credit
    ends (2026-10-05) and the account state has settled, all three of the following
    hold, each recorded with evidence:
    - **13a.** Billing Reports for a full period show **gross cost $0.00**, not merely
      $0.00 billed after credit offset.
    - **13b.** The three-step kill-switch live fire has been re-run **after** the account
      upgrade and passed. Every prior firing occurred behind the credit; this is the
      first time the `INCLUDE_ALL_CREDITS` trigger arms against a real charge.
    - **13c.** 13a holds continuously across a 14-day window during which ingest is
      running.

    Owner: Lane C. F2's completion note is written before Verification C and records it
    as an open dated obligation, naming this item. F2 is not re-opened by it; the
    zero-cost claim is not published until it closes.

### 7.1 Calendar constraints

Written down because they were held in one person's memory, and the chain they constrain
is serial: #82 merge → Wave 4 arm → first delivery → 7b → F2 exit → Verification C.

| # | Constraint | Owner |
|---|---|---|
| C1 | Account upgrade decided and executed **no later than 2026-09-28** — one week before credit end. Later risks resource suspension mid-window, which costs the ingest data; earlier wastes credit. | Lane C |
| C2 | Kill-switch live fire (13b) re-run immediately after upgrade, **before** the window opens. | Lane C |
| C3 | The 14-day window opens only after C2 passes, and **must not straddle 2026-10-05**. Earliest open 2026-10-05; earliest close 2026-10-19. | — |
| C4 | **Verification C's 14-day window (13c) and F4's 14-day continuous-ingest window are the same calendar block.** Both require post-credit operation and continuous ingest. Planned separately, they cost a month. | — |
| C5 | F3 (~20 h) sits between Wave 4's first delivery and the window opening. It is the **only slack in the chain**. Schedule delay is absorbed there or nowhere. | — |
| C6 | The F4 window carries the Claude Code emitter's human-initiated-session constraint: captures requiring tool/hook spans route through the operator's terminal. Fourteen consecutive days of that source is a staffing constraint, not a technical one, and belongs in the plan as such. | Lane C |

### 7.2 Closing-note requirements

Content requirements on the F2 completion note, not suggested wording.

- **CN1 — the credit sentence.** F2's $0.00 is credit-offset. Free Tier usage is
  credit-implemented in GCP, so gross cost is non-zero during entirely free operation
  (ADR-0004 Amendment 4). F2's billing evidence does not establish the zero-cost claim;
  item 13 does.
- **CN2 — the calendar block.** State C4 explicitly: Verification C's 14-day window and
  F4's are one block, opening on or after 2026-10-05.
- **CN3 — Wave 1 drift, root cause recorded.** Not "unexplained". W1.8 identifies it:
  sources where the API normalises a value and the configuration insists on writing it
  back — Monitoring lowercases the notification address while the secret was written in
  uppercase; `older_than = "0s"` is not persisted and was re-added on every plan run.
  Both named, both fixed (`lower(var.alert_email)`, `older_than = "86400s"`), verified by
  `terraform plan -detailed-exitcode` returning 0 with no changes on 2026-08-30.
- **CN4 — provenance rule for status claims.** Any claim in the closing note that an item
  is open must cite **where and when it was verified open**. Carrying a status forward
  from a prior document is not verification. This phase has already produced one such
  error — the Wave 1 drift root cause was carried as "unexplained" out of a summary table
  into a directive and then into a second directive, after W1.8 had explained and fixed
  it. The rule extends W3C.2's fixture-provenance principle to prose: **a hand-authored
  status table is a hand-authored fixture, and it fails the same way.**

## 8. Decision authority

| Class | Examples | Authority |
| --- | --- | --- |
| Lane A — decide alone, log it | Terraform module layout, Dockerfile details, `keyctl` UX, alert channel choice, e2e-cloud tooling, the DLQ retention value (rationale logged, surfaced at #44's closure) | Claude Code |
| Lane A — decide alone, log prominently | D3's fallback if a genuine secret appears, any deviation from architecture §6.1, any guard or allowlist change, any unexpected plan diff | Claude Code |
| Lane B — human-armed | Every `terraform apply` from Wave 1 on — four waves | Maintainer approves, Claude Code executes and verifies |
| Lane C — human only | The Wave 0 apply, billing-console confirm and re-attach, Verification A, key plaintext custody, environment protection setup | Maintainer |
| **Never** | Local or manual applies; paid features; flipping an ADR to `Accepted`; editing `eval-plan.md`; real-capture traffic to the cloud; weakening branch protection, a gate, or the kill-switch | — |

## 9. Human touchpoints

The complete list. Nothing else mid-phase.

1. **W0a** — environment protection setup, once. It is configured in Wave 0 and first
   used in Wave 1, which is the first wave with a CI apply path to protect.
2. **The Wave 0 apply** — from the maintainer's own credentials, because `ci-deploy` does
   not exist yet and both pending changes are billing-account-scoped (§2, §6).
3. **The W1a apply** — the deploy identity, targeted and local, for the same reason as
   Wave 0: an apply by `ci-deploy` cannot create `ci-deploy`. The last local apply of the
   phase. Setting `GCP_DEPLOY_SERVICE_ACCOUNT` afterwards is part of it.
4. **Four environment approvals** — Waves 1 through 4.
5. **Kill-switch live-fire confirmation and billing re-attach** — Wave 0, Lane C.
6. **Verification A** — any morning after the Wave 0 apply: Billing → Reports with the
   savings and credit filters cleared, confirming a non-zero usage cost against a zero
   net total. It is the observation the budget's whole spend basis rests on, it has never
   been performed (runbook §1 records it as outstanding, #17 step 2 carries it), and it
   is console-only, so no lane but Lane C can do it. If the observation contradicts the
   premise, stop: ADR-0004 Amendment 1 is withdrawn, not patched.
7. **First API key provisioning** through `keyctl` — after Wave 1, Lane C.
8. **C2-style exit review** — completion note, D2's scope statement, Verification B
   evidence, a decision-log skim.

The claude-code capture (#10, F1's C1) stays open and stays non-blocking: it gates F4's
detection-fidelity claim, not anything in F2.

## 10. Verification expectations

- Every wave issue carries the plan output, the roles and allowlist delta, and the
  post-apply verification commands **with their results**. A wave without recorded
  verification is incomplete regardless of how green the infrastructure looks.
- `e2e-cloud` is re-runnable and safe under replay, and that property is demonstrated by
  running it twice rather than argued from the view definitions.
- Cost evidence is empirical: Billing Reports observations recorded per the credit-lag
  procedure, never inferred from "nothing here should cost anything".
- A skipped CI job is not a passing one, and a merged fix is not a deployed one. Both
  sentences are already in this repository's history because both were learned here.

## 11. Issue map

| Issue | Role in F2 | Closes in F2 |
| --- | --- | --- |
| #33 | G1 — kill-switch live-fire before any service deploys | Yes, Wave 0 |
| #44 | G2 — ADR-0006's two DLQ obligations | Yes, Wave 3 |
| #18 | Verification B — a real notification reading `costAmount = 0.00` | Yes, Wave 4, or escalated per DoD 8 |
| #17 | F0 criterion 11 — the bill at the end of the billing period; its step 2 is Verification A (§9.4) | Not necessarily — it closes when the billing period does |
| #10 | F1's C1, the claude-code capture | No — non-blocking, gates F4 |
| #42 | F4 re-validation of the constructed corpus against real emitters | No — it is the other half of D2's honesty |
| #36 | Freeze A alignment in `eval-plan.md` | No — context only; F2 does not touch that file |

## 12. Changelog

**Amendment 1 — 2026-08-30** — Verification C, the credit qualification, and the shared
calendar block (source decision D-74; #17, #18, #74, ADR-0004 Amendment 4).

**Numbering, checked rather than assumed.** The amendment text warned against assuming
this is Amendment 1, citing the ADR-0004 sequence that was misnumbered once by assuming a
gap. Verified: this spec carries no prior amendment. Every occurrence of "Amendment" in it
before today refers to ADR-0004's, and §12 held one entry (v0.1). So it is Amendment 1
because the sequence is empty, not because nothing suggested otherwise.

1. §7 items 8–10 gain a qualifier, their text unchanged: they are evaluated against
   **billed** cost while a promotional trial credit is active, so they establish that the
   period was fully credit-offset and are not evidence for the zero-cost claim.
2. §7 gains item 13, **Verification C** — gross cost $0.00 after the credit ends, a
   kill-switch live fire re-run against a real charge for the first time, and both holding
   across a 14-day window with ingest running. No existing item is renumbered.
3. §7.1 records the calendar constraints C1–C6, including that Verification C's 14-day
   window and F4's are **one** calendar block.
4. §7.2 records the four closing-note content requirements.

**Placement corrected.** The amendment's header names "§5 (Definition of Done)". §5 of
this spec is *Out of scope (hard)*; the Definition of Done is **§7**, and its §3.3 would
have filed the calendar constraints under the section listing what the phase will not do.
Applied to §7.

**v0.1 — 2026-08-21** — the handoff directive rendered into the repository as the phase's
source of truth. Content follows the directive. Nine things are stated here that the
directive left implicit or stated against an earlier state of the repository, each one
recorded rather than silently applied:

1. **Gates A–F, not A–E.** Gate F — no issued API key in the repository — landed in F1
   W3 with issue #19. The directive's Lane A and acceptance criterion 12 both say A–E,
   which was the F0 set.
2. **Wave 1 carries a Gate B source-root extension.** `tools/keyctl` (D5) is Go source
   outside the declared scan roots, and Gate B's coverage check fails on it by design.
   Widening `SOURCE_ROOTS` is the intended response and is named as a work item so it is
   not discovered as a red build.
3. **Wave 1 carries `gcf-artifacts`.** The kill-switch runbook §7 assigns its cleanup
   coverage to F2 explicitly; the directive's Artifact Registry item names only the
   `plumbline` repository.
4. **§9 adds Verification A as a human touchpoint.** The directive called its list
   complete and does not contain it; the runbook and #17 both carry it as outstanding,
   and it is the observation the budget's spend basis rests on. Listing it is a change to
   the directive's scope for the maintainer's time and is flagged as such rather than
   folded in quietly.
5. **§11 maps the issues.** #18 and #17 are F2-bearing and were not enumerated in the
   directive; #18 *is* acceptance criterion 8 and #17 *is* the F0 item criterion 10
   absorbs.
6. **D4 states the mechanism constraint.** The `analytics/sql/` files are executable DDL
   and the Terraform view resource takes a query body, so `file()` alone does not carry
   the decision. What is fixed is the invariant — one place states the rule — and the
   mechanism is chosen in Wave 1.
7. **Wave 0 is not a CI apply, and Wave 1 builds the path.** The directive routes all
   five waves through the gated CI workflow. F0 shipped one CI identity and made it
   provably unable to deploy; `wif.tf` documents `ci-deploy` as F2's to create and does not
   create it. The first mutation of the phase therefore comes from the maintainer's own
   credentials whatever the model says — which is also what #33 specifies — and the rule
   binds absolutely from Wave 1. §2 and §6 state it in both places rather than leaving a
   reader to find the rule and the wave contradicting each other.
8. **Wave 0 applies one resource, not two.** The directive expects the Amendment-1 credit
   filter to be pending alongside the Amendment-2 permission fix. The authenticated plan
   says otherwise — 1 to add, 0 to change — so the filter is already live. The correction
   matters because W0b tells the operator to stop on an unexpected plan, and an
   expectation of two changes would have stopped this wave on the good news.
9. **D6 is read against architecture §7.1 as it already stands.** The allowlist already
   contains every F2 resource type. Per-wave growth therefore binds IAM grants and any
   unlisted type, and two allowlist rows describe resources F3 owns.
