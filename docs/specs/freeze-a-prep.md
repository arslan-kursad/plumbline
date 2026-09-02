# Freeze A — Pre-session brief

**Version:** 0.4 · **Status:** Accepted · **Date:** 2026-09-02
**Session:** 2026-09-02, 10:00–13:00 Europe/Istanbul · **Duration:** 3 h
**Freeze target:** [`docs/eval-plan.md`](../eval-plan.md) v0.2 · **Appendix A:** P1–P7, P11

> **v0.1 was a design-layer document and asserted its own state.** v0.2 is the same
> agenda checked against the repository, and the checking changed it: one out-of-scope
> item was inverted, two carried items were already closed, and two obligations that
> were on no list were found. §9 lists every change with its cause.

---

## 1. Purpose

Freeze A resolves the placeholders that gate F3. This brief exists to make those three
hours produce decisions rather than retrieval, and to force the freeze/no-freeze call
inside the session instead of discovering it afterwards.

It does not decide anything Freeze A decides. It fixes the order, the preconditions, and
the fallback.

**The session owns three outputs**, per
[`F2-completion-directive.md`](F2-completion-directive.md) Remaining Lane C item 2: the
ground-truth question answered, Freeze A performed, and `eval-plan.md` §2's stale
"F1 entry gate" line reconciled. All three, not two.

---

## 2. Preconditions

Four outstanding, two discharged. Missing preconditions are named at T+0 and the agenda
is adjusted before the session starts, not during it.

| # | Item | Feeds | Owner | State |
|---|---|---|---|---|
| C-1 | Anomaly Adjudicator raw output schema (fields, enums), input case shape, and reference-label source — written down | P1, P6 | Human | **outstanding** |
| C-2 | Apartment Triage task definition and output contract — drafted | P2 | Human | **outstanding** |
| C-3 | T1 model id + quantization, T2 model id, daily quota cap `Q` — read from current provider documentation, not from memory | P7 | Human | **outstanding** |
| C-4 | Available real case volume per agent over the 32-day window | P3 | Human | **outstanding** |
| C-5 | Claude Code scope-marker record verified against the repo, with file, line and commit | P11 | F1 capture | **discharged 2026-09-01** — see below |
| C-6 | Read-only readout: issue #68 body, DoD 1 text as written in the repo, enumerated CI gate list with names, `api-keys.md` §4 revoke command | §6 | Lane A | **discharged 2026-09-01** — see below |

**C-1 is the binding precondition.** P1 and P6 both hang on it, and P6 determines whether
E1 survives as the primary deterministic endpoint. Entering the session without C-1
converts the first hour from decision to retrieval.

**C-1 also has to answer where the output lands in the trace.** `eval-plan.md` §5.1 is
categorical: *"Evaluation of a run must be reproducible from the trace alone: if a metric
cannot be computed from persisted telemetry, it is not a valid metric here."* P1 asks for
the output contract; it does not ask whether that contract is **observable**, and R3
(*"output parses; required fields present; enum values in allowed set"*, §8.1) is computed
from the trace.

So three questions ride with the schema, and none of them is answered by the field list:

- **Where does the output land** — a span attribute, an event body, or nowhere? If nowhere,
  **R3 cannot be computed at all**, and E1 loses a conjunct of `R1∧R2∧R3∧R4`. That is an
  endpoint change, not a placeholder fill.
- **Is it truncated** by an attribute-size limit at realistic output lengths? A silently
  truncated output fails R3 for a reason that is not a regression.
- **Does it carry personal or customer-derived content?** ADR-0006 and CLAUDE.md would
  require redaction before storage, and a redacted output may not be checkable.

**C-2, C-3 and C-4 are not design decisions.** They are transcription, lookup, and
counting. They are listed as preconditions specifically so that they do not consume
session time.

### C-5 — discharged, and the path in v0.1 was wrong

The record is at
[`normalization/mappings/v1.41/claude-code.yaml`](../../normalization/mappings/v1.41/claude-code.yaml)
lines 19–20 — `scope_names: [com.anthropic.claude_code.tracing]` — committed in `6a0db21`
(2026-08-21), the file's only commit. v0.1 gave the path as `mappings/v1.41/…`, missing
the `normalization/` prefix that CLAUDE.md requires; it was flagged there as asserted and
unverified, and verifying it is what found the prefix.

Two things this does **not** settle, and P11 has to say which it means:

- Appendix A gives P11's owner as **F1 capture**, not Human. v0.1 said Human.
- Architecture §10 OQ-4 records the state as *"scope marker measured; tool/hook spans
  still unobserved"*, and `#10` is open on the capture procedure — the beta gate, the
  mandatory redaction, and the unobserved span types. The detection markers are measured.
  The dialect is not fully observed.

### C-6 — discharged, and it removed more than it added

The readout is the source for §6.1 below. Its four items are all in
[`f2-dod1-five-facts.md`](../evidence/f2-dod1-five-facts.md), in `#138`, in the merged
`#126` fix, and in the enumeration in §6.1. Reading them closed two of §6.1's three
carried items outright.

---

## 3. Out of scope for this session

- **Writing the F3 spec.** It follows the freeze; it does not share the session.
- **Deciding ADR-0008 / `#68`.** Scheduled separately for **2026-09-03**, thirty minutes.
  The decision needs no evaluation-plan context and Freeze A has no slack to lend it
  (§4). Recorded in the closure note's dated obligations and in the directive's Remaining
  Lane C item 3.
- **Closing DoD 1.** Measured on 2026-09-01 and carried to F2 closure, not here. See §6.1.
- **The SC-1 / SC-2 / SC-4b audit.** Opened as `#138`, milestone F3, its ADR due
  Accepted before 2026-10-05. §6.2 states what it carries and why it is not this session.
- **Freeze B placeholders (P8, P9, P10).** Not in scope for Freeze A and not discussed.

### What v0.1 put here and v0.2 removes

v0.1 listed *"any correction to `docs/eval-plan.md` §2"* as out of scope, on a
do-not-fix list, and called correcting it **"a pre-registration violation, not a typo
fix."**

**That was wrong, and it inverted a standing obligation.** Three sites in the repository
say the opposite, and one of them charters this session:

- [`F2-completion-directive.md`](F2-completion-directive.md) Remaining Lane C item 2 —
  the session's third named output is *"`docs/eval-plan.md` §2's stale 'F1 entry gate'
  line reconciled."*
- `#35` (closed, D1 ratified at the F1 exit review on 2026-08-21) — *"reconcile
  `docs/eval-plan.md` §2 as part of performing Freeze A — the same human action, the same
  commit, so the plan is never edited by the phase it governs."*
