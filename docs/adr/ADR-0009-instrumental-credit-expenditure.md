# ADR-0009 — Instrumental expenditure of expiring trial credit before the measurement window

**Status:** Proposed · **Date:** 2026-09-03 · **Deciders:** author (Lane C)
**Supersedes:** nothing · **Related:** `#74`, `#138`, `#177` (T2-01), ADR-0004
**Affects:** `architecture.md` §7 (cost guardrails), §10 (ADR index)
**Number:** read from `docs/adr/` on 2026-09-03 — 0001–0008 present, 0007 and 0008 both
Proposed, so 0009 is next. Re-derive before any later renumbering; do not inherit this.

> **v0.2 is v0.1 checked against the repository** at `main @ 418c67f`. Five claims did not
> survive, three of them reproductions of defects this repository corrected on 2026-09-02.
> §11 lists every change with the read that caused it.

---

## 1. Context

### 1.1 The asset

The billing account holds a Free Trial Welcome credit: promo value ₺13,987.54, **amount
remaining ₺13,987.54**, expiring **2026-10-05**. Consumption is zero.

The expiry is by date, not by exhaustion. At the observed burn rate the credit would outlast
the project by roughly twenty-nine thousand years. Nothing about the pace of work moves
2026-10-05. This is already recorded once and is not re-litigated here.

**These figures are transcribed from a console screenshot and are not re-read in this
document.** §3.1 makes the authoritative read a precondition.

### 1.2 The expiry is load-bearing

2026-10-05 is also when Verification C's window opens. That coincidence is the experimental
design, not a scheduling accident. Gross zero is measurable only once the credit is gone.
**The credit ending is the instrument.** Any action that extends, replaces, or renews it
destroys the measurement — see §5 and §7.4.

### 1.3 Two facts confirmed against vendor documentation

- The account upgrade scheduled for 2026-09-21 **does not forfeit the credit.** Upgrading to a
  paid billing account ends the Free Trial but unused credit survives to its own expiry, and
  Free Tier access continues alongside it. The operative deadline is 2026-10-05, not 09-21.
  The 09-21 date is C1, pinned in [`F2-completion-directive.md`](../specs/F2-completion-directive.md)
  F2C-18 — *"Pinned to 2026-09-21"* — rather than a ceiling that could drift.
- After 2026-10-05 the account is a paid account with no credit. Usage beyond Free Tier limits
  is charged to the payment method. The kill-switch is then the only layer between this project
  and a real charge — and its current `detach_threshold` of 200.00 has never been live-fired.
  The recorded live-fire (A2.12) ran against 5.00. Mechanism Proven; configuration Configured.
  Both halves are already recorded: [`ADR-0004`](ADR-0004-zero-cost-guardrails-kill-switch.md):690
  — *"Until that run is archived, this amendment describes a configuration, not a control"* —
  and [`f2-detach-threshold-200-applied.md`](../evidence/f2-detach-threshold-200-applied.md):46.

### 1.4 A question two pieces of evidence disagree about

`#74` records a mechanism argument, not an assumption, and this ADR must engage it rather
than restate it as framing:

> Billing Reports for August show TRY 0.04 gross against Cloud Run functions CPU, TRY 0.04 in
> savings, TRY 0.00 subtotal. The budget — which filters on `FREE_TIER` credits only — reports
> the gross figure unchanged, which is the evidence that the credit doing the offsetting is
> the trial credit and not an Always Free discount.

Against it stands one arithmetic observation: **remaining equals promo value exactly.** Had
the promo credit absorbed ₺0.04, remaining would read 13,987.50, which is representable at the
displayed precision.

So this is not "`#74` assumed and this ADR hypothesises". It is two readings of the same
month that cannot both be right, and the ADR takes no position. It is settled by one read of
the cost export broken down by credit type — §3.1 — and that read is a precondition because
the campaign's own cost attribution depends on which reading holds. If the arithmetic
observation wins, `#74`'s framing inverts and the zero-cost envelope already rests on Always
Free; `#74`'s wording changes with it.

### 1.5 The problem the credit can solve

Two open items share a solution and a funding source:

