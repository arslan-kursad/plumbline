# F3 — Prerequisite Directive

**Version:** 0.2 · **Status:** Proposed · **Date:** 2026-09-02
**Executor:** Claude Code (Lane A), except where a task states otherwise
**Supersedes nothing.** Successor to [`F3-entry-directive.md`](F3-entry-directive.md), which
has one open task (F3E-01c).
**Nothing in this directive is a measurement.** See §9.

> **v0.1 was authored against a session record rather than against the repository.** Checked
> against `main @ 1b800f6`, **four of twelve tasks close before work begins** and three more
> are narrowed or corrected. One of the four is replaced by a task that serves the same
> charter through a method that works. §10 lists every change with the read that caused it.
> This is the [`F3-entry-directive.md`](F3-entry-directive.md) §8 stop condition working, and
> it fired before any work began rather than after — the second time it has done so.

---

## 1. Purpose

[`F3-entry-directive.md`](F3-entry-directive.md) §2 holds: *no F3 spec exists; building
against unfrozen inputs starts F3 covertly.* Freeze A has not concluded — five prerequisites
are open and four of them are decisions, not reads. An F3 build task list therefore cannot be
authored today.

What can be authored is the work F3's gate will stand on, none of which depends on a frozen
input. This directive is that work, and the boundary is mechanical rather than judged.

**Scope test.** A task belongs in this directive if and only if its acceptance criteria can be
written without reading any placeholder in [`eval-plan.md`](../eval-plan.md) Appendix A. If
writing the criteria requires P1–P7, P11, or Q, the task is blocked and belongs in §6, not in
§5.

**Charter rule, carried from the entry directive.** Every task is chartered by an existing
issue, an existing carried obligation, or an existing recorded finding. No task originates
here. A task without a charter would be F3 execution under another name. **T1-05 is new in
v0.2 and its charter is named** — see §10.

## 2. Out of scope

- `docs/specs/F3-*.md` (the F3 spec itself), `eval_results` schema, `tools/calibrate.py`,
  `tools/mde.py`, `docs/eval-plan.constants.yaml`, R5 rule set, `docs/eval/rubric-v1.md`.
  All are Appendix A dependent. See §6.
- Any edit to [`eval-plan.md`](../eval-plan.md). It is a pre-registration document, human-only,
  Class 3. This includes that document's §2 known-wrong "F1 entry gate" line, which is
  protected — correcting it is a pre-registration violation, not a typo fix.
- Any ADR status flip. Status flips are review outputs.
- Selecting a disposition for T2-01. Lane A records the finding; it does not choose.

## 3. Context files

Read before starting. Where this directive and the repo disagree, the repo is right.

- [`F3-entry-directive.md`](F3-entry-directive.md) — §2 (why no spec exists), task table, lane
  column.
- [`architecture.md`](../architecture.md) — that document's §3.3 (default stream, downstream
  dedup), §4.1 (partitioning, `require_partition_filter`, canonical views), §6 (controls) and
  §10 OQ1. **Its §6 and §10 are not this document's** — see the reference convention below.
- [`eval-plan.md`](../eval-plan.md) — read only. Appendix A placeholder list; §8.1 for the
  R-family definitions T2-01 turns on.
- [`f3e-01a-emulator-divergence.md`](../evidence/f3e-01a-emulator-divergence.md) — the surface
  inventory. S1 and S2 are the two Track 1 works against.
- [`f3e-01b-rejection-probe.md`](../evidence/f3e-01b-rejection-probe.md) — what production
  refuses, measured; the local side derived and labelled as derived.
- [`c-1-dossier-filled-2026-09-02.md`](../evidence/c-1-dossier-filled-2026-09-02.md) — B1, B4
  and A5. Track 2 and Track 3 both start here.

**Reference convention, applied to this file itself.** Every `§` that means another document
names it. A bare `§` is this document's own. The collision is real rather than hypothetical:
[`architecture.md`](../architecture.md) has a §6 and a §10, and so does this directive. This is
the [`F2-completion-note.md`](F2-completion-note.md) §5 identifier rule, applied to the document
that records it.

**Open issues:** `#36`, `#74`, `#109`, `#138`.

**Merged pull requests, cited as evidence rather than as work:** `#148`, `#155`, `#156`,
`#163`, `#168`–`#172`.

