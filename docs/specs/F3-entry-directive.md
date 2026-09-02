# F3 Entry Directive

**Version:** 0.3 · **Status:** Proposed · **Date:** 2026-09-02
**Executor:** Claude Code (Lane A), except where a task states otherwise
**Nothing in this directive is a measurement.** See §10.

> **v0.1 was derived against `main @ 6a739c6`, which is this morning's base.** Eleven pull
> requests merged after it. Checked against the repository, **four of nine tasks were
> already satisfied** and one acceptance criterion had become unsatisfiable. §11 lists
> every change with the read that caused it. This is the §8 stop condition working, and it
> fired before any work began rather than after.

---

## 1. Purpose

F3 has no spec. Its inputs are not frozen. This directive covers the work that is
**prerequisite to F3 and independent of Freeze A** — the entry-condition backlog, the
capture gap under SC-1, and the tooling whose absence is now demonstrated rather than
suspected.

Every task below is chartered by an existing issue, an existing carried obligation, or an
existing acceptance criterion. No task originates here. A task without a charter would be
F3 execution under another name.

---

## 2. Out of scope

Each exclusion has a reason. None is deferred silently.

| Excluded | Reason |
|---|---|
| Any F3 component — gate plumbing, dataset freeze mechanism, `eval_results` schema | No F3 spec exists. Building against unfrozen inputs starts F3 covertly. `CLAUDE.md`: no scope beyond the active spec |
| Any edit to `docs/eval-plan.md` | Class 3, human-only. Includes the SC-1 row 1.1 path defect and the stale `architecture.md` pin in §4 — both are Freeze A exit conditions, `freeze-a-prep.md` §7 items 5 and 6 |
| Any edit to `.claude/settings.json`, including the Lane A deny-list shape | DoD 12 asserts nothing was loosened across F2, and F2 is not closed. The structural workaround (read-only CI readout) stands |
| ADR-0008 status flip | Standing directive in [`F2-completion-directive.md`](F2-completion-directive.md) — do not flip it. The review is scheduled 2026-09-03 as its own session |
| Making the cross-reference check blocking in CI | Ships non-blocking first (F3E-04). Flipping a check to blocking changes what CI asserts — Class 3 |
| Any capture run | Lane C. Lane A builds the harness and the diagnostics; the human runs them |
| DoD 1 remediation beyond what is already filed | F2 closure work, not F3 entry. Measured in [`f2-dod1-five-facts.md`](../evidence/f2-dod1-five-facts.md); facts 4 and 5 wait on one billing-API read Lane A is denied |

---

## 3. Context files — read before starting

- `CLAUDE.md` — boundaries, cost invariants, process rules.
- [`eval-plan.md`](../eval-plan.md) SC-1 and Appendix A — read-only; the corpus obligations originate here.
- [`F2-completion-directive.md`](F2-completion-directive.md) — lane model, autonomy classes, carried obligations.
- [`F2-minimal-gcp-footprint.md`](F2-minimal-gcp-footprint.md) §7.2 — CN1–CN5, the closing-note requirements.
- [`freeze-a-prep.md`](freeze-a-prep.md) §7 and §7.1 — the Freeze A exit conditions and the pre-freeze audit.
- [`f3e-01a-emulator-divergence.md`](../evidence/f3e-01a-emulator-divergence.md) — the surface
  inventory F3E-01b and F3E-01c are both scoped from.
- [`architecture.md`](../architecture.md) §5 (normalization), §7 (cost guardrails), §2.1 (collector contract).
- `scripts/ci/invariant-gates.sh` — the existing gate surface; the shape F3E-04 must not break.

**Open issues:** `#7`, `#10`, `#42`, `#138`.
**Closed issue:** `#126`.
**Merged pull requests, cited as evidence rather than as work:** `#137`, `#139`, `#141`,
`#144`, `#145`, `#147`, `#148`. v0.1 listed four of these among its issues and chartered
tasks on them; see §11.

---

## 4. Lane and autonomy

