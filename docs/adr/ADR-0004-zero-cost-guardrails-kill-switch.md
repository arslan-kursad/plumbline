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
- **Gate B (secondary, report):** path-scoped symbol scan over `collector/**/*.go`,
  `worker/**/*.cs`, `analytics/**/*.cs` for the streaming-insert symbol set. Scoped by a
  path allowlist, not a file denylist — documentation will keep naming these symbols and
  must never need an exclusion entry.
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
- The kill-switch is the one cost control that has been *observed* to work, because it is
  fire-tested with archived evidence at F0. It is also the acceptance criterion that cannot
  be satisfied on paper.
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

## References

- `docs/architecture.md` §2.3, §6.2, §7, §8.
- `docs/specs/F0-foundations.md` §W4, §W6.2, §W6.4, §W6.5, §W6.6, §5, §6.
- ADR-0001, ADR-0002, ADR-0003, ADR-0005 — each names its controls against this taxonomy.