> **v0.1 listed `#148`, `#155` and `#156` among its open issues.** All three are merged pull
> requests, verified 2026-09-02 through the issues API. This is the defect
> [`F3-entry-directive.md`](F3-entry-directive.md) §11 item 4 recorded and corrected against
> its own v0.1 — *"v0.1 listed `#141`, `#144`, `#145` and `#148` among its issues and chartered
> tasks on them"* — reproduced, with `#148` appearing in both lists. A correction recorded in
> one document does not propagate to the next one written; only re-reading does.

## 4. Standing requirements for every task in §5

These are not per-task boilerplate; they are the conditions under which any of this work
counts as done.

- **R-A · Discrimination.** Every check introduced or repaired here must be shown to fail.
  Record both runs: the green run and the deliberately broken run that turns it red. A check
  never observed red is not evidence, it is decoration. Precedent: the truncation test that
  discriminated by breaking four of six under round-half-up.
- **R-B · Identity, not co-existence.** An assertion about a view must also assert the state of
  what the view reads from. "The deduped view returned one row" is co-existence. "The base
  table holds two rows and the view returns exactly the later one" is identity.
- **R-C · Provenance on every status claim.** Any completion state written into a document
  names where and when it was read (CN4). No status value is written that nothing updates.
- **R-D · New CI checks ship non-blocking.** Turning a check blocking changes what CI asserts —
  Class 3. Ship non-blocking, observe, propose the flip separately.
- **R-E · No SHA pinned.** Every task reads the SHA it runs against at execution time. The one
  SHA in this document's header is stated for corroboration and requires re-derivation.
- **R-F · The Lane A host runs no containers.** Verified 2026-09-02: macOS 12.7.6, `docker`
  binary present, no daemon. Any acceptance criterion requiring the local stack to *run* is
  discharged in CI, not here. `gh workflow run ci.yml --ref <branch>` reaches CI without a pull
  request. **A task whose red run cannot be produced anywhere is not a task**, and v0.1 carried
  one — see T1-01.

---

## 5. Tracks

### Track 1 — Falsifiability floor

The carried obligation is [`F2-completion-note.md`](F2-completion-note.md):165 — *"The
emulator/production divergence is real and only half-measured… Architecture §8 rests the
local-first model on emulator fidelity. Carried to F3."* Its failure mode is a false green.
F3's central deliverable is a gate whose verdict is meant to be trusted. This track is the
precondition for that trust and, per the carry, closes early in F3 rather than at its exit.

> **v0.1 chartered this track on "the one control in the F2 controls table with state
> *Missing*".** No such table exists in `docs/`. Searched 2026-09-02 for rows in
> Proven/Configured/Missing states and for the string `Live-fired`: the only controls table in
> the repository is [`F1-completion-note.md`](F1-completion-note.md):52, whose columns are
> Control / Class / Catches and which carries no state column. The charter above is the one
> the repository actually holds, and it says the same thing.

#### T1-01 · Partition the local table · **CLOSED BEFORE WORK BEGAN — unsatisfiable**

**Charter.** Carried obligation *emulator/production fidelity*.

**Why it closes.** Three independent reads, any one of which is sufficient.

1. **The work was already attempted, twice, and both attempts are recorded as CI
   measurements.** [`seed.py`](../../scripts/e2e/seed.py):187 — *"Columns only. The stand-in
   refuses `CREATE TABLE ... PARTITION BY` outright, and a table created through this API
   carrying `timePartitioning` does not resolve on its Storage Write default stream either —
   measured, both times, in CI."* v0.1 asked for exactly these two things.
2. **No version bump rescues it.** `goccy/bigquery-emulator` `0.8.1` is pinned in
   [`docker-compose.yml`](../../docker-compose.yml) and, read from the releases API
   2026-09-02, `v0.8.1` (published 2026-06-13) is the newest release that exists. The pin is
   already current.
3. **The acceptance criterion cannot be run anywhere.** *"The probe, run against the local
   stack"* needs the emulator running; R-F says where that is possible, and it is not this
   host. Unlike T1-03, the underlying change cannot be made at all, so CI has nothing to run.

