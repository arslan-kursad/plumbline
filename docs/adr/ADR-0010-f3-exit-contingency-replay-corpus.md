# ADR-0010 — F3 exit contingency: gate proven against a replay corpus

**Status:** **Proposed** · **Date:** 2026-09-05 · **Deciders:** author (Lane C)
**Supersedes:** nothing · **Related:** `#177`, `#183`, `#184`, ADR-0009, C7 (F2C-19)
**Affects:** `project-brief.md` phase list; F3 exit criteria; `architecture.md` §10 index
**Number:** read from `docs/adr/` on 2026-09-05 — 0001–0009 present, 0010 next. Re-derive
before any later renumbering; do not inherit this.

Records decision **D6** of the F3 Unblock Directive v1.0 (2026-09-05), and the phase-list
correction that directive's §9.2 assigns here.

---

## 1. Context

### 1.1 What F3 exit currently means

`project-brief.md`:61 — *"DoD: seeded regression caught by the gate."* The gate reads E1,
which [`eval-plan.md`](../eval-plan.md):242 defines as `task_pass_rate` over the composite
contract `R1 ∧ R2 ∧ R3 ∧ R4`.
[`eval-plan.md`](../eval-plan.md) §8.1 defines **all four conjuncts over the trace**.

### 1.2 The subject emits nothing, and neither does the replication candidate

| Agent | Emits OTLP | Verified |
|---|---|---|
| Anomaly Adjudicator — the **primary subject** | **no** | four methods, [`c1-adjudicator-readout.md`](../evidence/c1-adjudicator-readout.md) |
| Apartment Triage — the replication candidate | **no** | four methods with live controls, [`c2-triage-readout.md`](../evidence/c2-triage-readout.md), `#183` |
| Claude Code | yes, natively | blocked on redaction, not access — [`claude-code-export-vs-capture.md`](../evidence/claude-code-export-vs-capture.md) |

So F3's exit depends on instrumentation that does not exist, in **two** repositories outside
this one.

### 1.3 The deadline is external and non-negotiable

C7, [`F2-completion-directive.md`](../specs/F2-completion-directive.md) F2C-19:

> F3 exit + three emitters ingest-ready ≤ 2026-10-04

It derives from the trial credit ending 2026-10-05, which no amount of work moves. **29 days
remain** as of this ADR's date.

### 1.4 The phase list contradicts C7, and this ADR is where that is corrected

`project-brief.md` scopes agent instrumentation to **F4** (*"instrument both real agents +
Claude Code source"*). C7 requires the emitters ingest-ready **before F3 exits**. Both cannot
hold.

**C7 wins, because it derives from an external date and the phase list does not.** The phase
list is wrong on this point. This is not a scope change to F3 — F3's scope always required
emitted telemetry, since every conjunct of its gate endpoint reads traces. What was wrong is
**F3's ~20 h budget** (`project-brief.md`:59), which was set without the instrumentation it
depends on. A mis-assigned budget corrected is not a renegotiated phase list.

---

## 2. Decision

**D6-1 — the trigger.** If the Adjudicator is not emitting OTLP satisfying the E1 predicate
inputs by **2026-09-12**, F3 exit is met by the alternative criterion in D6-2.

**D6-2 — the alternative exit criterion.**

> The gate mechanism proven against a walled-off replay corpus, with the subject experiment —
> baseline versus deliberately degraded Adjudicator — dated to F4.

**D6-3 — the phase list is corrected here.** Agent instrumentation is F3 work, not F4 work,
for the reasoning in §1.4. `project-brief.md`'s phase list is stale on that line until it is
edited; this ADR is the decision record, and the Brief is the summary.

**D6-4 — replay is the evidence shape either way.** Whether or not the trigger fires, the
seeded-regression experiment runs against a corpus captured from the instrumented Adjudicator
rather than against live traffic. A pre-registered experiment must be re-runnable, and
[`eval-plan.md`](../eval-plan.md) SC-1 row 1.2 requires fixtures *"captured from a real
emitter, not hand-authored"*. Replay satisfies both; live traffic satisfies neither on its
own.

---

## 3. The trigger is necessary but not sufficient, and this ADR does not hide that

**Recorded because U-00 found it on the day this ADR was drafted.**

D6-1 is written against the Adjudicator alone. C7 requires **three emitters ingest-ready**.
On 2026-09-05:

| Emitter | State if D6-1 is satisfied on 2026-09-12 |
|---|---|
| Adjudicator | emitting — trigger satisfied |
| Apartment Triage | **still needs a second instrumentation project** (`#183`) |
| Claude Code | needs environment config and redaction, not access |

**So satisfying D6-1 does not satisfy C7.** An Adjudicator emitting on 2026-09-12 leaves two
of three emitters short of *ingest-ready*.

This is a gap between D6 and C7 rather than an error in either. **This ADR does not close
it**, because closing it means reinterpreting a phase-exit item, which is Lane C's. It is
named here so the gap is not discovered at the trigger date, which is the same failure mode
D6 exists to prevent one level up.

---

## 4. Cost, stated plainly and not softened

**This removes differentiator 3 from F3 exit.** `project-brief.md`:17 —
*"Pre-registered evaluation criteria and a seeded-regression controlled experiment (baseline
agent vs deliberately degraded version; the gate must catch it)."* Under D6-2 the gate
mechanism is proven and the controlled experiment moves to F4.