- **Emulator/production fidelity.** The carried obligation is
  [`F2-completion-note.md`](../specs/F2-completion-note.md):165 — *"The emulator/production
  divergence is real and only half-measured… Architecture §8 rests the local-first model on
  emulator fidelity. Carried to F3."* Its failure mode is a false green, and F3's central
  deliverable is a CI gate whose verdict is meant to be trusted. Closing it requires
  exercising real BigQuery, Pub/Sub and Cloud Run at volumes the zero-cost invariant
  otherwise forbids.

  The reachable half was closed on 2026-09-02 without spending anything: T1-05 constrains the
  repository where the engine cannot be constrained, and T1-01 was closed as unsatisfiable
  because the local stand-in cannot create a partitioned table at all. **What the credit buys
  is the half neither of those reaches** — behaviour under real load against the real engine.
- **T2-01 disposition (a)/(c).** Adjudicator instrumentation sits on F3's critical path
  because E1 is computed over R1 ∧ R2 ∧ R3 ∧ R4 and **all four conjuncts are computed from
  the trace** ([`eval-plan.md`](../eval-plan.md) §8.1), which the Adjudicator does not emit.
  F3's hour budget — `project-brief.md`:59, ~20h — was set against a scope that excluded
  instrumentation.

Both require running the real pipeline under real load. That is precisely what the credit
funds, in the only window where funding it is free.

---

## 2. Decision

**D1.** Expiring trial credit may be spent as a **measurement instrument** before the
measurement window opens. It may not be spent for capacity, for schedule relief, or for
convenience. The distinction is testable: an expenditure qualifies only if its output is
evidence about the system, not throughput from the system.

**D2.** The expenditure is **gated on T2-01's disposition** (`#177`) and does not activate
until that disposition is recorded.

**The gate is not "disposition (b) means spend nothing".** v0.1 said so, on the premise that
(b) removes R3 and therefore removes instrumentation from F3. That premise is false: every
conjunct of E1 is trace-computed, so (b) is a redesign of the endpoint rather than a
narrowing of it, and a redesigned endpoint may still require the trace. The correct gate is
therefore **conditional on what (b) turns out to be**, not on the label:

| Recorded disposition | This ADR |
|---|---|
| (a) or (c) | Activates. D3's deliverables stand |
| (b), and the replacement endpoint needs no trace | Charter largely lost; D1's correct application is to spend nothing |
| (b), and the replacement endpoint still needs a trace | Activates, with D3's first deliverable intact |

Lane A does not decide which. The disposition is Lane C and `#177` names the three options
without recommending one.

**D3.** Under an activating disposition, the expenditure takes the form of **one campaign with
four declared deliverables**, not a standing allowance:

| Deliverable | Charter | State read 2026-09-03 |
|---|---|---|
| Adjudicator emits OTLP through the real pipeline | T2-01 disposition (a)/(c) | no instrumentation at all |
| SC-1 advances **0/3 → 3/3** with captured, not hand-authored, corpora | `eval-plan.md` SC-1 row 1.2 | **0 of 4 manifests read `captured`** |
| Emulator/production fidelity closed under real load | `F2-completion-note.md`:165 | reachable half closed 2026-09-02; this is the rest |
| Collector p95 overhead and RAM ceiling documented | Project Brief success criteria | not gathered |

**SC-1 is at 0/3, not 2/3, and the difference is the largest scope correction in this
revision.** Read 2026-09-03 from `testdata/fixtures/*/manifest.yaml`: `claude-code` is
`derived-from-measured-evidence`, `dotnet-agent`, `langgraph-python` and `unknown` are
`constructed`. None is `captured`. The "2/3" in v0.1 inherited F3E-02's superseded claim that
two emitters were unblocked; `langgraph-python` **is** the Adjudicator, and it emits nothing,
so its capture is downstream of this campaign's own first deliverable. `claude-code` is
blocked at authentication (`#10`). The campaign therefore carries three captures, ordered,
not one.

**D4.** The campaign declares, before it starts, the set of resources and configuration
changes it **intends to leave behind permanently** — Adjudicator instrumentation is one, load
generation is not. Anything present afterwards that is neither in the pre-campaign snapshot
(§3.2) nor in this declared set is residue.

**D5.** Residue-zero is proven **by identity, not by absence**: the post-campaign inventory
equals snapshot plus declared additions, exactly. Proof is an API read of the resource
inventory. A `destroy` returning success is not proof.

That rule is this project's recurring finding rather than a new one. Its most recent
instances, both 2026-09-02: a dedup view with its predicate deleted passed every golden file
because no duplicate existed for it to mishandle, and 125 tests passed against a table
definition stripped of `require_partition_filter` because nothing asserted it. *"The view
returned one row"* and *"the destroy returned success"* are the same shape — co-existence
offered where identity was required.