**And the finding it claimed to repair is not in the repository.** v0.1 stated that the
divergence *"was correctly observed and incorrectly attributed"*.
[`f3e-01b-rejection-probe.md`](../evidence/f3e-01b-rejection-probe.md) attributes it exactly as
v0.1 says is correct — *"the stand-in refuses `CREATE TABLE … PARTITION BY`. A table with no
`timePartitioning` cannot carry a partition-filter requirement"* — and labels the local side a
derivation rather than a measurement, in the same paragraph.

**The replacement attribution is itself wrong, and the error matters.** v0.1: *"This is not an
emulator semantic difference."* The local table is unpartitioned **because the emulator cannot
create it partitioned**. That is an emulator capability limit — precisely the fidelity gap this
track exists to close, relocated rather than dissolved. Calling it a repo-side omission would
have sent the work at a file that is already correct.

**What is true and survives:** local coverage of `require_partition_filter` is zero and cannot
be made non-zero by any change to this repository. That is a permanent known, not a defect
awaiting a fix, and T1-05 covers the part of the gap that is reachable.

#### T1-02 · Classify the write-path tests against partition behaviour (Lane A · Class 2)

**Charter.** [`f3e-01a-emulator-divergence.md`](../evidence/f3e-01a-emulator-divergence.md) S1:
what did write-path tests running against an unpartitioned table claim about partition
behaviour?

**Work.** Enumerate every write-path test. For each, state whether its assertion is
partition-dependent, partition-independent, or silently partition-independent — the third being
a test written as though it covered partitioning that did not. The surface is
`worker/Plumbline.Worker.Tests/`, `worker/Plumbline.Normalization.Tests/`,
[`seed_test.py`](../../scripts/e2e/seed_test.py), [`cloud_test.py`](../../scripts/e2e/cloud_test.py),
and the assertions in [`run.sh`](../../scripts/e2e/run.sh).

**Acceptance.** Output is a table, not a fix. Every write-path test appears in it with its
classification and the line it was read from. Any test in the third category is named and an
issue opened; a test that asserts a triviality is a defect under the standing invariant that
every assertion must be able to fail. Do not repair the tests in this task — repairing them
before they are classified destroys the record of what was uncovered.

> **The ordering constraint in v0.1 §8 is retired and inverted.** v0.1 required T1-01 first,
> *"because the classification is meaningless until the local table has the property being
> classified against."* The opposite holds: the third category — a test that reads as though it
> covered partitioning and does not — is **only** detectable while the table lacks the
> property. Against a partitioned table those tests would pass for the right reason and become
> invisible. With T1-01 closed the question is moot, and T1-02 runs first in the track.

#### T1-03 · Make the local stack produce duplicates (Lane A · Class 1)

**Charter.** [`f3e-01a-emulator-divergence.md`](../evidence/f3e-01a-emulator-divergence.md) S2;
[`architecture.md`](../architecture.md) §3.3.

**Finding being repaired.** The local path uses a COMMITTED stream, which produces no
duplicates. The assertion that exercises `spans_deduped` therefore passes identically whether
dedup works or does not — a working dedup and an absent duplicate are the same output. This is
the empty-result blindness class, in the component F3's gate will read from. Stated in S2 as
*"the local assertion `rows_seen = distinct_spans` passes both when dedup works and when there
was nothing to dedup."*

**Work.** The local harness deliberately injects a duplicate: identical `(trace_id, span_id)`,
differing `ingest_time`. This is a harness change and does **not** require the stream type to
change — which is what keeps it separable from T1-04.

**Acceptance.** Per R-B, both halves are asserted: the base table holds both rows, and
`spans_deduped` returns exactly one, the later `ingest_time`. Per R-A, the dedup predicate is
then removed and the assertion is observed red. **Per R-F both runs are produced in CI and the
run id is quoted**; neither can be produced on the Lane A host.

#### T1-04 · Stream parity · **CLOSED BEFORE WORK BEGAN — acceptance already satisfied**

**Charter.** [`architecture.md`](../architecture.md) §3.3 fixes the write path as Storage Write
API **default stream**. The local path uses COMMITTED.

**Why it closes.** v0.1 offered two branches and the repository has already taken the second.

- **Branch one — "move the local path to the default stream" — is impossible, and measured.**
  [`BigQueryStorageWriteSink.cs`](../../worker/Plumbline.Worker/Sinks/BigQueryStorageWriteSink.cs):173-181
  — *"The local stand-in cannot resolve it. `goccy/bigquery-emulator` grew implicit `_default`
  handling one day after its most recent release, so every tagged image answers `failed to get
  stream from …/streams/_default` — measured in CI across 0.6.6 and 0.8.1."* The explicit
  COMMITTED stream is the recorded workaround, not an unexamined choice.
