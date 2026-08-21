# ADR-0004 — Zero-cost guardrails & billing kill-switch design

**Status:** Accepted · **Date:** 2026-08-18 · **Work package:** F0 / W2
**Architecture:** §2.3, §6.2, §7, §8
**Supersedes:** — · **Superseded by:** —

## Context

`$0.00` is a hard constraint here, not a target, and it is also one of the four claims the
project exists to demonstrate. A cost overrun is therefore not a budget problem to absorb;
it is a failed experiment, published or unpublished.

Two properties of the problem shape the design.

**Free tiers do not stop — they start billing.** GCP offers no global hard spending cap.
Budget alerts are notifications. Nothing in the platform's default configuration prevents a
misconfigured `min-instances`, an enabled topic retention, or one unpartitioned query from
converting a $0 project into a billed one, silently, at 03:00.

**A guardrail can be nominally present and structurally unable to detect the violation it
names.** This is not hypothetical: the v0.1 guardrail for the BigQuery write path was a
repository grep for the literal string `insertAll`. The .NET client never surfaces that
string — it exposes the streaming insert path as `BigQueryClient.InsertRow` /
`InsertRows` / `InsertRowsAsync` — so a genuine violation in `worker/` would pass the gate,
while `CLAUDE.md`, which legitimately names the forbidden method, would fail it. The gate
was wrong in both directions and had been treated as protection. A gate that cannot fail on
its target is worse than no gate, because it is trusted.

So this decision covers two things: what the guardrails are, and how a guardrail is allowed
to be described.

## Decision

### 1. Control taxonomy — every invariant declares what actually holds it

Each invariant in the architecture §7 register names its enforcement point *and* its class:

- **Prevent** — the violation cannot be committed, merged, or deployed. Terraform-owned
  configuration, the forbidden-dependency gate, GitHub push protection.
- **Report** — the violation is detected after the fact and surfaced. Alerts, counters,
  CI scans that run on already-pushed commits.
- **Review** — no mechanical control; a human is the only detector.

Review-class invariants are permitted. What is not permitted is leaving an invariant
unlabelled, because an unlabelled control is read as prevention by default. The taxonomy
exists so that the honest answer — "nothing stops this; someone would have to notice" — is
written down instead of implied.

### 2. Guardrails are layered by how early they act

Terraform (the configuration cannot exist) → CI gates (the code cannot merge) → quotas
(the workload cannot scale) → alerts (the spend becomes visible) → kill-switch (billing
stops). The kill-switch is deliberately last: firing it means every earlier layer failed.
Its job is to bound the loss, not to be the control.

### 3. BigQuery write path

- **Gate A (load-bearing, prevent):** no `Google.Cloud.BigQuery.V2` reference in any
  `*.csproj` or `Directory.Packages.props`. If the package is absent, the forbidden API
  surface is unreachable regardless of what the symbols are called.
- **Gate B (secondary, report):** path-scoped symbol scan over the declared source
  roots for the streaming-insert symbol set. Scoped by a path allowlist, not a file
  denylist — documentation will keep naming these symbols and must never need an
  exclusion entry. The root list is declared once in the gate script, and the gate
  fails if source appears outside it: shrinking coverage has to be a visible decision.
- **Code review is not an enforcement point** for this invariant and is recorded as such.

### 4. Pattern notation

Forbidden-string patterns are written in a form that cannot match their own textual
representation; a character class around one literal character suffices
(`private[_]key`, `agent[-_. ]?lens`). This holds in the gate scripts and in the
specification text alike. Consequence: no gate needs an exclusion list, no gate can be
weakened by adding a path to one, and a whole-repository scan stays whole-repository.
Gate B's path scoping is unrelated to this — it targets a property of source code, where a
match in documentation is not a defect.

### 5. Billing kill-switch

Budget alert (threshold: **any spend above $0**) → Pub/Sub topic `billing-alerts` →
Cloud Function (Gen2, smallest, `us-central1`) calling `projects.updateBillingInfo` to
detach the billing account.

It is **live-fired in F0**, not assumed: the test publishes a synthetic alert message to
the topic, billing is observed to detach, and the evidence — function logs plus the billing
page — is archived in `docs/runbooks/kill-switch.md` together with the manual re-attach
procedure. An untested kill-switch is a comfort object.

