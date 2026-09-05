# U-00 — the 2026-09-03 surface, re-derived

**Read:** 2026-09-05 · **Lane:** A · **Repo:** `main @ f64a0bc`
**Task:** F3 Unblock Directive v1.0 (2026-09-05) U-00 — **not in the repository**; see below
**Supersedes as evidence:** the Lane A F3 status report of 2026-09-03, which was produced
against `main @ 8e8a232` and which no task in that directive may cite.

**What would have falsified this readout:** any of the items below still standing as the
2026-09-03 report described them. Eleven were checked; **seven have moved**.

---

## The headline: Wave 1 and Wave 2 are already delivered

The directive's own Wave 1 and Wave 2 sections name ten output files. **Nine of the ten exist on `main`
today**, merged 2026-09-04 under `#185` and `#186` — one day after the source report and
one day before the directive was written.

| Task | Named output | State |
|---|---|---|
| U-00 | `f3-status-rederivation-2026-09-05.md` | **this file** — the only one missing |
| U-01 | `c2-triage-readout.md` | **exists**, merged `#185` |
| U-02 | `e1-predicate-readout.md` | **exists**, merged `#185` |
| U-03 | (readout + correction) | **exists** — addendum in `c2-triage-readout.md` |
| U-04 | `f2-dod-8-9-10-semantics.md` | **exists**, merged `#185` |
| U-05 | `claude-code-export-vs-capture.md` | **exists**, merged `#185` |
| U-06 | `claims-ledger.md` | **exists**, merged `#185` |
| U-07 | `proposals/freeze-a-items-2-6.md` | **exists**, merged `#185` |
| U-08 | `p3-volume-mde-table.md` | **exists**, merged `#185` |
| U-09 | `p5-rubric-inputs.md` | **exists**, merged `#185` |
| U-11 | F3E-01c tracker issue | **exists** — `#184` |
| U-12 | `runbooks/pre-credit-end-reset.md` | **exists**, merged `#185` |
| U-10 | (two carried dispatches) | **superseded** — see below |
| U-13 | deny-list rewrite, prepared | **not started** |
| U-14 | D6 contingency ADR | **not started** |

**So the directive's blocking pair — U-01 and U-02, which §12 says everything downstream
waits on — returned two days before the directive was issued.** Nothing downstream is
blocked on them.

---

## Item-by-item re-derivation

### 1 · Date and the C7 countdown — **correct**

Machine clock reads **2026-09-05**. C7 is 2026-10-04. **29 days**, which is the figure the
directive's closing line states. No correction.

### 2 · PR merge states — **all five merged**

The directive asks for the merge state of five PRs. Read through the issues API 2026-09-05:

| PR | State |
|---|---|
| `#176` T1-02 write-path classification | **merged** |
| `#179` T1-03 local duplicates | **merged** |
| `#180` T1-05 partition-filter check | **merged** |
| `#181` T3-01 400 discriminator | **merged** |
| `#182` ADR-0009 | **merged** |

**Two the directive does not know about**, both merged 2026-09-04: `#185` (Wave 1 and 2
outputs) and `#186` (C-2 dossier filled).

### 3 · F3 milestone open issues — **seven, not five**

The directive's §5 context list names `#177`, `#175`, `#138`, `#74`, `#36`. Read
2026-09-05, the milestone holds **seven**:

| Issue | Status vs the directive |
|---|---|
| `#36`, `#74`, `#138`, `#175`, `#177` | known |
| **`#183`** Apartment Triage emits no OTLP | **new** — filed 2026-09-03 by U-01 |
| **`#184`** F3E-01c round-trip probe | **new** — filed 2026-09-03 by U-11 |

### 4 · ADR-0008 disposition — **no record; §9.3's concern is confirmed**

`ADR-0008-single-port-otlp-multiplexing.md`:3 still reads **`Status: Proposed`**, dated
2026-08-26. `architecture.md`:450's index agrees. The transport review was scheduled for
2026-09-03 as its own session; **nothing in the repository records that it occurred or what
it decided.**

Corroborating the directive's §9.3: `architecture.md` still advertises gRPC ingest at
`:37`, `:38` and `:63` (*"OTLP receive (HTTP `4318` + gRPC `4317`)"*).

**This is not a Lane A finding to resolve.** Per the standing directive in
[`F2-completion-directive.md`](../specs/F2-completion-directive.md), ADR-0008's status flip is
forbidden to Lane A, and §4.2 of the current directive repeats it. Recorded, not acted on.
It joins D2's scheduling problem, as the directive's own conflicts section says it should.

### 5 · SC-1 provenance counts — **unchanged at 0 of 4**

Read 2026-09-05 from `testdata/fixtures/*/manifest.yaml`:

| Dialect | `provenance` |
|---|---|
| `claude-code` | `derived-from-measured-evidence` |
| `dotnet-agent` | `constructed` |
| `langgraph-python` | `constructed` |
| `unknown` | `constructed` |

**Zero read `captured`.** No movement since 2026-09-03. The figure "0/3" used in
`ADR-0009` and `#177` remains correct.

---

## Where the 2026-09-03 report is now wrong

Three corrections, all of them the report's own outputs having overtaken it.