- **Branch two — "the divergence is recorded as a dated known with its blast radius named" — is
  the acceptance criterion, and it is met.**
  [`f3e-01a-emulator-divergence.md`](../evidence/f3e-01a-emulator-divergence.md) §S2, dated
  2026-09-02, names the direction (emulator-permissive), the mechanism, and the blast radius.

**Also: T1-04 and T1-01 were mutually exclusive as written.** A partitioned table plus the
default stream is the exact combination [`seed.py`](../../scripts/e2e/seed.py):187 records as
not resolving. Executing both would have produced a local stack that writes nothing.

**Residue, and it is not required by the acceptance.** The divergence lives in an evidence file
rather than in a tracked issue. Filing one is optional and is not chartered here.

#### T1-05 · Static partition-filter check over repository SQL (Lane A · Class 1) — **new in v0.2**

**Charter.** [`f3e-01b-rejection-probe.md`](../evidence/f3e-01b-rejection-probe.md):58 — *"a
query written outside the e2e path — a view, a dashboard, an eval-engine read — meets no local
objection. That is the gap, and it is a gap in coverage rather than in behaviour."* The gap is
recorded; nothing closes it.

**Why this and not T1-01.** T1-01 tried to give the local *engine* the constraint, which the
emulator forbids. This gives the *repository* the constraint, which nothing forbids. It does
not restore emulator fidelity and does not claim to — it covers the reachable half of the same
gap, and the unreachable half stays named in T1-01.

**Work.** A check that reads every `SELECT` against `spans`, `spans_deduped` or `spans_real` in
`analytics/sql/` and `scripts/`, and asserts each carries a predicate over `start_time`.

**Acceptance.** Per R-A, both runs recorded: green against the tree as it stands, and red
against a seeded query with the filter removed. Per R-D it ships non-blocking. It runs on the
Lane A host — no container, no credentials — which is what makes it the reachable half.

**Residual uncertainty, recorded rather than resolved.** A textual check over SQL is weaker
than an engine constraint: it can be defeated by a query built at runtime, and the eval engine
does not exist yet to be scanned. It closes the case where a filter is *forgotten* in a file,
which is the case that has occurred.

### Track 2 — The observability precondition

#### T2-01 · Record the E1 dependency chain (Lane A authors the record · Lane C decides · Class 3)

**Charter.** [`c-1-dossier-filled-2026-09-02.md`](../evidence/c-1-dossier-filled-2026-09-02.md)
B1 and B4: the Adjudicator emits no OTLP, and B4 is *"the largest item in this dossier."*

**The chain, stated once so it is not re-derived.**

F3's DoD is a seeded regression caught by the gate. The gate reads E1. E1 is computed over
R1 ∧ R2 ∧ R3 ∧ R4. **All four are computed from the trace** —
[`eval-plan.md`](../eval-plan.md) §8.1: R1 trace structural validity, R2 telemetry schema
conformance, R3 output contract, R4 behavioral invariants. Trace data for the Adjudicator
requires the Adjudicator to emit OTLP. It does not. Instrumentation is scoped to F4.

The escape route — compute the endpoint from a fixture corpus instead of live telemetry — is
closed by pre-registration: [`eval-plan.md`](../eval-plan.md) SC-1 row 1.2 requires *"≥1 fixture
per dialect **captured from a real emitter**, not hand-authored"*, and there is nothing to
capture from an emitter that does not emit.

> **v0.1 wrote this chain through R3 alone**, and its disposition (b) followed from that:
> *"redefine the F3 gate endpoint to one not requiring R3."* Read against
> [`eval-plan.md`](../eval-plan.md) §8.1, **every conjunct of E1 is trace-computed**, so
> without instrumentation E1 has no computable component rather than three of four. Dropping
> R3 changes nothing, and an issue offering it as a disposition would send the decision at an
> option that does not exist.