### 6. Escape hatch

Any spend above $0.00 on two consecutive days produces an incident note in `docs/` —
before the kill-switch makes the question moot.

## Alternatives considered

**A. Budget alerts only (the documented GCP approach).**
Rejected. An alert is a notification, and the gap between "email sent" and "human reads
email" is unbounded on a part-time schedule of roughly 90 hours spread over six weeks. The
failure this design defends against is precisely the one that happens while nobody is
looking; a control that requires attention does not address it.

**B. Quotas alone, no kill-switch.**
Rejected as sufficient, adopted as a layer. Quotas are per-service and per-metric, so the
surprise arrives from the service that was not capped. The project-level BigQuery custom
query quota is set regardless — it is prevent-class and covers the single largest scan
risk — but a per-service cap is not a global brake.

**C. A kill-switch that disables the offending service instead of detaching billing.**
More surgical, less destructive. Rejected: it requires correctly identifying *which*
service is spending, at the moment of failure, in a code path that is exercised roughly
never. Detaching billing is one API call with one outcome, and that is exactly what makes
it testable. Testability is the whole argument — a selective kill-switch would be a larger
program with a lower probability of working when needed.

**D. Trusting the free tier without a brake.**
Rejected. Free tiers begin billing at the limit rather than stopping, and this design
contains components with no free tier at all when misconfigured (`min-instances > 0`,
Pub/Sub topic retention). The project's own thesis is that invariants must be enforced
rather than intended; exempting the cost invariant from that would be self-refuting.

**E. Code review as an enforcement point.**
Rejected as an enforcement point, retained as a practice. A single-author repository with
zero required approvals (F0 spec W6.5) does not produce review as a mechanical property.
Claiming it as enforcement in a public case study would be the silent degradation this
project refuses.

**F. Literal-string CI greps as the general gate pattern.**
Rejected as the primary form — it failed on its first application, in both directions.
Retained as a secondary, path-scoped signal where the symbol set is known and stable
(Gate B).

## Consequences

**Positive**

- "Is this invariant actually enforced?" is answerable by reading one table, and the answer
  can be "no, only reviewed" without that being a defect — only without it being hidden.
- The kill-switch is the one cost control whose claim rests on observation rather than
  configuration, because it is fire-tested with archived evidence. It is also the
  acceptance criterion that cannot be satisfied on paper. *(Written for F0, where the
  live-fire was deferred to the F2 entry gate. As of Amendment 3 the switch has been fired
  twice and has not yet worked; the sentence stands as the reason that is known.)*
- The pattern-notation rule removes the exclusion-list failure mode permanently, rather
  than patch by patch. It was reached the hard way: two gates in this project tripped on
  the documents that defined them.

**Negative / accepted costs**

- Detaching billing is indiscriminate. It stops the collector and the worker along with
  whatever was spending, so a kill-switch firing during F4's 14-day continuous-ingest
  window restarts that criterion. Accepted deliberately: a broken measurement is
  recoverable, an unbounded bill is not.
- Re-attaching requires a human with billing-account permissions. The runbook is therefore
  load-bearing infrastructure, not documentation, and its absence would make the
  kill-switch a denial-of-service on the project.
- The kill-switch function lives inside the envelope it protects. It is small and free, but
  it cannot restore what it detached — the recovery path is deliberately outside the
  system, in a human's hands.
- Gate A depends on the forbidden capability being nameable as a package. A write path
  introduced through a different package, or a raw REST call, is outside its reach; Gate B
  is a thin secondary net over a fixed symbol list. The gap is real and is not closed by
  this decision.
- Several invariants remain review-class: no invented canonical schema (ADR-0001), view
  discipline for dedup (ADR-0002), the Firestore collection boundary (ADR-0003), no public
  live API in v0.1 (ADR-0005). Labelling them changes nothing mechanically. It only stops
  the project from believing they are protected.

**Contract correction carried on this branch**