**D6.** Teardown completes and is proven by **2026-10-01**, not 10-04. Two reasons: a failed
teardown needs repair time before the credit expires, and **10-04 is not merely contested —
it is C7's own constraint and C7 is already blocked.**
[`F2-completion-directive.md`](../specs/F2-completion-directive.md) F2C-19 states it:
*"F3 exit + three emitters ingest-ready ≤ 2026-10-04"*, *"Blocked by: Freeze A, the F3 entry
gate"*, and *"That question has no scheduled session."* A campaign planning teardown for 10-04
would be planning against a date its own prerequisite does not hold.

---

## 3. Preconditions

None of these is optional and none may be satisfied retroactively. Every one exists because
the campaign's evidence is worthless without it.

### 3.1 Cost baseline, read not assumed

Current cost broken down by `project_id` **and** by
credit type. This settles §1.4 and establishes what the campaign's consumption is measured
against. Without it, post-campaign cost cannot be attributed to the campaign.

**This read is Lane C.** Attempted from Lane A on 2026-09-03 and refused at the permission
layer: `gcloud billing accounts list` was denied. Per the standing rule the denial is reported
once and not routed around. §1.1's figures and §1.4's question both wait on it.

### 3.2 Resource inventory snapshot

A dated API read of every resource and the configuration
values this campaign will touch. This is the identity term in D5. It is not a Terraform state
listing; state and reality are two propositions.

### 3.3 Kill-switch live-fire at 200.00

Before the campaign, not after. The campaign
deliberately raises spend against a threshold whose current value has never fired, in the
weeks immediately before the payment method becomes live. Firing it afterwards proves the
wrong thing at the wrong time.

### 3.4 Free-tier storage headroom recorded

Campaign volume lands in BigQuery and persists.
Post-teardown headroom must be comparable to a pre-campaign number.

---

## 4. Proof obligations

### 4.1 Synthetic walling

Campaign load carries `synthetic = true` and is proven walled by
query, not by the generator knowing it set the flag. The captured Adjudicator corpus is **not**
synthetic and must not be flagged as such — SC-1 row 1.2 requires a real capture, and flagging
it would make the corpus inadmissible against the criterion it exists to satisfy.

### 4.2 Excludability

Campaign rows must be excludable by query from F4's continuous-ingest
counts. Campaign volume inflating an F4 DoD number is the same defect class as a copied status
table: two different propositions with one shape.

### 4.3 Storage teardown

Synthetic partitions are deleted and §3.4's headroom re-read. BQ rows
surviving into the measurement window are residue with a cost consequence, not leftover data.

### 4.4 Fidelity findings are recorded whichever way they fall

If local and production agree,
that is the result and the carried obligation closes. If they diverge, the divergence is the
more valuable finding and F3's gate design changes. Neither outcome is a failed campaign; a
campaign that reports only the convenient direction is.

---

## 5. What this decision does not permit

- **Non-plumbline work on the same billing account.** Credits attach to a billing account, not
  a project; there is no per-project allocation of a promo credit. Consumption by other
  projects means the *account* is not at zero even if the *project* is — two propositions, one
  shape.

  **v0.1 deferred this to the cost-regime ADR. That ADR has now been read and does not settle
  it.** ADR-0004 fixes the ceiling's value and its currency — *"Stated in the billing account's
  own currency"* — and concerns the kill-switch mechanism; it does not scope the publishable
  claim. Neither pre-registered statement scopes it either: [`eval-plan.md`](../eval-plan.md):191
  row 4.5 reads *"Monthly GCP net cost"* with a billing-console method, and `project-brief.md`:19
  reads *"on GCP"*. **The ambiguity is in the pre-registered criterion, not in an ADR** — which
  makes resolving it a Class 3 edit to a human-only document, not a read. Prohibited here, and
  the prohibition now has a reason that a read cannot lift.
- **Raising `max_instances` above 2, or any other standing invariant, to buy throughput.** That
  spends a claim to save hours.
- **Extending, renewing, or accepting a replacement credit.** See §7.4.

---

## 6. Alternatives considered