**The consequence.** Adjudicator instrumentation sits on F3's critical path irrespective of
which phase document owns it. This is not a new discovery of the capture requirement — the
capture plan already stands at three items. It is a discovery about *sequencing*: the planned
move from SC-1 0/3 to 2/3 does not unblock the gate, because the two capturable emitters are
not the one it reads. F3's hour budget was set against a scope that excluded instrumentation.

**Dispositions. Exactly three, and Lane A picks none of them.**

| | Disposition | Cost |
|---|---|---|
| (a) | Pull Adjudicator instrumentation into F3 | Scope change, recorded. No ADR if no criterion moves. F3's budget is then wrong and must be restated |
| (b) | Replace the deterministic gate endpoint with one computable without a trace | Changes a pre-registered acceptance criterion, and **not by dropping R3** — E1 has no trace-free residue. ADR required |
| (c) | F3 DoD met against a replay corpus captured after instrumentation | (a) with different sequencing; the calendar cost is the same |

**Acceptance for Lane A.** The issue exists, states the chain in the form above — including
that all four conjuncts are trace-computed — names the three dispositions without recommending
one, and is linked from the F3 milestone. The disposition itself is Lane C.

#### T2-02 · Determine the lane for Adjudicator instrumentation (Lane C · Class 3)

**Charter.** `#109`; the standing but unadopted principle that a task's lane is determined by
the strongest permission its execution requires, not by the layer that authors it.

**Work.** The Adjudicator lives outside this repository. A cross-repository write is outside
the scope of `.claude/settings.json`, so the task is not plainly Lane A whatever it looks like.
[`c-1-dossier-filled-2026-09-02.md`](../evidence/c-1-dossier-filled-2026-09-02.md) B4 already
records the answer's shape — *"outside plumbline entirely… no plumbline lane covers it"* —
which makes this a ratification rather than a derivation. Derive the lane from the permission,
and in the same pass either adopt the principle or record a second deferral with a reason.

**Acceptance.** The lane is written. **The third-instance trigger has not fired**: v0.1 expected
T4-03 to supply a third instance of a lane assigned by resemblance, and T4-03 dissolved on
reading. This remains a pattern of two, and the deferral is still available.

### Track 3 — Denominator integrity

#### T3-01 · Establish whether the two 400s carry a body discriminator (Lane A · Class 2) — **narrowed**

**Charter.** [`c-1-dossier-filled-2026-09-02.md`](../evidence/c-1-dossier-filled-2026-09-02.md):140
— *"a malformed image and an unparseable model response produce the same status code, so from
outside the API they are indistinguishable."*

**What v0.1 asked for is already answered.** v0.1 asked whether the two 400s are
distinguishable and for a table of observed 400s. The dossier's third pass, 2026-09-02, records
all three failure shapes with file and line: abstain (well-formed, `pending_human`), rejected
input (`400`, no response body of the contract type), and model failure (`VLMParseError`
subclasses `ValueError`, caught at `api/main.py:176-179`, re-raised as `400`). The status-code
question is closed and the answer is *no discriminator at the status layer*.

**The residue, which is the whole of this task.** Whether the two paths differ in the response
**body** — a distinct `detail` string, an error code, any field an evaluator can branch on
without a human reading the payload. The dossier establishes the codes are equal; it does not
record the bodies.

**Bound on this task.** [`eval-plan.md`](../eval-plan.md) §5.1 must separate a harness error,
which leaves the denominator, from an agent failure, which stays in it. That edit is human-only
and Class 3. Lane A's work is upstream of it: determine what §5.1 can be written to say.
**Note the exact pre-registered text before proposing anything:** that section excludes `error`
from the denominator *"only if `error_rate ≤ 2%`, otherwise the run is void"* — a clause both
v0.1 and the dossier quote without.

**Acceptance.** A table with one row per 400-producing path and its body discriminator, or the
absence of one, each row citing the file and line it was read from in `aiqs-agent` at a named
commit. If no discriminator exists for any row, that is the finding, and it relocates the
required change from eval-plan wording into the harness or the emitter. Say so plainly rather
than proposing wording that the telemetry cannot support. **This is a read of an external
repository at a pinned SHA**, not a run: nothing here executes the Adjudicator.

### Track 4 — Record corrections

#### T4-01 · Remove status affordance from the entry directive (Lane A · Class 1)

**Charter.** The rule that a directive pins no SHA, generalised: status behaves like a SHA. It
is read at execution time, not carried.