**It is the second headline claim to move in four days.** The first was the cost regime:
ADR-0004 Amendment 5 withdrew *"$0.00 on GCP Always Free"* on 2026-09-02 and replaced it with
a 200 TRY net ceiling, which left the second blog post without its subject.

**Each move is individually defensible. Nobody is tracking the sum.**
[`claims-ledger.md`](../claims-ledger.md) exists to start tracking it and already records
both: claim 4 partial, claim 3 partial. If D6 fires, claim 3 moves again and the ledger row
must move with it **in the same change**, not afterwards.

---

## 5. Alternatives considered

**A1 — let C7 slip and keep the experiment in F3.** Rejected. F2C-19 records the cost: the
block splits, Verification C runs on an idle or synthetic-only system, and the cost result
degrades from *"gross $0.00 under real load"* to *"gross $0.00 while idle"* — *"a materially
weaker claim, and a month to redo"*. **That trades differentiator 4 to save differentiator 3**,
and it trades a measurement that cannot be repeated for one that can.

**A2 — redefine the gate endpoint so it does not read traces.** Rejected, and this is `#177`
option (b), rejected as D1 of the same directive. The claim under test is that OTel GenAI
telemetry suffices to evaluate an agent. A gate reading anything else makes the ingestion and
normalization stack decorative and drops differentiators 1 and 3 together. **Dropping R3
alone is not a partial form of this** — all four conjuncts are trace-derived, so there is no
reduced version.

**A3 — instrument only the Adjudicator and declare C7 met.** Rejected on the reading in §3:
C7 says three emitters, and one is not three. Recorded as an alternative because it is the
one a reader in a hurry would take.

**A4 — pre-register nothing and decide on 2026-10-03.** Rejected with the reasoning that
makes this ADR exist. Deciding at the deadline is deciding under duress and produces a post
hoc criterion. The cost-regime softening was done correctly — before the measurement window,
by ADR, with reasoning — and this is that shape applied a second time.

---

## 6. Consequences

**6.1 Accepted.** F3 can exit on a date C7 can meet, with the gate mechanism proven rather
than assumed. The experiment is not cancelled; it is dated.

**6.2 The budget is restated, not the scope.** F3's ~20 h excluded instrumentation. Two
instrumentation projects and three captures are now inside F3's critical path. **This ADR
does not produce a new number** — sizing B4 is `UNKNOWN — not decided` in both dossiers, and a
number invented here would be the same defect as an anchor drafted before it is approved.

**6.3 Residual risk, named.** If the trigger fires and the F4 experiment then slips, the
project ships a gate that was never run against the regression it was built to catch. **The
mitigation is that D6-2 requires the mechanism to be *proven* against the replay corpus**, not
merely built — a seeded regression in the corpus, caught by the gate, with both runs recorded.
A gate that has only been seen green is decoration, which is the standing rule this project
applies everywhere else.

**6.4 A pre-registration edit becomes due.** F3 exit criteria are pre-registered. A
conditional exit criterion is still a criterion, so `eval-plan.md` and `project-brief.md` both
carry text this decision changes. **Neither is edited here** — both are Class 3, human-only,
and `eval-plan.md` edits belong to Freeze A. This ADR is the decision; the documents are the
summary, and where they disagree with it the ADR is the record.

---

## 7. Enforcement

Which controls **prevent** a violation of this decision and which only **report** one.

| Obligation | Control | Prevent or report |
|---|---|---|
| No F3 deliverable before Freeze A | `F3-entry-directive.md` §2; directive stop conditions | **Report only** — no mechanism |
| The replay corpus is captured, not hand-authored | `manifest_validate.py`, `provenance` field, asserted in CI | **Prevent** |
| Corpus rows are walled off from real-traffic counts | `synthetic = true`, `spans_real` excludes them | **Prevent** |
| The gate is observed red as well as green (§6.3) | none today — the gate does not exist | **Report only** |
| The trigger is evaluated on 2026-09-12 | calendar | **Report only** |
| Claim 3's ledger row moves when D6 fires | none | **Report only** |

**Four of six have no preventive control.** That is the honest position and it is why the
trigger date is written into a decision record rather than left to judgement: the only
enforcement available for most of this is that it is written down where someone will read it.

---

## 8. Open items this ADR does not resolve

| Item | Nature | Blocks |
|---|---|---|
| The D6-1 / C7 gap (§3) | Lane C — reinterpreting a phase-exit item | whether C7 can be met at all |
| Instrumentation sizing (B4, both dossiers) | not decided — depends on how much state is exported | F3's restated budget |
| `project-brief.md` phase-list edit | Class 3, human | the Brief agreeing with this ADR |
| `eval-plan.md` exit-criterion text | Class 3, Freeze A | pre-registration agreeing with this ADR |

Status remains **Proposed**. A status flip is a review output, not an authoring output.