Architecture §2.3 stated the worker "must not use `insertAll`". That is the same defect as
the v0.1 gate, one level up: an implementer writing `BigQueryClient.InsertRowsAsync` would
read the prohibition, never encounter the string, and conclude they had complied. The v0.2
correction fixed the *control* in §7; §2.3 is the same defect in the *contract*. The two
are corrected in the same pull request on purpose — a reader landing between them would
find an enforcement point contradicting the contract it enforces, which is worse than
either version alone.

## Enforcement

- **Architecture §7 is the register.** A new invariant added without an enforcement point
  and a class is an incomplete change, rejected at review.
- **F0 spec W6.2 gates, each proven to fail** — not merely green on a clean tree (F0 spec
  §6; acceptance criterion 9). A gate that has never failed is untested, and this project
  has already shipped one that could not fail.
- **W6.4 push protection is the prevent-class control for secrets; Gate C is the
  report-class backstop behind it.** Push protection rejects at push time, before the
  secret reaches history; Gate C runs in CI, after. This pairing is the worked example of
  the taxonomy in §1.
- **Kill-switch live-fire with archived evidence** — F0 acceptance criterion 7, and the
  one criterion in the phase that cannot be satisfied by writing something down.
- **Terraform owns every GCP resource** (§8); anything hand-created is drift, and drift is
  a bug.

## Amendment 1 (2026-08-19) — Budget spend basis

Status unchanged: the decision above stands. What is corrected is one parameter of §5 —
the basis on which the budget computes the number the kill-switch function reads.

### Problem

The chain was implemented with the budget filter set to `EXCLUDE_ALL_CREDITS`. The intent
was right: promotional credits — the Free Trial and marketing grants, which Cloud Billing
groups under the `PROMOTION` credit type — act as a form of payment, and a net-cost basis
would sit at $0.00 while real money was being consumed.

The setting overshoots. Budgets compute spend as gross cost minus the *selected* credits;
with all credits excluded, spend is gross cost. Always Free is not an absence of charge —
it is a `FREE_TIER` credit applied against a non-zero gross cost line. Under
`EXCLUDE_ALL_CREDITS` the budget therefore reports spend above zero during entirely
normal, entirely free operation.

Consequences of leaving it:

- The kill-switch detaches billing on the first Cloud Run request in F2, while the
  invoice reads $0.00.
- The failure is not recoverable by the system. Re-attachment is human-only by design
  (§5), so a false positive is an outage rather than a blip.
- **The F0 live-fire cannot detect it.** The live-fire publishes a synthetic message and
  exercises Pub/Sub → function → detach. This defect is upstream of that boundary, in how
  the budget computes the number the function reads. A passing live-fire is not evidence
  against this class of defect, and the runbook now says so where the evidence is
  archived.

### Decision

Subtract the Free Tier credit type and nothing else:

```hcl
budget_filter {
  credit_types_treatment = "INCLUDE_SPECIFIED_CREDITS"
  credit_types           = ["FREE_TIER"]
}
```

`credit_types` may only be non-empty under `INCLUDE_SPECIFIED_CREDITS`; any other
treatment requires it empty, so a mismatch fails at the API rather than degrading
silently. The enum values were read from the Cloud Billing credit-type reference, not
from memory: `FREE_TIER` is the free-tier credit, and `PROMOTION` is the type that covers
the Free Trial and campaign grants.

This yields the intended semantics exactly: **any spend not covered by Always Free fires
the switch, and promotional credits cannot mask it** — on a trial account and on a paid
one alike, so the control does not depend on which kind of account it is pointed at.

No change to the Cloud Function. The `costAmount > 0` comparison and its zero-boundary
and permanent-versus-retryable tests remain valid; only the meaning of `costAmount`
changes, and it changes to what this design always intended it to mean.

### Alternatives considered

| Option | Free Tier reads as spend | Promotional credit masks spend | Verdict |
|---|---|---|---|
| `INCLUDE_ALL_CREDITS` (API default) | no | **yes** | Rejected: the original risk stands. |
| `EXCLUDE_ALL_CREDITS` (as first built) | **yes** | no | Rejected: false-positive detach during normal operation. |
| `INCLUDE_SPECIFIED_CREDITS` + `FREE_TIER` | no | no | **Adopted.** |
| Non-zero (epsilon) threshold | n/a | n/a | Deferred to F2 — see residual risk below. |