**A1 — Let the credit expire unused.** The only option with zero residue risk, and the one that
forfeits the sole cheap window to close the fidelity obligation under real load. Rejected:
"safe" and "costless" are not the same, and the obligation's failure mode is a false green in
the component built to detect false greens.

**A2 — Spend it on unrelated work.** Genuine value, wrong instrument. Re-scopes the publishable
claim, which per §5 touches pre-registered ground rather than an ADR. Not rejected on merit —
deferred to its own decision, because it is a different decision with a different cost.

**A3 — Spend it on capacity to accelerate F3.** Rejected. Violates standing invariants and
converts the project's headline claim into schedule.

**A4 — Obtain further credit to extend the runway.** Rejected with prejudice. The credit ending
is the experiment. A well-intentioned future action here would silently destroy Verification C,
which is why it is written down rather than left to judgement.

---

## 7. Consequences

### 7.1 Accepted

The fidelity obligation closes under real load before F3's gate depends on
it, rather than at F3's exit. T2-01(a) becomes affordable without expanding F3's budget in real
money. SC-1 reaches 3/3 with admissible corpora — from 0/3, which is three captures rather than
one. The p95 and RAM criterion gets data that would otherwise have to be gathered after 10-05
under rationing.

### 7.2 Cost in time, stated plainly

The campaign is real hours inside a 32-day window that
already has zero buffer and one human — and D3's corrected scope makes it more hours than v0.1
budgeted, because SC-1 is three captures from done and one of them is gated on the campaign's
own first deliverable. This ADR funds the campaign in money and does not fund it in time. If
the schedule cannot absorb it, the honest response is to reduce D3's deliverables explicitly
and record which ones were dropped — not to start the campaign and let it decay.

### 7.3 Residual risk

Residue survives teardown; mitigated by D5 and §4, not eliminated.
Campaign volume contaminates F4 counts; mitigated by §4.2. Both are detectable by query, which
is the standard this project holds itself to.

### 7.4 A standing prohibition, recorded once

The credit's expiry must not be extended,
renewed, or replaced. Anyone reading this later — human or implementation layer — will be
tempted to treat expiring credit as a problem to solve. It is the instrument. Restoring the
runway would leave the project with a working pipeline and no publishable cost result.

### 7.5 An F5 dependency partly repaid

The cost-regime softening left the second blog post
("$0 on GCP with billing screenshots") without a subject. A dated instrumental expenditure with
declared intent, proven residue-zero, and a clean post-credit gross-zero measurement is a
stronger subject than an unbroken flat line — it shows the control working rather than never
being tested.

---

## 8. Enforcement

Required by [`docs/adr/README.md`](README.md), which fixes the section set and asks which
controls **prevent** a violation and which only **report** one. For this decision the honest
answer is that most of it is reported, and that is the reason the preconditions are hard.

| Obligation | Control | Prevent or report |
|---|---|---|
| Spend stays under the ceiling | Kill-switch at `detach_threshold` 200.00 | **Prevent** — but only once §3.3 live-fires it. Until then it is Configured, not Proven |
| Trajectory stays under the burn line | `architecture.md` §7 daily month-to-date check | Report |
| `max_instances ≤ 2`, region, `min_instances = 0` | `terraform static checks`, plan guard | **Prevent** |
| No resource outside the type allowlist | Plan guard (`architecture.md` §7) | **Prevent** |
| No enumerated credit filter reintroduced | Gate H, `invariant-gates.sh` | **Prevent** |
| Every query constrains `start_time` | `partition-filter-check.sh`, non-blocking | Report |
| D5 residue-zero | API inventory read against §3.2's snapshot | **Report only** — nothing prevents residue in real time |
| §4.1 synthetic walling | Query over `spans_real` / `spans_deduped` | Report |
| §4.2 excludability | Query scoped by run id | Report |
| D6 teardown by 2026-10-01 | Calendar; no mechanism | **Report only** |

**Three obligations have no preventive control at all** — D5, D6, and §4.2. They are detected
after the fact by query or not at all. That is why §3.2's snapshot is a precondition rather
than a step: without the identity term taken *before*, the only residue check available
afterwards is absence, which D5 rejects.

---

## 9. Open items this ADR does not resolve

