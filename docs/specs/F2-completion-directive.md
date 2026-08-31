# F2 — Completion Directive

**Version:** 1.3 (Amendment 3) · **Status:** Approved · **Date:** 2026-08-30
**Canonical copy:** `docs/specs/F2-completion-directive.md` in the repo. The chat-side copy
is a snapshot and loses its tie to the repo the moment it is not re-committed (Project
Brief, working model). Every amendment is committed before it is executed against, and the
decision log records the commit SHA — otherwise "which version" is unanswerable, which is
how Amendment 2 came to be read as missing.
**Lane C sign-off:** 2026-08-30 — Decisions 1–4 of §9 approved
**Baseline:** `main` @ `aac1097` · open PR #82 · measured F2 status snapshot 2026-08-30
**Executor:** Claude Code (Lane A), with explicit hand-backs to Lane B (armed apply) and Lane C (human-only)
**Repo target:** `docs/specs/F2-completion-directive.md`

This directive is the single approval artefact for taking F2 from its current blocked
state to phase exit. It does not restate the DoD; it sequences the remaining work and
adds the checks the current plan does not yet contain.

**Authority order on conflict:** `docs/specs/F2-minimal-gcp-footprint.md` §7 (DoD) →
`F2-decision-log.md` (decisions) → `docs/architecture.md` §10 (ADR status) → this
document. If any of those contradict a line here, they win and this line is stale.

### Amendment 3 (2026-08-30, post-merge review)

Resolves five contradictions raised by the executor plus two defects that follow from them.

- **Items 1 and 2** (F2C-04 cites Amendment 2 while the header reads 1.1; §7 criterion 2
  still demands the withdrawn guard clause) **were already fixed in v1.2.** The copy read
  was stale. This is the third instance in F2 of the same failure class — local `main` vs
  `origin/main`, plan output vs API, and now a chat snapshot vs the repo. Fixed
  structurally by the **Canonical copy** line in the header, not by another correction.
- **Item 3 — valid.** F2C-04b was mislabelled `cloud-independent`; its first half reads the
  live Cloud Run API. Relabelled below. Read-only, no apply, does not block on Wave 4 — but
  not cloud-independent.
- **Item 4 — valid.** Task IDs were renumbered between v1.0 and v1.1. Crosswalk and an ID
  stability rule added below.
- **Item 5 — valid.** W2.16 added to F2C-20's closure list.
- **#61 — executor is right, this directive was wrong.** F2C-21 said "#61 closed by #82".
  #82's own plan shows `spans_deduped will be updated in-place`; the cloud views are still
  the two-column form. A merged fix is not a deployed one (spec §10). Corrected below. The
  defect class is the same as F2C-01's: a snapshot claim carried into normative text without
  being re-derived.
- **`analytics-api` — this directive over-specified.** F2C-04b named three Cloud Run
  services; F2 deployed two. `Cannot find service` is the correct and useful result, and
  recording it rather than skipping the line is right: an unread line and a non-existent
  service are different facts. Corrected below.

**ID stability rule, effective now.** A task ID, once issued, is immutable. New tasks take
new numbers; withdrawn tasks are marked withdrawn and their numbers are never reused. The
v1.0 → v1.1 renumbering is frozen by this crosswalk; all references resolve against v1.1+
numbering:

| v1.0 | v1.1 onward | Subject |
|---|---|---|
| F2C-19 | F2C-20 | DoD 11, close the decision log |
| F2C-20 | F2C-21 | Closure note CN1–CN4 |
| F2C-21 | F2C-22 | Remove standing human apply roles |
| — | F2C-19 | C7, the window's engineering prerequisite (new in v1.1) |

### Amendment 2 (2026-08-30, post-#82 review)

Written against the executor's #82 completion report. Three of the four items below are
corrections to this directive, not to the work.

- **F2C-04** — acceptance criterion was self-contradictory and is withdrawn. DoD 6 evidence
  relocated to new **F2C-04b** (API read + guard mutation probe).