### Consequences

1. The F0 live-fire stays a valid test of the Pub/Sub → function → detach segment and is
   **not** re-run for this change. Its scope limit is now written down rather than
   implied.
2. A new empirical criterion lands in F2: with services deployed and serving traffic, a
   **real** budget notification must show `costAmount = 0.00`. It is the only test that
   exercises the budget → message segment, and it is vacuous before F2 because nothing
   billable is running.
3. A detach is human-irreversible, so a fire must be triageable from the function's own
   log output. The function already logs the per-invocation decision inputs — reported
   cost, currency, threshold flag and cost interval. `budgetAmount` is deliberately not
   among them: it is a constant of the Terraform configuration, not per-invocation data,
   and reading it from the log rather than from the configuration would be the weaker
   source. The triage sequence in the runbook names the fields that exist.

### Residual risk — deliberately not decided here

Credit application can lag usage reporting. If a `FREE_TIER` credit lands in a later
budget update than the usage it offsets, a transient non-zero cost is possible while the
account is genuinely free. Two mitigations are candidates: an epsilon threshold — an
explicit, documented relaxation of "any spend above $0" — or a two-consecutive-updates
confirmation rule, which trades a bounded exposure window for false-positive immunity at
the cost of function state.

**Neither is adopted now.** Choosing before observing real notification sequences would
substitute a guess for a measurement, in the one control whose whole argument is that it
was tested rather than assumed. The decision is taken in F2 against captured payloads and
recorded as a further amendment. Until then the residual risk is accepted and stated, not
mitigated by assumption.

## Amendment 2 (2026-08-21) — The kill-switch could not detach billing

Status unchanged. The decision stands; its permission model was wrong, and the
live-fire is what proved it.

### What happened

The first live-fire published a synthetic notification and the function did
everything right up to the act itself:

```
11:05:13 INFO  budget notification received budget="plumbline zero-spend"
               cost=0.01 currency=TRY threshold_exceeded=1 interval_start=LIVE-FIRE
11:05:14 ERROR cannot read billing info and retrying will not help
               error="googleapi: Error 403: The caller does not have permission"
```

Billing stayed attached. The control was inert, and had been inert since the day
it was deployed.

### Cause

Detaching billing is authorized on **both sides** of the project-to-billing-account
association:

| Permission | Scope | Predefined roles containing it |
| --- | --- | --- |
| `resourcemanager.projects.deleteBillingAssignment` | project | Project Billing Manager, Billing Account Administrator |
| `billing.resourceAssociations.delete` | billing account | **Billing Account Administrator only** |

The design granted Project Billing Manager on the project and nothing on the
billing account, which covers one side of a two-sided check.

### Decision

Grant `roles/billing.admin` to the kill-switch service account **on the billing
account**, keeping the project-side grant. This is what Google's own
disable-billing-with-notifications procedure grants, and there is no narrower
option: the permission exists in exactly one predefined role, and billing-account
IAM takes predefined roles.

### What this costs, stated rather than absorbed

**The claim that this identity "can detach and cannot re-attach, by construction"
is withdrawn.** It was the tidiest sentence in §5 and it was false. The only role
that can delete the association can also create it. Re-attachment remains a human
step because of the function's code and the operating procedure — not because the
identity is incapable of it. That is a weaker guarantee and it is now written as
one.

**Blast radius.** A service account inside this project holds administrator rights
over the billing account: it can move billing for any project under that account,
and close the account. Three things bound it, none of which is a permission
boundary on the role itself:

- No key exists to steal (§6.1 — Workload Identity Federation, no exported keys).
- It is invocable only by Eventarc from the `billing-alerts` topic; `run.invoker`
  is granted on that one service, not project-wide.
- The function's code never attaches, and never names a project other than
  `TARGET_PROJECT_ID`. It has exactly one write call, with an empty billing
  account name.

**Alternative reconsidered.** Alternative C above — disabling the offending
service instead of detaching billing — becomes more attractive once detaching
costs this much authority. It is still rejected for the reason given there: it
requires correctly identifying what is spending, at the moment of failure, in a
code path exercised roughly never. Revisit it in F2 if the blast radius proves
unacceptable; that would be a further amendment, not a silent change.