- [`project-brief.md`](../project-brief.md), amendment note — *"it still says 'F1 entry
  gate' and is stale on that line until the human performing Freeze A reconciles it
  (issue #36)."*

The category error is in the phrase "pre-registration violation". `eval-plan.md` carries
**Status: DRAFT — NOT FROZEN**, and §12's change control is explicit that it governs
changes *after* freeze. Correcting a line whose staleness has been recorded since
2026-08-21, before the freeze, is the reconciliation. Tagging a v0.2 that still misstates
its own freeze gate is what would need an ADR to undo afterwards.

**§2 reconciliation is in scope.** Confirmed with the maintainer 2026-09-01. Note it has
**two** occurrences, not one:

1. the Freeze A table row — `| **Freeze A** | F1 entry gate (human action) | … |`
2. the prose above it — *"no agent data exists at the F1 entry gate"*

---

## 4. Decision order

Ordered by dependency. P6 is a branch point: its outcome changes the cost of everything
after it, so the remainder of the agenda is re-planned once, in-session, rather than
pre-planned on an assumption.

| Clock | Item | Output |
|---|---|---|
| T+0 – T+10 | Precondition check against §2 | Missing preconditions named; agenda adjusted before starting |
| T+10 – T+50 | **P1** — Adjudicator task definition and output contract | Fields and enums fixed |
| T+50 – T+90 | **P6** — reference-label sourcing procedure and stratification keys | Scenario A, B or C determined; E1 viability settled |
| T+90 – T+100 | **Re-plan** | Order and time budget for P4 / P5 set per §4.1 |
| T+100 – T+125 | **P3** — `N_gate` and achieved MDE from C-4 | If volume cannot support the MDE, the gate design changes — not the threshold |
| T+125 – T+150 | **P4 / P5** in the order set at T+90 | |
| T+150 – T+160 | **Freeze decision** per §5 | Binding; not deferred past this mark |
| T+160 – T+180 | Remaining P4 / P5 work, then P11 close-out, then the §2 and §7 v0.2 edits | |

**The agenda is exactly the session, with zero slack.** Three hours is 180 minutes and the
agenda runs to T+180. v0.1 was written against a repository that recorded the session as
10:00–12:00; that was a transcription error — the scheduling commit `4a1d370` says
10:00–13:00 in its own message — and it is corrected on `main`. The correction removes the
defect where the freeze decision fell after the session ended. It does not create slack.

**T+160–T+180 is lighter than v0.1 assumed** because §6.1 emptied (see §6.1), and heavier
because the §2 and §7 edits moved into it from nowhere. Net, it is the same twenty minutes
carrying different work.

### 4.1 The P6 branch

| Scenario | Reading | Consequence for the remainder |
|---|---|---|
| **A** — discrete verdict, per-item ground truth available | E1 viable as primary | P4 carries the load; P5 is secondary. Run P4 first |
| **B** — discrete verdict, no ground truth | E1 reduces to contract-pass-rate | P4 and P5 both load-bearing; the gate's endpoint definition needs re-reading against the plan |
| **C** — free-text output | E2 becomes primary | P5 carries the load; run P5 first, and expect it to overrun. The eval-plan's endpoint architecture is affected, which is an ADR, not a placeholder fill |

Scenario C is the one that does not fit in the session. If P6 lands on C, §5 option (b)
is the expected outcome and should be taken at T+150 without further debate.

### 4.2 The degradation catalog has unstated preconditions on the subject

`eval-plan.md` §7.2's six degradations are **frozen at Freeze A**. Three of them assume
properties of the Adjudicator that nothing in this repository confirms, and a freeze would
pin a variant that cannot be built.

| Variant | Assumes | Confirmed by |
|---|---|---|
| **D2 — prompt ablation**, the **primary** case | the system prompt has a distinguishable constraint/rubric section, removable as a single-factor change with no other diff | C-1 |
| D4 — context truncated to 1 item | an input carries more than one evidence item | C-1 |
| D5 — tool errors caught and ignored | the agent calls tools, and has error handling that can be made to swallow | C-1 |

**D2 is the one that changes the session.** §7.2 makes it primary deliberately — *"the
hardest realistic regression, because the agent keeps producing structurally valid output
and only quality degrades"* — and notes that a gate catching only D6 catches crashes rather
than regressions.

**If the prompt has no separable constraint section, the primary experimental case has to
be redesigned.** That is not a placeholder fill; it is a change to the experiment design
Freeze A exists to fix, and it lands in §5 option (b) the same way scenario C does.

Checked at T+0 with the rest of §2, not discovered at T+125 when P4 is being written.

---

## 5. The freeze decision at T+150

`eval-plan.md` Appendix A, verbatim:

> No placeholder is filled by assumption. An unresolved placeholder blocks its freeze
> stage; it does not degrade into a default.

That rule is load-bearing and is not being relaxed here.

It has a consequence worth stating before the session rather than discovering after it:
on the agenda above, **P5 is the most likely item to be left unfinished, and that is a
predicted outcome, not an accident.** Freeze A is currently all-or-nothing, so an
unfinished P5 blocks the freeze and therefore blocks the F3 spec.

At T+150 exactly one of the following is chosen and recorded:

- **(a) Second session.** Freeze A does not complete today; a dated follow-up session is
  fixed before the session ends. Cost: days out of the 32 available before 2026-10-04,
  taken from the phase with no buffer.
- **(b) Freeze restructuring ADR.** Freeze A is split into stages so the gate-critical
  placeholders can freeze on schedule and the remainder freezes separately. This changes
  the freeze mechanics of a pre-registration document, so it requires an ADR under
  `eval-plan.md` §12 change control — stating what changed, why, and what data had already
  been observed at the time of the proposal. It is not an informal deferral.

**(c) — leaving placeholders open without choosing (a) or (b) — is not available.** It
reads as a completed freeze and is the project's central defect class in its exact
canonical form.

---

## 6. Carried items

### 6.1 What the C-6 readout did to this section

v0.1 listed three items here and budgeted session time for all three. **Two were already
closed and the third is not Freeze A's.** Reading them is what established that.

| Item | v0.1 said | Measured 2026-09-01 |
|---|---|---|
| `#68` — "two different meanings 24 h apart" | Read the issue; restore the ADR-0008 carry or record that it closed; if the OTLP/gRPC reading is real, **open the ADR** | **No contradiction existed.** `#68` has one meaning in this repository, and every reference to it — in `architecture.md`, ADR-0008, the F2 decision log, the F2 completion note and the F2 completion directive — agrees with it. **ADR-0008 already exists** — Proposed, 2026-08-26 — so there is no ADR to open. Its status is a review output the directive says explicitly not to flip; that review is dated 2026-09-03 and is out of scope here (§3) |
| DoD 1 — "wording moved between documents" | Read the item's text; make both documents agree | **Both texts are real and neither is a paraphrase.** §3's gate row asserts an ordering; §7 item 1 asserts five completion facts. Measured fact by fact in [`f2-dod1-five-facts.md`](../evidence/f2-dod1-five-facts.md): three hold, one is a state claim written as an event claim, one has a referent that moved. **F2 closure work, not Freeze A's** |
| DoD 12 — "gate count moved from eight to nine" | Name the ninth gate from the enumerated CI list | **Already closed in the repo.** [`f2-dod-1-2-5-12-rederived.md`](../evidence/f2-dod-1-2-5-12-rederived.md), 2026-09-01, enumerates all nine by name against run [`33475352691`](https://github.com/arslan-kursad/plumbline/actions/runs/33475352691). Eight lettered gates A–H; the ninth assertion is **`Gate B coverage`**, which has no letter |

**§6.1 carries nothing into the session.** That is the readout paying for itself, and it
is also the reason v0.1's cost estimate for this section was wrong in the safe direction.

**One consequence survives and is not documentation hygiene.** gRPC ingest does not exist
in the deployed system: Cloud Run routes one port, the collector serves HTTP there, and
the gRPC listener starts in the container with nothing routed to it. If ADR-0008 lands on
HTTP-only, **all three emitters must use OTLP/HTTP**, and that constraint has to reach the
instrumentation work in writing before it starts. The decision is 09-03; the constraint
is F4's.

### 6.2 Deferred out of the session, with a deadline — now `#138`

The Brief's success criteria are pre-registered. Amending one after the measurement window
opens is a post-hoc change; amending one before it opens is a protocol amendment. The
window opens **2026-10-05** (`#74`), so that — not the drafting of the blog series — is
the operative deadline.

v0.1 asserted all three criteria fail in the same shape. **They do not.** Checked against
the repository, they take three different dispositions:

| Criterion | As written | Disposition |
|---|---|---|
| SC-4b | `$0.00` for two consecutive calendar months | **Amend by ADR.** Row 4.5 does not say gross or billed, and that is the whole question. Gross cost is non-zero until the credit ends 2026-10-05, so two gross-zero months fall in November–December |
| SC-2 | 14 days uninterrupted live ingest from 3 real sources | **Define, before 2026-10-05.** Not undefined — `eval-plan.md` row 2.1 already operationalizes it as `≥1 span with synthetic=false per source per UTC day`, which is materially weaker than the word it will be reported under. And its primary metric is a staffing commitment: one of the three sources emits only when a human runs a session (`C6`) |
| SC-1 | ≥3 dialects normalized with golden tests | **Do not touch.** v0.1 had this wrong. Row 1.2 already requires *"≥1 fixture per dialect captured from a real emitter, not hand-authored"* and makes a manifest-incomplete fixture inadmissible. The criterion is correct; the fixture set is not (`#42`). Weakening a correct criterion to match non-compliant artefacts is the bad kind of amendment |

**SC-1's removal converts a criterion problem into a schedule problem.** Three captures
are owed, not one: `langgraph-python` and `dotnet-agent` are the maintainer's own agents
and are blocked on nothing; `claude-code` is the hard one, behind `#10`.

**Disposition: one issue, one ADR** — SC-4b's basis and SC-2's definition. SC-1 needs no
ADR because nothing about it is being amended. Opened as `#138`, milestone F3, ADR
**Accepted before 2026-10-05**.

---

## 7. Exit condition

Freeze A is complete when, and only when:

1. **P1–P7 and P11** are recorded in `docs/eval-plan.md` v0.2 with their values, not their
   intentions.
2. **§2 is reconciled** — both occurrences of "F1 entry gate" (§3). This is the session's
   third chartered output, not an optional extra.
3. **`#36` is discharged** — SC-1 row 1.4 aligned with the vendored registry **and**
   `normalization/semconv/v1.41/external-allowlist.yaml`. The row currently names the
   vendored registry and not the allowlist. `#36`'s own target is *"Freeze A (F3 entry
   gate) — the same human action that reconciles §2"*.
4. **`#10`'s eval-plan half is discharged** — SC-1 row 1.2's manifest field set gains
   `redacted_fields`. A redacted capture is not raw emitter output, and row 1.3's
   losslessness check has to say which artefact it validates against.
5. **SC-1 row 1.1's data source is corrected** — see §7.1. It names a directory that does
   not exist.
6. **§4's `architecture.md` pin is refreshed** — v0.3 is ten versions stale (§7.1).
7. The file is on `main` and its SHA is tagged `eval-plan-freeze-a`, per §2's freeze
   mechanic.
8. If the freeze did not complete, the §5 choice — (a) or (b) — is recorded with its date.

**Items 3–6 appeared on no list before this brief was checked against the repository.**
All four are `eval-plan.md` v0.2 edits, and all four would have been frozen wrong and then
needed an ADR under §12 to correct.

### 7.1 Pre-freeze audit of the file being frozen — 2026-09-01

Lane A read `eval-plan.md` against the repository: every internal `§` reference against
this file's own headings, every cross-document reference against the cited document's
headings, and every path it names against the filesystem. Four findings; two are exit
conditions above, two are not defects.

**Clean:** all internal section references resolve. Every `architecture.md` section the
plan cites — `architecture.md` §3.3 (dedup), §4.1 (`spans_deduped`/`spans_real`/
`synthetic`), §4.2 (`datasets`/`eval_runs`), §5, §7, §10 OQ-1 and OQ-4 — exists and still
says what the plan says it says. **Each is written against `architecture.md` and not as a
bare number**, because three of them — §4.1, §4.2 and §5 — are also section numbers *this*
document has, and a bare reference would resolve locally and silently to the wrong one.

**Finding 1 — SC-1 row 1.1 names a directory that does not exist.** The row's data-source
column reads `normalization/testdata/<dialect>/`. That string occurs **once in the whole
repository, in this row**. The corpus is at `testdata/fixtures/<dialect>/`, which is what
the tests actually read — `worker/Plumbline.Normalization.Tests/FixtureCorpus.cs:80` and
`worker/Plumbline.Worker.Tests/IngestionEndpointTests.cs:152`. Freezing it as written
pins the primary criterion's primary data source to a path nothing uses.

**Finding 2 — §4 pins `architecture.md` at v0.3; `main` carries v0.13.** Only the pin is
stale: every section it cites still resolves and still carries the cited content. Worth
correcting rather than leaving, because a pre-registration that names a version of its
context file which no longer exists cannot be checked against that version later.

**Finding 3 — `redacted_fields` already exists in all four fixture manifests.** So `#10`'s
row 1.2 edit (§7 item 4) is the criterion catching up to the artefacts, not a new
requirement being imposed on them. The manifests carry more than row 1.2 names —
`provenance`, `construction_basis`, `evidence`, `synthetic_values`, `redaction_rules`,
`validation_status`. Whether row 1.2's list should grow to match is a decision, not a
transcription, and is not proposed here.

**Finding 4 — no fixture declares itself `captured`, in its own manifest.** Three read
`provenance: constructed`; `claude-code` reads
`provenance: derived-from-measured-evidence` and explains at length why it is not
`captured` — the raw capture was never committed, and no `claude_code.tool` or
`claude_code.hook` span was ever produced because every captured run failed
authentication before reaching a tool call. Row 1.2 requires *"≥1 fixture per dialect
captured from a real emitter"*.

**So SC-1 is unmet on the corpus's own self-declaration, not on an outside reading.** That
is `#138`'s SC-1 disposition — do not amend the criterion, schedule the three captures —
confirmed from the artefacts rather than argued from the plan.

The `eval-plan.md` edit is Class 3 and human-only. It is not delegated to the
implementation layer, and this brief does not authorize it.

---

## 8. Provenance

**v0.1** was derived on 2026-09-01 from a design-layer project-context document, and every
state claim in it was a claim from that document rather than from a repository read. Its
own §8 said so and instructed that it not be cited as evidence.

**v0.2 is that document checked against the repository**, on `main` at `6a739c6`, with the
GitHub API for issue and milestone state. Each correction in §9 names what was read. The
readings are reproducible and the artefacts they produced are in the repository:
[`f2-dod1-five-facts.md`](../evidence/f2-dod1-five-facts.md), `#138`, and the merged
`#126` fix.

**The instruction from v0.1 §8 stands, narrowed.** This brief is a plan, not evidence.
Where §6 names a measurement, cite the evidence file or the run — not this file. Where it
names an obligation, the issue is the record. What this document is authoritative for is
the *order of the session* and nothing else.

**One measurement is recorded as unread rather than assumed.** Whether the deployed budget
still carries Amendment 4's credit filter today was not read: `.claude/settings.json`
denies `Bash(gcloud billing:*)`, which refuses `budgets list` — a read — for sharing a
prefix with the commands that detach billing. It bears on DoD 1 fact 5, not on Freeze A.

---

## 9. Changelog

**v0.2 — 2026-09-01** (supersedes v0.1). Seven changes, each with the read that caused it.

1. **Session duration corrected to three hours** (header, §4). v0.1 said 3 h; the
   repository recorded 10:00–12:00 at two sites. The scheduling commit `4a1d370` says
   10:00–13:00 in its own message, so the files were wrong and are fixed on `main`. Under
   the 120-minute reading the T+150 freeze decision fell thirty minutes after the session
   ended — the one output this brief exists to force.
2. **The `eval-plan.md` §2 do-not-fix item is removed and inverted** (§3). It contradicted
   the directive that charters this session, a closed and ratified issue (`#35`), and the
   Project Brief's own amendment note. `eval-plan.md` is not frozen, so §12 does not yet
   apply to it. Confirmed with the maintainer.
3. **§6.1 emptied** (§6.1). `#68` had one meaning, not two; ADR-0008 already exists and
   its status flip is a dated review, not this session's work; DoD 12 was closed in the
   repository on 2026-09-01; DoD 1 is F2 closure work and was measured separately.
4. **SC-1 removed from the amendment list** (§6.2). Row 1.2 already requires real-emitter
   capture and makes manifest-incomplete fixtures inadmissible. The criterion is correct
   and the fixtures are not, which is a capture schedule, not an amendment.
5. **Two exit-condition items added** (§7 items 3 and 4). `#36` and `#10` both target
   Freeze A in their own text and appeared on no list in v0.1.
6. **C-5 and C-6 discharged; the C-5 path corrected** (§2). `normalization/` prefix,
   file, line and commit recorded. P11's owner is `F1 capture` per Appendix A, not Human.
7. **ADR-0008 moved to its own dated session** (§3). 2026-09-03, thirty minutes. It is
   unbudgeted work on the critical path to C7 and does not belong inside a freeze session
   with zero slack.

**v0.4 — 2026-09-02** (supersedes v0.3). Two additions to C-1's scope, from building its
intake form against `eval-plan.md`.

9. **C-1 must answer where the output lands in the trace** (§2). §5.1 says a metric that
   cannot be computed from persisted telemetry is not a metric here, and R3 is computed
   from the trace. P1 asks for the contract and not for its observability, so an
   Adjudicator whose output never reaches a span would satisfy P1 and leave E1 with a
   conjunct it cannot evaluate.
10. **A reference in §7.1 was silently resolving to the wrong document, and adding §4.2
    made it worse before it was caught.** §7.1's "clean" line cited
    `architecture.md` §3.3 through §10 by bare number. This document already had its own
    §4.1 and §5, so those two were
    resolving locally rather than to the architecture; adding a §4.2 heading in this
    revision extended the collision to a third, and the cross-reference check **went quiet
    rather than louder** — a false positive became a false negative. All of them are now
    written against their document. The check cannot tell "resolves correctly" from
    "collides coincidentally", which is worth knowing about it.
11. **§4.2 records that three degradations assume properties of the subject.** D2 —
    the primary case — assumes a separable constraint section in the system prompt; D4
    assumes multi-item inputs; D5 assumes tool calls. The catalog is frozen at Freeze A,
    so an unconfirmed assumption would pin a variant that cannot be built. D2's failure is
    a §5 option (b) event, like scenario C.

**v0.3 — 2026-09-01** (supersedes v0.2). One change, from reading the file being frozen
rather than the plan for freezing it.

8. **§7 gains items 5 and 6, and §7.1 records the audit that produced them.** Lane A
   checked every reference and path in `eval-plan.md` against the repository. SC-1 row
   1.1 names `normalization/testdata/<dialect>/`, a directory that exists nowhere — the
   corpus is at `testdata/fixtures/<dialect>/` and the tests read it there. §4 pins
   `architecture.md` at v0.3 against a `main` carrying v0.13. Two further findings are
   recorded as context rather than as defects: `redacted_fields` is already in all four
   manifests, and no manifest declares itself `captured`.