Lane A is autonomous, self-merge after green CI, decision-log-replaces-confirm. Class 1
decisions record the decision, the alternative not taken, **and the residual uncertainty**.
Class 3 conditions are a stop, not a request to continue.

**Lane assignment rule, applied here and not assumed:** a task's lane is determined by the
strongest permission its execution requires, not by the layer that authors it. F3E-01a's
first deliverable is the lane determination for F3E-01b, because that is exactly where
`#109` went wrong — the lane was assigned by what the task looked like.

---

## 5. Waves

**Wave 1 — complete 2026-09-02.** F3E-01a (`#152`), F3E-02 (`#153`), F3E-03 (`#154`),
F3E-04 (`#151`). All four merged; §6 carries each with its evidence.

**Wave 2 — gated on Wave 1, and split at the lane boundary F3E-01a found:**

- **F3E-01b — rejection probe.** Lane A, read-only, dry-run.
- **F3E-01c — round-trip probe.** Lane C, requires a written row.

**Closed before work began:** F3E-05, F3E-06, F3E-07a, F3E-07b. Retained in §6 with their
evidence rather than deleted — what was chartered is part of the record.

### 5.2 Why F3E-01b became two tasks

F3E-01a's inventory ([`f3e-01a-emulator-divergence.md`](../evidence/f3e-01a-emulator-divergence.md))
returned two findings that change the task rather than inform it.

**The instrument was wrong.** The charter said *"run the fixture corpus through both paths
and diff the results"*. Rows are identical by construction — timestamp truncation happens
in the worker before either path is chosen (S6) and the column set is generated from one
DDL under a CI diff (S7). What differs is **what each side refuses**: the local table is
unpartitioned so `require_partition_filter` is not enforced (S1), and the local sink uses a
`COMMITTED` stream where production uses `_default`, so the at-least-once duplicates the
dedup views exist to remove are not produced locally (S2). A row diff sees none of that and
comes back clean, which reads as reassurance.

**The lane boundary runs through the middle.** Asking *"does production reject this?"* is
`bq query --dry_run`, which creates nothing — Lane A, on the precedent W2.17 set. Asking
*"does production round-trip this JSON identically?"* needs a row written and read back, and
no dry run produces one — Lane C. A single task spanning both would begin in Lane A, reach
the round-trip probe, and stop. That is `#109` repeating, and §8 says stop at the discovery
rather than reclassify afterwards. **Splitting now is that stop, taken before the work
starts instead of during it.**

### 5.1 The 04/07b sequencing constraint is retired

v0.1 required F3E-04 to demonstrate against a base recorded *before* F3E-07b merged, on the
reasoning that 07b repairs the defect 04 must catch. **07b merged on 2026-09-01 as `#148`.**
The constraint's purpose is not lost; it moved into history.

F3E-04's demonstration base is therefore **read from git rather than recorded at execution
time**, and the acceptance criterion names the method, not a number:

> The base is **the merge commit of `#147`** — the commit that introduced the two `§9.1`
> references into `freeze-a-prep.md`, before `#148` removed them.

Measured 2026-09-01 that commit is `1d59385`, where `freeze-a-prep.md` contains two `§9.1`
occurrences against zero at `e754016`. **That value is stated for corroboration and must be
re-derived, not inherited** (CN5, and §10 below).

---

## 6. Tasks

### F3E-01a — Emulator/production divergence surface inventory · **CLOSED 2026-09-02**

Delivered as [`f3e-01a-emulator-divergence.md`](../evidence/f3e-01a-emulator-divergence.md)
(`#152`). Seven surfaces, two `unknown`. Two diverge by construction and both in the
direction that matters. The lane determination it was asked for is what split F3E-01b —
see §5.2.
**Charter:** F3 entry carry — [`F2-completion-note.md`](F2-completion-note.md) §5, *"the
emulator/production divergence is real and only half-measured… Carried to F3."*
**Lane:** A. **Wave 1.**