**Finding, verified 2026-09-02 through the pull-request API.** F3E-01b is shown open —
[`F3-entry-directive.md`](F3-entry-directive.md):85 lists it under Wave 2 as pending, and its
§6 entry carries no closure marker — while `#156` merged it at `2026-09-02T07:36:38Z`. `#155`,
which closed Wave 1, merged at `2026-09-02T07:15:06Z`. F3E-01b finished **21 minutes after**
the document that would have recorded it was written, so the directive never received the
update. The record shows completed work as pending, and
[`f3e-01b-rejection-probe.md`](../evidence/f3e-01b-rejection-probe.md) exists on `main` to
prove it.

**Work.** Do not write `CLOSED`. A completion marker closes this instance and leaves the
generator: the next task to close makes the document wrong again. Remove the status affordance,
or replace each value with an issue reference in CN4 form — `F3E-01b — #156, read 2026-09-02`.

**Acceptance.** No completion state in the directive is asserted by a value that nothing
updates. The directive carries charter and lane; completion lives in the tracker.

#### T4-02 · Reconcile the task count (Lane A · Class 1) — **narrowed to the repository**

**Charter.** The same generator as T4-01: a count is a status claim, and this one is stated in
three places with three values.

**Two of v0.1's three sources are not in the repository.** Searched 2026-09-02: no "F3 status
report" and no "session summary" file exists under `docs/`. v0.1 asked to *"make both documents
agree with the repo"*; neither document is reachable from Lane A, and per `CLAUDE.md` an
external snapshot that disagrees with `docs/` is stale by definition. **What is reconcilable is
the repository's own count**, and it is the one that will be cited later.

**Work.** One read of [`F3-entry-directive.md`](F3-entry-directive.md). State the count once,
with its derivation — specifically whether 01a/01b/01c count as one task or three. The
directive's own §11 says *"four of this directive's nine tasks"*, written before the 01b split
that its §5.2 then made; the same enumeration after the split is ten. Both numbers are correct
under different rules, which is the defect.

**Acceptance.** The count appears with its provenance and its derivation rule. A count stated
without its derivation rule is the defect, not the number. **If the two external documents are
later supplied, they are reconciled against this, not the reverse.**

#### T4-03 · Verify F3E-01c's lane · **CLOSED BEFORE WORK BEGAN — dissolves on reading**

**Charter.** An apparent discrepancy between a status report assigning F3E-01c to Lane C and a
session summary describing the directive as a Lane A handoff.

**Why it closes.** [`F3-entry-directive.md`](F3-entry-directive.md) states the lane explicitly,
twice, and both times as C:

> :85 — *"**F3E-01c — round-trip probe.** Lane C, requires a written row."*
> :184 — *"**Charter:** same. **Lane:** **C** — requires a written row. **Wave 2.**"*

Its header reads *"**Executor:** Claude Code (Lane A), except where a task states otherwise"*,
and this task states otherwise. §6's entry adds a paragraph headed *"Why it cannot be Lane A"*.
There is no discrepancy in the repository: a document-level default and a task-level exception
are not two conflicting assignments.

**Consequence for T2-02.** This was v0.1's candidate third instance of `#109` — a lane assigned
by resemblance rather than by permission. It is not one. **The pattern remains at two**, and
T2-02's acceptance is corrected accordingly.

#### T4-04 · Split the kill-switch controls row · **CLOSED BEFORE WORK BEGAN — no such row**

**Charter.** `detach_threshold` moved from 5.00 to 200.00; a controls table reading
*Kill-switch / Proven / Live-fired (A2.12)* would then assert Proven over a value never tested.

**Why it closes.** **The row does not exist.** Searched 2026-09-02 across `docs/` for rows in
Proven/Configured/Missing states, for the string `Live-fired`, and for references to `A2.12`.
The only controls table in the repository is [`F1-completion-note.md`](F1-completion-note.md):52
(Control / Class / Catches, no state column). `A2.12` occurs exactly once, as the heading of
[`F2-decision-log.md`](F2-decision-log.md):1026, which is a decision-log entry rather than a
status row — and which already carries its own scope limits in a section headed *"What it does
not establish"*.

**And the substance is recorded, in three places, none of them claiming Proven.**