**1 · "P11 YOK" — wrong, and already corrected in the repo.** The report listed P11 as
absent. U-03 established on 2026-09-03 that the scope marker **is measured** — recorded in
`normalization/mappings/v1.41/claude-code.yaml`:19-20, which states in its own comment that
it is the answer to `architecture.md` §10 OQ-4, and corroborated at `architecture.md`:465.
The correction is in `c2-triage-readout.md`'s addendum.

**The directive's U-03 anticipated the consequence and it holds:** P11 is a transcription
into Appendix A, not a decision. **Freeze A's item 1 is seven decisions and one transcription,
not eight decisions.**

**2 · "SC-1 is one hard capture and two easy ones" — wrong.** The report treated
`dotnet-agent` as capturable. U-01 measured otherwise: the Apartment Triage agent emits
nothing, by four methods with live controls (`#183`). **Two of three dialects need
instrumentation projects; only `claude-code`'s block is access rather than absence.**

**3 · "claude-code is authentication-blocked" — wrong.** U-05 established that what cannot
authenticate is the *nested non-interactive invocation* — Lane A running Claude Code inside
itself — not the capture path or the exporter. `#10`'s blocking finding is **personal data in
a public repository**, not access.

---

## Two things the directive states that this read changes

### D6's trigger is inadequate as written, and U-01 already fired the condition

The directive's own U-01 rationale says: *"If it also emits nothing, C7 contains two
instrumentation projects and D6's trigger date is already past on the day it was written."*

**It emits nothing.** So the antecedent holds.

D6's trigger is written against the **Adjudicator** alone — *"if the Adjudicator is not
emitting OTLP that satisfies the E1 predicate inputs by 2026-09-12"*. But C7 requires **three
emitters ingest-ready**, and on 2026-09-05 the position is:

| Emitter | Ingest-ready by 2026-09-12? |
|---|---|
| Adjudicator | needs an instrumentation project |
| Apartment Triage | needs a **second** instrumentation project |
| Claude Code | not access-blocked; needs env config + redaction |

**So satisfying D6's trigger would not satisfy C7.** An Adjudicator emitting on 2026-09-12
leaves two of three emitters short. This is a gap between D6 and C7, not an error in either,
and it is named here rather than left to be discovered at the trigger date. **Resolving it is
Lane C** — it is a scope question about what C7 means, and the directive's stop conditions forbid
Lane A from reinterpreting a phase-exit item.

### U-10 remains superseded, and D4 changes only half of it

**U-10(a)** — split the controls-table kill-switch row. **The table does not exist.** Searched
again 2026-09-05: no table in `docs/` carries Proven/Configured/Missing states; the only
controls table is [`F1-completion-note.md`](../specs/F1-completion-note.md):52, whose columns
are Control / Class / Catches. The substance is recorded in three places already —
[`ADR-0004`](../adr/ADR-0004-zero-cost-guardrails-kill-switch.md):690,
[`f2-detach-threshold-200-applied.md`](f2-detach-threshold-200-applied.md):46, and
[`eval-plan.md`](../eval-plan.md):193 row 4.7.

The directive adds *"the row is re-joined only after D4 executes"*, which is sound as a rule
and still has no row to apply to.

**U-10(b)** — partition the local table and re-run the probe. **Unsatisfiable**, for three
reasons unchanged since 2026-09-03: the work was attempted twice and failed, measured in CI
(`scripts/e2e/seed.py`:187); `v0.8.1` is the newest `goccy/bigquery-emulator` release, so no
version bump helps; and no container runtime exists on the Lane A host.

**Acceptance criterion 7 cannot be met**, and it is worth stating why in the directive's own
terms: it requires *"the probe's assertion before and after partitioning"*, and there is no
"after" state this repository can reach. The criterion is not failed by omission; it is
unreachable.

---

## What is actually outstanding

| Task | State |
|---|---|
| U-13 deny-list rewrite, prepared | **not started** — genuinely new |
| U-14 D6 contingency ADR | **not started** — genuinely new |
| D1 recorded against `#177` | **not done** — the disposition is decided but the issue does not say so |
| U-10 | superseded, twice reported |
| everything else in Waves 1 and 2 | delivered 2026-09-04 |

## A finding about the directive itself

**Its stated repo target does not exist.** The directive's §0 names
`docs/specs/F3-unblock-directive.md`; searched 2026-09-05, that path is absent, so the
document governing this work is not in the repository and every reference to its section
numbers dangles.

Two consequences, both recorded rather than acted on:

- **D1–D6 are not repo-normative.** They are approved decisions of record living outside the
  record. D1 in particular — the `#177` disposition, `(a) + (c)`, `(b)` rejected — is the
  decision three documents have been waiting on, and `#177` does not say so.
- **Landing it is Lane C's**, not Lane A's. This readout does not create it, and does not
  link to it, because a link to an absent target is the defect class `#151`'s check exists to
  find.

The parts of it that this readout can act on are the two unstarted tasks, U-13 and U-14, and
the recording of D1 against `#177`.

## Provenance

Every item above re-read on 2026-09-05 against `main @ f64a0bc`, through the filesystem and the
GitHub issues API. **No claim in this file is carried from the 2026-09-03 report**; where that
report is cited it is cited as the thing being corrected, which is what U-00 was asked to do.