Read-only comparison of emulator behaviour against the worker's write path. Enumerate what
*can* diverge, not what does. Candidate surfaces: `require_partition_filter` enforcement,
Storage Write API default-stream semantics, nanosecond-to-microsecond TIMESTAMP conversion
(truncation is pinned), JSON column round-trip, type coercion on `gen_ai_*` columns.

**Deliverables:** (1) the surface inventory, each entry naming the source read; (2) a
recommendation on whether F3E-01b is worth building; (3) **the lane determination for
F3E-01b**, stating the strongest permission its execution requires and why.

**Acceptance:** every inventory entry cites a file and line or a documentation URL. An
entry reading "unknown" is admissible and preferred over an assumed one.

---

### F3E-01b — Rejection probe
**Charter:** F3 entry carry, via F3E-01a. **Lane:** **A** — read-only, dry-run only.
**Wave 2.** **Covers surfaces S1 and S3.**

Take statements and queries production rejects, and assert the local stack rejects them
too. Enumerate where it does not.

**Scope is fixed here and may not widen during execution.** `bq query --dry_run` against
`plumbline-19458`, and read-only queries. Nothing that writes a row, nothing that creates a
table. The moment a probe needs either, it belongs to F3E-01c and this task stops — §8.

S1 supplies a first case already known to fail: a query with no partition predicate is
accepted locally and rejected by the cloud table.

**Direction is mandatory in every report.** Emulator-permissive — CI green where production
would reject — is the only failure that matters. The one direction measured so far is the
opposite (false-red: CI fails on SQL production accepts, W2.16/W2.17). Production-permissive
findings are harmless and must be labelled as such, never aggregated into a single
divergence count.

**Acceptance:** either at least one divergence is found and characterised by direction, or
the report states *how many surfaces were probed, which ones, and which were not reachable*.
A report of "no divergence" without that enumeration is not admissible: an empty result must
state why it is empty — the rule the completion note's §5 already carries.

---

### F3E-01c — Round-trip probe
**Charter:** same. **Lane:** **C** — requires a written row. **Wave 2.**
**Covers surfaces S4 and S5.**

Whether a JSON column survives production byte-identically, and whether column-name
matching differs between the two sides. Both are recorded as **unknown** in the inventory
and neither can be settled by reading.

**Why it cannot be Lane A.** Establishing a round-trip needs a row written and read back.
No dry run produces one, and `bq insert` is on the Lane A deny-list. This is stated before
the work begins rather than discovered inside it.

**S4 is the one to run first.** It sits directly under SC-1 row 1.3's losslessness claim:
if the emulator normalises JSON and production does not, a local round-trip test passes
over a transformation the cloud never performs.

**Cost, so it is chosen and not stumbled into.** One row written to a real table, and the
row is `synthetic = true` and walled off (architecture §4.1). Under the 200 TRY ceiling
(ADR-0004 Amendment 5) the write is immaterial; under the old hard zero it would have
needed its own argument.

**Acceptance:** for each of S4 and S5, either a divergence characterised by direction, or a
statement of what was written, what came back, and why the two are the same. "No
divergence" without the artefacts is not admissible.

---

### F3E-02 — Capture harness for the two unblocked emitters · **CLOSED 2026-09-02**

Delivered in `#153`: `scripts/capture/capture.sh`, `redact.py`, `manifest_validate.py`,
and [`agent-capture.md`](../runbooks/agent-capture.md). The validator discriminates in
both directions and the redaction gate refuses by default, both asserted in CI. **The
captures themselves are Lane C and are not done.**
**Charter:** `eval-plan.md` SC-1 row 1.2; `#42`; `#138`. **Lane:** A builds; C runs. **Wave 1.**

**The gap is now measured from the artefacts, not argued from the plan.** Read 2026-09-01,
no fixture manifest declares itself `captured`: `dotnet-agent`, `langgraph-python` and
`unknown` read `provenance: constructed`; `claude-code` reads
`derived-from-measured-evidence` and explains why. SC-1 row 1.2 requires *"≥1 fixture per
dialect captured from a real emitter, not hand-authored"*.