- [`ADR-0004`](../adr/ADR-0004-zero-cost-guardrails-kill-switch.md):690-692 — *"re-running it
  against 200.00 is required before the ceiling can be claimed as enforced. **Until that run is
  archived, this amendment describes a configuration, not a control**"*.
- [`f2-detach-threshold-200-applied.md`](../evidence/f2-detach-threshold-200-applied.md):46 —
  *"**The ceiling is configured, not proven.**"*
- [`eval-plan.md`](../eval-plan.md):193, row 4.7 — live-fire evidence must name *"the threshold
  it was fired against"* and cover *"the **deployed** threshold"*, added under `#163` on
  2026-09-02.

The identifier/identity rule is already applied here, including inside the pre-registration
document, which is the one place this directive may not edit. **Nothing to split.**

### Track 5 — Entry directive residue

#### T5-01 · F3E-01c round-trip probe (Lane C)

The single open task from [`F3-entry-directive.md`](F3-entry-directive.md). One line. It is not
blocked on Freeze A and should not travel with it.

---

## 6. Blocked register

Listed so that absence is legible. Nothing here is deferred by choice.

| Item | Blocked on | Nature of the block |
|---|---|---|
| `docs/specs/F3-*.md` | Freeze A record | The unrecorded decision is itself the block |
| `eval_results` schema | P1 output contract; [`architecture.md`](../architecture.md) §10 OQ1 | Design, post-freeze |
| `tools/mde.py`, `tools/calibrate.py` | P3 → N_gate and MDE; C-4 category selection | Decision |
| `docs/eval-plan.constants.yaml` | Q sourcing procedure; C-3 T1 hosting and model ids | Decision + external |
| R5 rule set | P4 | Freeze A |
| `docs/eval/rubric-v1.md` | P5 four-point anchors | Freeze A |
| Reference label source | P6 | **Narrowed 2026-09-02:** the dossier answers C1/C2 — MVTec AD annotations, independent, per-item. What is open is which categories the corpus draws from |
| P2 disposition | Fill / defer / minimal | Decision |
| `#36`, `#74`, `#138` | Freeze A or earlier | Milestone |

**The Freeze A block is not that the session has not happened.** The prep brief required
exactly one of (a) second session or (b) an ADR splitting the freeze mechanics to be recorded
at T+150. Neither appears in the 2026-09-02 dates list. An unrecorded open placeholder reads as
option (c), and (c) did not exist — a ready form and a filled form look identical. The block is
that *it is not readable from the record whether Freeze A concluded*, which is the project's
own central defect class applied to its governance rather than to its data.

Four of the five outstanding prerequisites are decisions the human owes. None is a read. No
part of this block is delegable to the implementation layer.

## 7. Test expectations

- Every check in Track 1 ships with a recorded red run (R-A). A green-only record is rejected at
  review regardless of what the check asserts.
- No test introduced here asserts a triviality. Every assertion must be able to fail.
- T1-02 produces a classification, not a repair. Repairing before classifying destroys the
  evidence of what was uncovered.
- T1-03's two runs are produced in CI and quoted by run id (R-F). A local green is not
  available and a claim of one would be false.
- T3-01 produces an observation table, not proposed eval-plan wording.
- Tracks 2 and 4 produce records and reads. Neither produces a decision.
- New CI checks ship non-blocking (R-D). The flip to blocking is proposed separately and is
  Class 3.

## 8. Ordering

**Track 4 and T5-01 first.** T4-01 and T4-02 are reads and record repairs with no dependency on
anything else here. T4-03 and T4-04 are already closed above.

**Track 1 runs T1-02 before T1-05.** The classification is what tells T1-05 whether any existing
test already covers what it would check; building the check first risks a second assertion of
something already asserted. T1-03 is independent of both.

> v0.1 ordered T1-01 before T1-02. Both halves of that constraint are gone: T1-01 is closed, and
> the reasoning inverted — see T1-02.

**T2-01 before any Track 1 work is scheduled against calendar time**, because its disposition
may change what F3 contains and therefore what the schedule is measuring.

## 9. Provenance

**v0.1** was derived from the session record of 2026-09-02 and was not checked against the
repository before being issued.

**v0.2 is that directive checked against the repository** at `main @ 1b800f6`, on 2026-09-02.
Every closure in §5 names the file and line that closed it. The reads behind the four closures
were made against the working tree at that commit and against the GitHub issues and releases
APIs on the same date.