| Item | Nature | Blocks |
|---|---|---|
| §1.4 — which of the two readings of August holds | One read of the cost export by credit type; **Lane C, refused to Lane A 2026-09-03** | §3.1, §1.1's figures, and `#74`'s wording |
| T2-01 disposition | Lane C decision, three options, none picked (`#177`) | D2 — this ADR's activation |
| Scope of the zero-cost claim: account or project | **Not an ADR read.** `eval-plan.md` row 4.5 and `project-brief.md`:19 both leave it open; settling it is a Class 3 edit to pre-registered text | §5's first bullet |

Status remains **Proposed**. A status flip is a review output, not an authoring output.

---

## 10. Provenance

Every correction in §11 names the file and line it was read from, at `main @ 418c67f` on
2026-09-03. The credit figures in §1.1 are **not** among them — they are transcribed from a
console screenshot and are exactly what §3.1 exists to replace with a read.

No line in this ADR is admissible as evidence in a closing note or a DoD table.

---

## 11. Changelog

**v0.2 — 2026-09-03** (supersedes v0.1). Five changes, each with the read that caused it.
Three are reproductions of defects this repository corrected on 2026-09-02; a correction
recorded in one document does not propagate to the next one written.

1. **"The one Missing control in the F2 controls table" is removed** (was §1.5, D3, §6 A1,
   §7.1). No table in `docs/` carries Proven/Configured/Missing states — searched 2026-09-03,
   the only controls table is [`F1-completion-note.md`](../specs/F1-completion-note.md):52,
   whose columns are Control / Class / Catches. The charter is
   [`F2-completion-note.md`](../specs/F2-completion-note.md):165. This is the same premise
   `#173` removed from the F3 prerequisite directive on 2026-09-02.
2. **D2's gate is re-specified.** v0.1 read disposition (b) as *"redefining the gate endpoint
   so it no longer requires R3"* and concluded that (b) means spend nothing.
   [`eval-plan.md`](../eval-plan.md) §8.1 defines **all four** conjuncts of E1 over the trace,
   so dropping R3 buys nothing and (b) is a redesign whose trace requirement is unknown until
   it is written. The gate is now conditional on what (b) turns out to be. `#178` made the same
   correction to T2-01's own text on 2026-09-02.
3. **SC-1 is 0/3, not 2/3** (D3, §7.1, §7.2). Read 2026-09-03 from
   `testdata/fixtures/*/manifest.yaml`: zero manifests read `captured`. The "2/3" inherited
   F3E-02's superseded claim; `langgraph-python` is the Adjudicator and emits nothing, so that
   capture is downstream of this campaign's own first deliverable, and `claude-code` is blocked
   at authentication (`#10`). Three captures, ordered — recorded in §7.2 as a cost in time.
4. **§5's deferral is replaced by a read.** v0.1 deferred the account-versus-project scope to
   the cost-regime ADR. That is ADR-0004; it has now been read and fixes the ceiling's value
   and currency, not the claim's scope. Neither `eval-plan.md`:191 row 4.5 nor
   `project-brief.md`:19 scopes it either, so the ambiguity sits in pre-registered text and
   settling it is Class 3. The prohibition stands with a reason a read cannot lift.
5. **§8 Enforcement added; two dangling references repaired.**
   [`docs/adr/README.md`](README.md) fixes the section set as Context, Decision, Alternatives
   considered, Consequences, **Enforcement**, and v0.1 had no Enforcement section. Writing it
   surfaced that three obligations — D5, D6, §4.2 — have no preventive control at all. Also:
   D5's *"fourth row of this project's central defect table"* named a table that does not exist
   (there is a central defect **class**, [`freeze-a-prep.md`](../specs/freeze-a-prep.md):397,
   not a table with rows), and the open-items row citing a *"controls-table row split recorded
   as a Lane A task"* pointed at T4-04, which `#173` closed before work began for the reason in
   change 1.

   **Caught by the cross-reference check while writing, and worth recording as such.** §1's
   subsections were `###` headings while §3, §4 and §7's were bold labels, so the document's
   own references to §3.1, §4.2, §7.2 and §7.4 resolved to nothing. The check reported four of
   them; the repair is thirteen subsections promoted to headings, which makes the numbering
   consistent rather than silencing the finding. `xref-check.sh` returns to its 13-finding
   baseline with none in this file.

**Not changed, and verified rather than assumed:** the ADR number (0009), the 09-21 upgrade
date (C1, pinned in F2C-18), the `detach_threshold` 200.00 / A2.12-at-5.00 asymmetry, and D6's
2026-10-01 teardown deadline — which the C7 read strengthened rather than weakened.