### Why this is the argument for live-firing, not against it

§5 says an untested kill-switch is a comfort object. It was one — for the whole
period between deploying it and firing it. No amount of reading the configuration
would have found this: the permission model is plausible, symmetric, and wrong,
and every layer above it worked. The test that this project made mandatory is the
only thing that could have caught it, and it caught it on the first attempt.

## Amendment 3 (2026-08-21) — The permission model was wrong on the other side too

Status unchanged. Amendment 2's fix was necessary, correct, and not sufficient. The
second live-fire is what proved it, and it failed with the same error as the first.

### What happened

```
20:17:49 INFO  budget notification received budget="plumbline zero-spend"
               cost=0.01 currency=TRY threshold_exceeded=1 interval_start=LIVE-FIRE-2
20:17:49 ERROR cannot read billing info and retrying will not help
               error="googleapi: Error 403: The caller does not have permission"
```

Billing stayed attached. `roles/billing.admin` was live on the billing account at the
time — verified against the billing account's IAM policy, not against Terraform state.

### Cause

The function's first call is `Projects.GetBillingInfo`, and reading a project's billing
info requires `resourcemanager.projects.get` **on the project**. The kill-switch identity
did not have it. Its entire project-level permission set was six permissions:

```
eventarc.events.receiveAuditLogWritten
eventarc.events.receiveEvent
logging.logEntries.create
logging.logEntries.route
resourcemanager.projects.createBillingAssignment
resourcemanager.projects.deleteBillingAssignment
```

Project Billing Manager carries exactly the last two. Billing Account Administrator
carries `resourcemanager.projects.get`, but against the **billing account** resource,
which is not the project the function reads. So the identity could delete the billing
association and could not find out whether it needed to.

### Why Amendment 2 did not catch this

Amendment 2 read the 403 and reasoned about the act the function exists to perform —
detaching — and detaching is genuinely two-sided, so the analysis produced a real defect
and a correct fix. What it did not do was read the log line it quoted. **`cannot read
billing info` names the call that failed, and it is not the detach.** The fix addressed
the second call while the failure was in the first, and the two-sided-authorization story
was plausible enough to stop the search.

The lesson is narrow and worth keeping: an error message that names an operation is
evidence about *which* operation, and a diagnosis that does not account for the wording is
incomplete however well it explains the status code.

### Decision

A custom role carrying one permission:

```hcl
resource "google_project_iam_custom_role" "killswitch_billing_reader" {
  role_id     = "killswitchBillingReader"
  permissions = ["resourcemanager.projects.get"]
}
```

Rather than `roles/browser`, the narrowest predefined role containing it, which also
grants `resourcemanager.projects.getIamPolicy`, `projects.list`, and folder and
organization reads. This identity already holds administrator rights over the billing
account; it is the last one in the project that should collect incidental reads. The cost
is a resource type added to the architecture §7.1 allowlist, which is what that list is
for.

### What this says about the control, again

Two live-fires, two permission defects, both invisible to configuration review and both
fatal to the control. The kill-switch was inert from the day it was deployed until the day
it was tested, and then it was inert again through one fix. §5's sentence — an untested
kill-switch is a comfort object — has now been demonstrated twice by the same object.

The third live-fire is the one that has to pass, and the record in
`docs/runbooks/kill-switch.md` §4 carries all three attempts rather than only the one that
worked. A runbook that archives only successes teaches nothing about the failure modes of
the thing it documents.

## References

- `docs/architecture.md` §2.3, §6.2, §7, §7.1, §8.
- `docs/specs/F0-foundations.md` §W4, §W6.2, §W6.4, §W6.5, §W6.6, §5, §6.
- ADR-0001, ADR-0002, ADR-0003, ADR-0005 — each names its controls against this taxonomy.
- Cloud Billing credit types (`FREE_TIER`, `PROMOTION`, …) and the rule that
  `credit_types` is non-empty only under `INCLUDE_SPECIFIED_CREDITS` — Amendment 1.