**No line in this directive is admissible as evidence in a closing note or a DoD table.**
Re-read from the repository. The one SHA in the header is stated for corroboration and requires
re-derivation (R-E).

## 10. Changelog

**v0.2 — 2026-09-02** (supersedes v0.1). Nine changes, each with the read that caused it.

1. **T1-01 closed as unsatisfiable.** [`seed.py`](../../scripts/e2e/seed.py):187 records both
   halves of the requested work as already attempted and failed, measured in CI; `v0.8.1` is the
   newest emulator release (releases API, 2026-09-02), so the pin is current and no bump helps;
   and the acceptance needs a local stack this host cannot run (R-F). The misattribution it
   claimed to repair is absent from
   [`f3e-01b-rejection-probe.md`](../evidence/f3e-01b-rejection-probe.md), and its replacement
   attribution is wrong in the direction that would have sent work at a correct file.
2. **T1-05 added**, chartered on
   [`f3e-01b-rejection-probe.md`](../evidence/f3e-01b-rejection-probe.md):58. This is the only
   task new in v0.2. It covers the reachable half of T1-01's gap by constraining the repository
   rather than the emulator, and its residual weakness is recorded in the task rather than
   argued away.
3. **T1-04 closed; its acceptance is already met.** Branch one is impossible per
   [`BigQueryStorageWriteSink.cs`](../../worker/Plumbline.Worker/Sinks/BigQueryStorageWriteSink.cs):173-181
   (measured in CI across two image versions); branch two is satisfied by
   [`f3e-01a-emulator-divergence.md`](../evidence/f3e-01a-emulator-divergence.md) §S2, dated,
   with its blast radius named. Recorded additionally: T1-01 and T1-04 were mutually exclusive,
   and executing both would have produced a local stack that writes nothing.
4. **T4-03 closed; it dissolves on reading.**
   [`F3-entry-directive.md`](F3-entry-directive.md):85 and :184 both assign Lane C explicitly. A
   document-level default plus a task-level exception is not a conflict. T2-02's acceptance is
   corrected: the `#109` pattern remains at two instances, not three.
5. **T4-04 closed; the row it splits does not exist.** No controls table in `docs/` carries
   Proven/Configured/Missing states; `A2.12` occurs once, as a decision-log heading. The
   substance is already recorded in
   [`ADR-0004`](../adr/ADR-0004-zero-cost-guardrails-kill-switch.md):690, in
   [`f2-detach-threshold-200-applied.md`](../evidence/f2-detach-threshold-200-applied.md):46,
   and in [`eval-plan.md`](../eval-plan.md):193 row 4.7 under `#163`.
6. **T2-01's chain corrected from R3 to all of R1–R4.** [`eval-plan.md`](../eval-plan.md) §8.1
   defines every conjunct of E1 over the trace, so without instrumentation E1 has no computable
   component. v0.1's disposition (b) — drop R3 — was not a real option and is replaced.
7. **T3-01 narrowed to the response body.** Its status-code question was answered by
   [`c-1-dossier-filled-2026-09-02.md`](../evidence/c-1-dossier-filled-2026-09-02.md) on
   2026-09-02, third pass. The remaining question is whether the bodies discriminate. The task
   also now quotes [`eval-plan.md`](../eval-plan.md) §5.1's `error_rate ≤ 2%` clause, which both
   v0.1 and the dossier omit when quoting it.
8. **T4-02 narrowed to the repository.** Its other two sources — an "F3 status report" and a
   "session summary" — are not files in `docs/`. The count is reconciled against
   [`F3-entry-directive.md`](F3-entry-directive.md), whose own §11 says nine while the
   post-split enumeration is ten.
9. **§3 separates issues from pull requests, and Track 1's charter is replaced.** `#148`, `#155`
   and `#156` were listed as open issues and are merged pull requests (issues API, 2026-09-02) —
   the defect [`F3-entry-directive.md`](F3-entry-directive.md) §11 item 4 already recorded
   against its own v0.1, with `#148` appearing in both lists. Track 1's charter moves from a
   non-existent controls table to
   [`F2-completion-note.md`](F2-completion-note.md):165, the carried obligation that says the
   same thing. **R-F is added** to §4, because v0.1 carried a task whose red run could not be
   produced anywhere and nothing in the standing requirements would have caught it.