**Two of the three emitters carry no *access* blocker** — the LangGraph adjudicator and the
.NET agent are first-party, with no beta gate and no nested-authentication constraint.

> **Corrected 2026-09-02.** This originally read that two thirds of the SC-1 gap was
> *reachable* on that basis. It is not. Read at
> [`c1-adjudicator-readout.md`](../evidence/c1-adjudicator-readout.md), the Adjudicator has
> **no OTLP instrumentation at all** — no `opentelemetry-*` dependency, no imports, nothing
> emitting. There is no access problem because there is nothing to access. Instrumenting
> the agents is **F4** by the Project Brief's own phase list. The harness below is correct
> and still needed; it runs later than this task implied.

**Deliverables:** (1) a one-command capture path per emitter; (2) mechanical redaction —
not a documented manual step; (3) a manifest validator covering every field SC-1 row 1.2
requires, including `redacted_fields`; (4) a runbook naming the Lane C steps.

**Note for deliverable 3:** `redacted_fields` is already present in all four manifests, and
the manifests carry fields row 1.2 does not name — `provenance`, `construction_basis`,
`evidence`, `synthetic_values`, `redaction_rules`, `validation_status`. The validator
covers what row 1.2 requires; whether row 1.2 should grow to match the manifests is a
Freeze A decision and is not settled here.

**Acceptance — the validator must be shown to discriminate.** It rejects one of the existing
hand-authored fixtures and accepts a captured one. A validator that passes everything
presented to it has not been tested; it has been run.

---

### F3E-03 — Claude Code capture failure diagnostic package · **CLOSED 2026-09-02**

Delivered in `#154`: `claude-code-preflight.sh` (eight blocking checks, authentication
last) and `capture_report.py` (four terminal states, none of them "retry"). **The
capture attempt itself is Lane C and has not been made.**
**Charter:** `#10`; OQ-4, [`architecture.md`](../architecture.md) §10. **Lane:** A builds; C runs. **Wave 1.**

The capture is not unscheduled. It was attempted and every run failed at authentication
before reaching a tool call. That is a fact, not a diagnosis. Claude Code cannot run Claude
Code, so Lane A builds the instrumentation that converts the next human attempt into an
answer.

**Partly satisfied already, and the scope is the remainder.** Read 2026-09-01:
[`claude-code-capture.md`](../runbooks/claude-code-capture.md) exists (158 lines, §3
Prerequisites through §7 *"if the capture still cannot reach tool spans"*), and
`scripts/capture/otlp-file-receiver.py` exists and works. **What does not exist is anything
executable between them.** §3's prerequisites are prose a human checks by reading.

So this task is not "write the runbook". It is the same distinction F3E-02 draws for
redaction: **turn the documented manual steps into a check that runs.**

**Deliverables:** an executable pre-flight (environment, auth path, exporter configuration,
endpoint reachability) and a capture wrapper that records which spans were reached before
failure, with the failure surfaced rather than swallowed.

**Acceptance:** the runbook, followed once by a human, yields either a captured fixture or a
**named root cause**. "Retry" is not an acceptable terminal state. The scarcest resource on
the path to 2026-10-04 is that human attempt; spending one to learn nothing is the failure
this task exists to prevent.

---

### F3E-04 — Mechanical cross-reference check · **CLOSED 2026-09-02**

Delivered in `#151`. All five acceptance criteria run; criterion 1 verified against the
merge commit of `#147`. Ships non-blocking, reporting 13 findings against `docs/` of
which two look real — a ratio recorded rather than tuned away.
**Charter:** `#7`, pulled forward from F5. **Lane:** A. **Wave 1.**

Scope: internal section references and relative links across `docs/`.

**Why it moves forward.** A session auditing specifically for this defect class produced it
twice while auditing — once caught before filing (the CN5 draft, recorded in
`F2-minimal-gcp-footprint.md` §12, Amendment 3), once caught only after merge (`#148`). Manual review is now demonstrated not
to close this. That demonstration is the charter, and it is two data points, not a
suspicion.