- **F2C-01** — the test already existed at this directive's own baseline
  (`TimestampNarrowingTests.cs`). Recorded as a spec defect: the task was authored from the
  status snapshot rather than from the repo. The task nonetheless earned its place, because
  what was executed was the mutation check (round-half-up substitution breaks 4 of 6 cases),
  which converts *a test exists* into *the test discriminates*. The cases that survive
  substitution are the ones where truncation and rounding agree; that is expected, not a gap.
- **F2C-23** — added: fix the SQL scanner that reads comments as code (decision log W2.16).
  The keyword ban proposed as an alternative is rejected; rationale in the task.
- **Evidence labelling** — emulator results are labelled as emulator in every archive.
  `dataset now holds: ['spans', 'spans_deduped', 'spans_real']` with 13 rows per view is an
  emulator result. Cloud `plumbline.spans` remains at 0 rows and DoD 3 remains open.

Two standing principles surfaced by this session belong in `CLAUDE.md`, not here, and are
F3-entry work:

- **Verify from the authoritative source, not a cache.** "Read from the API, not from plan
  output" and "read `origin/main`, not local `main`" are the same rule. Both failure modes
  have now occurred in this phase.
- **A control is proven only by a deliberate failure.** Already applied unnamed in four
  places (F2C-01 mutation, F2C-08 pre-drill alert check, F2C-04b guard probe, F2C-22
  dry-run). Naming it makes it reusable in F3 and F4.

### Amendment 1 (2026-08-30)

Records Lane C approval of the four decisions in §9 and the constraints that approval
alone does not resolve:

- **F2C-03** — merge approval is pre-granted against a machine-checkable precondition,
  with a named abort condition. Added so that a pre-granted approval remains a gate
  rather than becoming Lane A discretion.
- **F2C-09** — decided: the F2 constructed payload carries `synthetic=true`.
- **F2C-18** — approved as a ceiling, not as a date. C1 still needs a pinned date; **C7**
  added, because C4 has a prerequisite no calendar item owned.
- **F2C-21** — approved with sequencing constraints: after F2 exit, and only after the
  break-glass runbook exists and has been dry-run.

---

## 1. Purpose

Close DoD items 3, 4, 7b, 8, 9, 10, 11 and produce the F2 closure note, by:

1. clearing the single real blocker (#82) with its invariant pinned by a test rather
   than by a code reading;
2. arming and executing Wave 4 with an IAM pre-flight, because five IAM failures in F2
   surfaced only at apply and none were caught in review;
3. proving the happy path first and the failure path second, with the evidence for each
   kept separable;
4. recording what F2 cannot finish (Verification C, calendar C1–C7) as dated
   obligations rather than as silence.

## 2. Out of scope

- F3: eval engine, Freeze A, the Adjudicator ground-truth-labelability question. **Note
  C7:** out of scope for this directive, but on the critical path to the Verification C
  window — see §6.
- F4: 14-day continuous ingest, dashboards, SPA, real emitters.
- **ADR status flips.** `Proposed → Accepted` is a review output, not an authoring
  output. Claude Code does not flip ADR-0008 or any other ADR status in this directive.
- #36, #9, #7 — outside F2, not blocking.
- Any GCP resource created outside the gated apply path.
- Re-opening the `/healthz` interception question. It stays recorded as an unexplained
  known-unknown with no date attached.

## 3. Context files (read before starting)

- `docs/specs/F2-minimal-gcp-footprint.md` §7 (DoD, §7.1 calendar, §7.2 CN1–CN4).
- `F2-decision-log.md` — D1–D6, W0.\*–W3.8, A2.1–A2.13.
- `docs/runbooks/wave4-first-delivery.md` — pre-check, four-branch fault tree, success
  signature, base-table verification, dedup-premise check, DLQ triage.
- `docs/adr/ADR-0004` (Amendment 4), `ADR-0006`, `ADR-0007`, `ADR-0008`.
- `docs/architecture.md` §3.3–§3.4 (at-least-once + dedup, dead-letter path), §4.1 (views).
- PR #82 as authored; issues #17, #18, #47, #61, #63, #68, #74, #82.

## 4. Lane protocol

- **Lane A** (Claude Code, autonomous): everything not marked otherwise. Self-merge after
  green CI and gates.
- **Lane B** (human-armed apply): Wave 4 dispatch requires `gcp-production` reviewer
  approval. Claude Code dispatches, then **stops**.
- **Lane C** (human-only): #82 merge authority, billing console, account upgrade,
  key plaintext custody.

At every **STOP** marker Claude Code hands back with a structured status summary and does
not proceed on inference. No mid-phase interruptions otherwise.

A pre-granted Lane C approval (F2C-03, F2C-21) is valid only against the precondition
named with it. Preconditions are machine-checkable by construction; a precondition that
requires judgement to evaluate has not been pre-approved and returns to Lane C.

---

## 5. Task list

### Track A — Unblock #82 · Lane A + pre-granted Lane C approval · start now

**F2C-01 — Pin the nanos→micros truncation invariant with a test.**
ADR-0007's D7 table describes the code correctly: integer division on `ulong`, no
`Math.Round`. But the invariant is currently guaranteed by *reading* the code. A later
refactor that substitutes rounding would violate ADR-0007 silently and shift every span
boundary by up to one microsecond.
*Action:* add a golden/unit test in the worker normalization suite asserting truncation
at boundaries — 0, 1, 999, 1000, 1001, 1500, 1999, 2000 ns → 0, 0, 0, 1, 1, 1, 1, 2 µs.
Test name references ADR-0007.
*Acceptance:* the test fails when rounding semantics are substituted. Verify by inverting
the implementation locally; do not commit the inversion.
*Blocks:* #82 merge.

**F2C-02 — Make the dedup premise explicit and testable.**
The two-column dedup window is only correct if duplicate deliveries of the same span
carry an identical `start_time`. If that ever fails, duplicates land in different
partitions and the view under- or over-counts with no error surface — a silent
degradation, not a visible one.
*Action:* (a) state the premise as a header comment in the view SQL, where anyone editing
it will read it; (b) state it in #82's description; (c) add the verification query to
`wave4-first-delivery.md` as a mandatory step; (d) record it as a decision-log entry.
*Acceptance:* no code path relies on the premise without the premise being written
adjacent to it.

**F2C-03 — #82 merge. Lane C approval pre-granted 2026-08-30 (Decision 1).**
*Precondition, all four required:* F2C-01 green · F2C-02 landed · Gates A–H green · no
allowlist or protection rule loosened. All four are mechanically checkable; Claude Code
verifies and merges.
*Abort condition — approval is void if it fires:* the F2C-01 test shows the
implementation **rounds** rather than truncates. In that case: do not merge, do not
change the code to match ADR-0007, and do not amend ADR-0007. **STOP and hand back.**
A divergence between an ADR's decision table and the implementation is a review finding;
choosing which of the two is authoritative is a Lane C decision, not an execution detail.

### Track B — Wave 4 preparation · Lane A · runs in parallel with Track A; dispatch blocked by F2C-03

**F2C-04 — Wave 4 Terraform. Acceptance corrected by Amendment 2.**
`bigquery.tf` reads the SQL files, so the views enter the plan; `make e2e-cloud` is merged.
*Acceptance:* `terraform plan -detailed-exitcode` in the gated path shows the view
resources and nothing else — no Cloud Run configuration delta.
*Withdrawn:* the second half of the original acceptance ("the guard output shows the Cloud
Run guardrails were actually evaluated") was self-contradictory and is void. A plan with no
Cloud Run delta cannot carry a Cloud-Run-shaped attribute for the guard to evaluate; the
two halves excluded each other. `nothing in this plan carries a checked attribute` is the
guard behaving correctly, not a gap in the work. DoD 6 evidence moves to F2C-04b.

**F2C-04b — DoD 6 evidence, relocated. Lane A, read-only against live infrastructure: no
apply, no gated path, does not block on Wave 4 — but not cloud-independent (Amendment 3).**
DoD 6 makes two claims that were conflated. They need different evidence:

1. *State claim — the Cloud Run services are inside the guardrails.* Evidence: read
   `min-instances`, `max-instances`, region and instance size for `collector`,
   `ingestion-worker` **from the API**, not from any plan. This is strictly stronger than
   the plan-derived evidence DoD 6 previously carried. `analytics-api` is **not** in scope:
   it is F3's service and does not exist at F2. Record the `Cannot find service` result
   with its date rather than omitting the line — an unread line and a non-existent service
   are different facts, and this one is the dated baseline F3 entry will need when it takes
   up the guard-denies-`analytics-api`-by-design question.
2. *Control claim — the guard discriminates.* A guard that has never rejected anything is
   an unproven control. Evidence: a probe branch that sets `max_instances = 3` (or
   `min_instances = 1`), a plan run, and the guard's rejection captured; branch deleted,
   never merged, never applied. This is the same mutation technique that converted
   F2C-01 from "a test exists" into "the test discriminates".

*Acceptance:* both artefacts archived and dated. Neither may be inherited from an earlier
run (spec §7.2 CN4).

**F2C-05 — Pre-arm flight check. Immediately before dispatch, not earlier.**
Two failure modes have precedent in this phase and both are cheap to pre-empt:

1. *Pin decay (A2.13):* confirm the `6a504b4` images for `collector` and
   `ingestion-worker` are still in Artifact Registry. Cleanup keeps the last two tags and
   deletes anything older than a day; a pending wave outlives its own pin.
2. *IAM at apply:* enumerate every `setIamPolicy` call in the plan and, for each, verify
   the apply identity holds the required permission **by reading from the API**, not from
   the plan.
3. Update the apply-identity permission ledger with the result. This ledger has not been
   confirmed complete since F2-W3C; this task closes it or states what is missing.

*Acceptance:* a written pre-flight record with API-read evidence. Any failure → do not
dispatch, hand back. The plan job would reject an unapproved change anyway, but at the
cost of a dispatch.

**F2C-06 — Dispatch Wave 4 → `gcp-production` approval. Lane B. STOP.**

### Track C — Cloud-independent preparation · Lane A · parallel with A and B

This track is the reason the chain is not as serial as the snapshot states. Every item
here can be authored before Wave 4 exists.

**F2C-07 — Poison fixture and DLQ triage procedure, written before the drill.**
*Fixture:* a payload published directly to `traces` that the worker cannot deserialize
(non-gzip bytes or truncated protobuf), carrying attributes that make it identifiable in
the DLQ without opening the payload.
*Redaction rule — fills a gap in ADR-0006:* ADR-0006 places redaction post-deserialize,
pre-write. A poison message never reaches that stage, so the redaction boundary does not
cover it. Rule: DLQ evidence never contains payload bytes. Archive metadata only —
`message_id`, `publish_time`, delivery attempt count, message attributes, payload size,
SHA-256 of the payload. Write this into the DLQ runbook with an explicit reference to
ADR-0006 and the gap it fills.
*Acceptance:* the procedure is reviewable before any message is published.

**F2C-08 — Verify the DLQ alert from the API, before the drill.**
Confirm the `num_undelivered_messages > 0` policy exists, is enabled, and its notification
channel is real and deliverable. A drill that discovers a misconfigured alert has proven
nothing about the alert and has already spent the clean-DLQ precondition.

**F2C-09 — Synthetic walling for the F2 constructed payload. DECIDED 2026-08-30
(Decision 2).**
The constructed OTLP used for DoD 3 carries resource attribute `synthetic=true`. Without
it, the rows land in `spans_real` and contaminate F4's 14-day real-source window, which
F4 has no cheap way to clean afterwards.
*Consequences, now binding:*

1. DoD 3 is verified against `spans_deduped` under a partition filter.
2. `spans_real` is asserted to **exclude** those rows — the first live test of the
   walled-off-synthetic invariant, taken while it is free.
3. `wave4-first-delivery.md` sets the flag and names which view proves which claim.
   Amend it if it does not.

**F2C-10 — Draft the closure-note skeleton** (CN1–CN4 per spec §7.2) with placeholders.
Filled from measurement after the chain completes — authored now, not authored later.

### Track D — First delivery · blocked by F2C-06 approval

**F2C-11 — Execute `wave4-first-delivery.md`. Closes DoD 7b.**
7b is binary and cannot be rehearsed: nothing local can mint a Google-signed token, so the
first delivery *is* the exam.
*On failure:* follow the four-branch fault tree. **Do not retry blind.** Each failed
delivery burns five attempts and deposits a message in the DLQ, which contaminates DoD 4's
evidence — see F2C-13.

**F2C-12 — DoD 3 evidence.**

1. Partition-filtered read from `spans_deduped` returns the delivered spans.
2. Base-table row count recorded alongside the view count.
3. Dedup premise checked empirically: publish the same export twice, assert base table
   `2n` and view `n`, and assert the duplicate pair shares `start_time` (F2C-02).
4. `spans_real` excludes the synthetic rows (F2C-09).

*Acceptance:* query text and results archived. DoD 3 is marked from this measurement,
never from the fact that the apply succeeded.

### Track E — Failure path · after Track D succeeds

**F2C-13 — Drill preconditions.**
Drain the DLQ and clear the alert **before** the drill, and record the pre-drill depth as
0. Otherwise "the alert fired" is not attributable to the drill, and the DoD 4 evidence is
indistinguishable from first-delivery fallout.

**F2C-14 — Execute the poison drill. Closes DoD 4.**
*Acceptance:* message reaches `traces-dlq` after 5 attempts; alert fires; triage rehearsal
performed and archived under the metadata-only rule (F2C-07); and — the step usually
omitted — a subsequent valid delivery still succeeds, proving the main subscription
recovered rather than being left in an unproven state.

### Track F — Billing, credit and calendar · Lane C · does not block Tracks A–E

**F2C-15 — DoD 8 / Verification B (#18):** a real budget notification read with
`costAmount = 0.00`. Lane C captures; Lane A archives the notification's raw fields, not a
screenshot alone.

**F2C-16 — DoD 9:** credit-lag procedure live with at least one data point.

**F2C-17 — DoD 10:** period invoice fully credit-offset (#17).

**F2C-18 — Calendar C1–C7 written into the closure note as dated items.**
Approved 2026-08-30 (Decision 3) as a ceiling. **Open sub-item:** C1 is approved as
`≤ 2026-09-28`, which is the constraint restated, not a date. A ceiling with no pinned
date drifts to the ceiling; a slip past it cascades into C2 (live-fire before the window
opens) and C3 (earliest open 2026-10-05). Pin a date.

**F2C-19 — C7 (new, this amendment): the window's engineering prerequisite.**
C4 requires Verification C's window and F4's continuous-ingest window to be one calendar
block. That is only achievable if, on the day the window opens, F3 has exited and all
three emitters are instrumented and emitting. No calendar item owns that.
*Constraint:* F3 exit + three emitters ingest-ready **≤ 2026-10-04**.
*Blocked by:* Freeze A, the F3 entry gate, which is behind the unresolved Adjudicator
ground-truth-labelability question. That question has no scheduled session.
*If C7 misses:* the block splits, Verification C runs on an idle or synthetic-only system,
and the cost result degrades from "gross $0.00 under real load" to "gross $0.00 while
idle" — a materially weaker claim, and a month to redo. That trade is a Lane C decision if
it arises; it is not taken by default through schedule slip.

**F2C-23 — Fix the SQL scanner, do not fence the SQL. Lane A, follow-up issue, not in
#82's scope.**
Decision log W2.16 found that a `--` comment containing the two keywords that open the
partitioning clause suppresses view creation, and that a second site survived only because a
`;` happened to follow it. The comments were reworded and CI is green; the scanner is
unchanged.
*The proposed alternative — a gate forbidding those keywords in `analytics/sql/*.sql`
comments — is rejected.* It encodes the wrong invariant. F2C-02 mandates an explanatory
premise comment in exactly these files; a keyword ban makes the file hostile to the
documentation this directive requires, and it makes the codebase accommodate a defective
parser instead of fixing it. It is also the repo's existing lesson pointed the wrong way:
the forbidden-string rule says a scanner must not match its own representation. The
generalisation is that a scanner reading code must not read comments as code.
*Action:* strip `--` line comments and `/* */` blocks before keyword scanning; add the
regression test in §8; leave a short marker in the SQL file referencing W2.16 and this
issue, so the current wording is not "tidied" back into the trap. Do not restate the
trigger words in that marker.
*Priority:* not a Wave 4 blocker — current state is green. But `bigquery.tf` reads these
SQL files, so the trap sits on the apply path, not only on CI. File the issue now, carry it
in the closure note as a dated obligation, and let execution land in F3 if it does not fit
before closure. Losing it to "later" is the failure mode to avoid.

### Track G — Closure

**F2C-20 — DoD 11.** Close the decision log: D1–D6, W0.\*–W3.8, A2.1–A2.13, plus entries
created by this directive (F2C-02 premise, F2C-09 synthetic decision, F2C-07 redaction
rule, F2C-05 permission ledger, W2.16 scanner finding, Decisions 1–4, and the Amendment 2
and Amendment 3 corrections). Close #63 and #47.

**F2C-21 — Closure note (CN1–CN4).** Carries forward as **dated open obligations**:
DoD 13 / Verification C (gross $0.00 after credit exhaustion, post-upgrade live-fire,
14-day window); C1–C7; #68 with ADR-0008 left at `Proposed` (status flip is a review
output — do not flip it); **#61 open until F2C-12** — #82 merged the corrected view
definitions but did not deploy them, and #61 closes on a partition-filtered read succeeding
against the cloud views, not on the merge; `/healthz` interception recorded as an
unexplained unknown with no date attached.

**F2C-22 — Remove standing apply roles from human principals. APPROVED 2026-08-30
(Decision 4), with sequencing constraints.**
The bootstrap paradox was recorded as a spec defect; leaving the roles attached past F2
converts a recorded defect into standing exposure.
*Ordering, binding:*

1. **After** F2 exit — after Wave 4 apply, first delivery and the DLQ drill. Removing the
   roles while a wave can still need local recovery trades one exposure for an outage.
2. The break-glass runbook is **written and dry-run before** removal, not after. Removing
   the roles against an untested recovery path repeats the F2C-08 error class: an
   unverified control counted as a control.
3. The Lane B armed-apply path (GitHub Environment + WIF service account) is untouched;
   this removes human principals only.

*Acceptance:* roles removed, verified by reading the IAM policy from the API; break-glass
runbook committed with a dated dry-run record.

---

## 6. Where the chain is serial, and where it is not

Genuinely serial — each link needs the previous one to exist:

```
#82 merge → Wave 4 plan → dispatch → approval → first delivery (7b) → DoD 3 → DoD 4 → closure
```

Not serial, and currently scheduled as if it were:

- **F2C-01, F2C-02** (Track A) — pure repo work, no cloud dependency.
- **F2C-07, F2C-08, F2C-09, F2C-10** (Track C) — fixtures, runbook text, alert
  verification, closure skeleton. All authored against the current cloud, before Wave 4.
- **Track F** — Lane C, calendar-bound, independent of the chain.

Only *verification* is serial. Preparation is not. Running Track C during the wait for
#82 and for `gcp-production` approval removes it from the critical path entirely.

**Revised critical path after Amendment 1.** F2's own critical path is two human actions:
the #82 precondition check and Wave 4 arming. But the *project's* critical path to
2026-10-05 no longer runs through F2 at all — it runs through the Adjudicator
ground-truth-labelability question → Freeze A → F3 exit → emitter instrumentation → C7.
F2 completion has roughly five weeks of runway against that date; F3 entry, which is
blocked on an unscheduled design question, does not. The snapshot's claim that F3 is the
chain's only slack inverts this: F3 is not slack, it is the binding constraint.

## 7. Acceptance criteria — F2 exit

1. DoD 3, 4, 7b, 8, 9, 10, 11 satisfied, each **measured at closure**, none carried from a
   prior summary (spec §7.2 CN4).
2. DoD 5, 6, 12 **re-measured** at closure rather than inherited from the 2026-08-30
   snapshot: `terraform plan -detailed-exitcode` → 0; DoD 6 evidenced per F2C-04b (API read
   of the three Cloud Run services **plus** a captured guard rejection), not from a plan
   that happens to contain no Cloud Run resources; Gates A–H green with no rule, allowlist
   or protection loosened during #82 or Wave 4. Where a required check was satisfied by a
   path-filter skip, the skipped job is named in the closure note — a skipped job is not a
   passing job.
3. DoD 13 / Verification C recorded as a dated obligation with C1–C7 attached — explicitly
   not claimed as complete.
4. Every infrastructure claim in the closure note verified by reading from the API, not
   from plan or apply output.
5. Apply-identity permission ledger complete, or its remaining gap stated.
6. Break-glass runbook committed and dry-run recorded (F2C-22 precondition), whether or
   not role removal has executed by closure.
7. Zero occurrences of any forbidden legacy-name pattern under the self-non-matching
   pattern form; no exclusion list required.

## 8. Test expectations

- **F2C-01:** boundary test on nanos→micros truncation; fails under rounding semantics.
- **F2C-02 / F2C-12:** duplicate-injection check — base table `2n`, view `n`, identical
  `start_time` across the pair.
- **F2C-09 / F2C-12:** `spans_real` excludes rows flagged `synthetic=true`.
- **F2C-11:** first delivery is the test for 7b; no substitute exists.
- **F2C-14:** poison → DLQ after 5 attempts, alert fires from a depth of 0, main
  subscription recovers on the next valid delivery.
- **F2C-04b:** guard rejects a deliberately out-of-range Cloud Run attribute on a probe
  branch; rejection text archived, branch deleted, never applied.
- **F2C-23:** regression test places the trigger keywords inside a `--` comment and asserts
  every view is still created.
- **F2C-22:** break-glass runbook dry-run, dated, before removal.
- Emulator results are labelled as emulator wherever archived; they never satisfy a DoD
  item that names the cloud.
- No test asserts a triviality to make a job look real (F0 §6 carries forward).

## 9. Decisions of record

Approved by Lane C on 2026-08-30. These are decision-log entries, not proposals.

| # | Decision | Recorded outcome | Constraint attached |
|---|---|---|---|
| 1 | Merge #82 | Approved in advance | Void if F2C-01 shows rounding → STOP, hand back (F2C-03) |
| 2 | `synthetic=true` on the F2 constructed payload | Decided | DoD 3 proves via `spans_deduped`; `spans_real` exclusion asserted (F2C-09) |
| 3 | Account upgrade ≤ 2026-09-28 | Approved as ceiling | Concrete date still unpinned; C7 added (F2C-18, F2C-19) |
| 4 | Remove standing human apply roles + break-glass runbook | Approved | After F2 exit; runbook written and dry-run first (F2C-22) |

### Remaining Lane C items

1. **Pin C1 to a date.** A ceiling is not a date.
2. **Schedule the Adjudicator ground-truth-labelability session.** It gates Freeze A,
   which gates F3, which gates C7, which gates the single calendar block C4 requires. It
   is a separate conversation and it is on the critical path to 2026-10-05 — not F2's
   critical path, the project's.