**Acceptance, in this order:**
1. Run against the base defined in §5.1 — the merge commit of `#147`, re-derived from git
   at execution time. It must find the two `§9.1` references in `freeze-a-prep.md`.
2. It must find a deliberately seeded broken reference in a test fixture.
3. It must **not** flag a document-qualified reference, **and qualification is a property
   of the sentence, not of the line.** `freeze-a-prep.md` carries at least five qualified
   references: `§12` twice meaning `eval-plan.md`'s change control, and `§3.3`, `§4.2`,
   `§10` in a sentence whose subject is `architecture.md`. This file carries two more where
   the qualifier sits on the *following* line, inside the same sentence. A line-scoped
   check reports all of them and has traded one manual pass for another.

   *Measured, not assumed:* a line-scoped prototype run over this directive while it was
   being written flagged seven references, **all seven false positives**. Two of them were
   worth acting on anyway — the reference was correct but loosely qualified, and both were
   tightened. That is the ratio the check has to beat to be worth switching on.
4. Finding zero on a corpus known to contain defects means the check is wrong. Fix the
   check; do not adjust the corpus.
5. Ships as a **non-blocking** CI job emitting its findings as an artifact. Flipping it to
   blocking is a separate decision and is Class 3.

---

### F3E-05 — CN5 and the identifier/identity rule · **CLOSED 2026-09-01**

Both rules are recorded. CN5 is `F2-minimal-gcp-footprint.md` §7.2, filed as **Amendment 3**
(`f749625`). The generalisation at three instances is `F2-completion-note.md` §5
(`f1b8111`), carried to F3 as a design rule.

v0.1's warning was accurate and had already fired: the CN5 draft wrote a bare `§5` while
§5 of that spec is *Out of scope (hard)*. Caught before filing, corrected to name its
document, and recorded in Amendment 3's changelog rather than fixed silently.

---

### F3E-06 — `api-keys.md` §4, two changes · **CLOSED 2026-09-01**

Merged as `#137` (`5f2e180`); `#126` closed with it. Verified on `main`: `revoke-refresh`
occurs zero times, `updateMask.fieldPaths=status` three times. Both changes landed together,
which is what the task required — removing the first without adding the second would have
left the runbook with no executable revocation procedure.

Also found while doing it: `keyctl` has no revoke flag, so the prose instruction had no
command behind it anywhere in the repository.

---

### F3E-07a — Hygiene, Wave 1 · **CLOSED 2026-09-01**

| Item | Evidence |
|---|---|
| Session timing corrected to `4a1d370`'s own message | `#141` (`29a7ec2`); both sites now read 10:00–13:00 |
| Run reference re-derived against the current base | `#144` (`4ec073c`); run `33503481240` @ `216fee2`, with the SHA beside the id per CN5 |
| F3 milestone created | Milestone `#4`. F4 (`#5`) and F5 (`#6`) followed, so `#42` and `#7` have homes |

---

### F3E-07b — Hygiene, Wave 2 · **CLOSED 2026-09-01**

`freeze-a-prep.md`'s two `§9.1` references repaired in `#148` (`e754016`). Zero occurrences
remain.

**Merged before F3E-04 existed to demonstrate against it.** That is the sequencing
constraint v0.1 wrote to prevent, and it was already lost when v0.1 was drafted. §5.1
records how F3E-04's acceptance survives it.

---

## 7. Test expectations

- Every check added here must be shown to fail on a known-bad input before it is trusted on
  a clean one. No assertion that cannot fail.
- No test asserts a triviality to make a job look real.
- Any read that can legitimately return empty states why it is empty.
- Evidence cites where and when it was derived, and — for run references — against which
  base (CN5).

---

## 8. Stop conditions specific to this directive

Beyond the standing Class 3 list:

- Any task requiring an `eval-plan.md` edit. Stop and report; it is a Freeze A item.
- F3E-01b turning out to require permissions beyond Lane A after work has begun. That is the
  `#109` failure repeating; stop at the discovery, do not proceed and reclassify afterwards.
- Any finding that a task's charter has already been satisfied in the repo. Stop and report
  rather than re-doing it. **This condition has already fired once, against v0.1, and closed
  four of nine tasks** — see §11.

---

## 9. Reporting

One decision log for the directive, appended per task: decision, alternative not taken,
residual uncertainty. Wave 1 reports before Wave 2 begins. Findings that change method but
not acceptance criteria are Class 2 — record and open an issue, do not interrupt.

---

## 10. Provenance

**v0.1** was derived on 2026-09-01 from the C-6 read-only readout at `main @ 6a739c6` and
from the Freeze A audit session of the same day.

**v0.2 is that directive checked against the repository** at `main @ e754016`. `6a739c6` is
this morning's base: eleven pull requests merged after it, and four of this directive's nine
tasks were among their outputs. Every task now records the SHA it executed against rather
than citing one from here.

**No line in this directive is admissible as evidence in a closing note or a DoD table.**
Re-read from the repository. The one SHA quoted in §5.1 is stated for corroboration and is
explicitly marked as requiring re-derivation.

---

## 11. Changelog

**v0.3 — 2026-09-02** (supersedes v0.2). Wave 1 closed; Wave 2 split.

6. **Wave 1 is complete** — F3E-01a, F3E-02, F3E-03 and F3E-04 merged as `#152`, `#153`,
   `#154` and `#151`. Each entry in §6 is marked closed with its evidence and kept rather
   than deleted. **What is closed is the Lane A half:** the two agent captures, the Claude
   Code attempt, and the rejection and round-trip probes are all still to run.
7. **F3E-01b is split into F3E-01b (Lane A) and F3E-01c (Lane C)**, on two findings from
   F3E-01a. The instrument was wrong — rows are identical by construction and the
   divergence is in what each side *refuses*, so a row diff comes back clean and reads as
   reassurance. And the lane boundary runs through the middle of the task: dry-run probing
   creates nothing, a round-trip needs a written row. Reasoning in §5.2; a single task
   spanning both would be `#109` repeating.
8. **§3 gains the inventory** as a context file, since both Wave 2 tasks are scoped from it.

**v0.2 — 2026-09-01** (supersedes v0.1). Five changes, each with the read that caused it.

1. **F3E-05, F3E-06, F3E-07a and F3E-07b closed before work began.** All four were
   delivered on 2026-09-01, after v0.1's `6a739c6` base. Verified individually on `main`:
   CN5 present in `F2-minimal-gcp-footprint.md` §7.2, the identifier rule present in
   `F2-completion-note.md` §5, `revoke-refresh` absent from `api-keys.md` and the `PATCH`
   command present, both session-timing sites reading 10:00–13:00, the run row carrying its
   SHA, the F3 milestone existing, and zero `§9.1` occurrences in `freeze-a-prep.md`.
   Retained in §6 with evidence rather than deleted.
2. **F3E-04's acceptance criterion 1 was unsatisfiable and is repaired** (§5.1). It required
   the check to find a defect that `#148` had already removed from `main`. The base is now
   defined by method — the merge commit of `#147` — rather than by a recorded value.
3. **F3E-04 gains acceptance criterion 3.** A check that flags document-qualified references
   trades one manual pass for another. `freeze-a-prep.md` carries at least five such
   references, enumerated, which makes this testable rather than aspirational.
4. **§3 separates issues from pull requests.** v0.1 listed `#141`, `#144`, `#145` and `#148`
   among its issues and chartered tasks on them. They are merged pull requests — the outputs
   of the session the directive was derived from. That misclassification is why four tasks
   were chartered as open work.
5. **F3E-03 is scoped to the remainder rather than the whole.**
   `docs/runbooks/claude-code-capture.md` and `scripts/capture/otlp-file-receiver.py` both
   already exist. What is missing is anything executable between them, which is the same
   documented-manual-step distinction F3E-02 draws for redaction.
