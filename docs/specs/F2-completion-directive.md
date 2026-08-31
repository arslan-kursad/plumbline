# F2 — Completion Directive

**Version:** 1.7 (Amendment 7) · **Status:** Approved · **Date:** 2026-08-31
**Canonical copy:** `docs/specs/F2-completion-directive.md` in the repo. The chat-side copy
is a snapshot and loses its tie to the repo the moment it is not re-committed (Project
Brief, working model). Every amendment is committed before it is executed against, and the
decision log records the commit SHA — otherwise "which version" is unanswerable, which is
how Amendment 2 came to be read as missing.
**Lane C sign-off:** 2026-08-30 — Decisions 1–4 of §9 approved · 2026-08-31 — Amendment 7,
Decisions 5–17 and the §4 autonomy envelope approved
**Baseline:** `main` @ `490beac` · #82 merged · live readings of 2026-08-31, project `plumbline-19458`
**Executor:** Claude Code (Lane A), with explicit hand-backs to Lane B (armed apply) and Lane C (human-only)
**Repo target:** `docs/specs/F2-completion-directive.md`

This directive is the single approval artefact for taking F2 from its current blocked
state to phase exit. It does not restate the DoD; it sequences the remaining work and
adds the checks the current plan does not yet contain.

**Authority order on conflict:** `docs/specs/F2-minimal-gcp-footprint.md` §7 (DoD) →
`F2-decision-log.md` (decisions) → `docs/architecture.md` §10 (ADR status) → this
document. If any of those contradict a line here, they win and this line is stale.

### Amendment 7 (2026-08-31, the executable chain and the autonomy envelope)

Removes the two things that made the remaining chain need a confirmation round-trip per
step: undecided shape inside `make e2e-cloud`, and a permission story that was wrong about
itself. Four claims in the proposal did not survive being read against the repo. They are
corrected here rather than committed, and every measurement below is dated.

- **The deny-list does not refuse monitoring reads, and the class it was said to block was
  never blocked.** The proposal's largest decision — move read-only verification into a new
  CI workflow — rested on `.claude/settings.json` permitting Cloud Run reads and refusing
  monitoring reads. It carries no monitoring rule at all. The entry that denied F2C-08.1 is
  `Bash(gcloud alpha:*)`, and the command reached for was `gcloud alpha monitoring policies
  list`, which is what [`f2-dod4-alert-configuration.md`](../evidence/f2-dod4-alert-configuration.md)
  records. The GA surface is not denied. Measured 2026-08-31 from Lane A:
  `gcloud monitoring policies list` returned the `traces-dlq` policy enabled, and IAM
  policy, Pub/Sub subscription config, the Cloud Run service list, Artifact Registry tags
  and the deployed view DDL all read the same day from the same lane. Decision 5 keeps the
  artefact and drops the workflow.
- **F4's uptime check is not decided to bind `/health`, and that decision is not homeless.**
  The proposal asked the closure note to carry `/health` as a constraint F4 inherits.
  [`F2-directive-w3c-consolidation.md`](F2-directive-w3c-consolidation.md) §5 measured
  `/health` on 2026-08-26 returning Go's `404 page not found` — the collector registers
  `/healthz` and `/v1/traces` and nothing else — and recorded the binding as **undecided
  rather than written down wrong**; its §6 lists the path as Open. Writing the proposed
  sentence would have committed the binding that document deliberately refused. What the
  closure note carries is the open question and its three options, per §2 here and
  [`collector-endpoints.md`](../runbooks/collector-endpoints.md).
- **The closure note already schedules DoD 1 and 2, and its placeholder count was
  overstated.** [`F2-completion-note.md`](F2-completion-note.md) carries *(placeholder)* on
  DoD 1, 2, 5 and 12 — the four items the proposal wanted added to a re-derived-at-closing
  bucket. The note holds **16** placeholders, not 18: the higher figure counts two prose
  lines that describe placeholders rather than being ones. Nothing is added and the count
  does not move. The bucket defect the proposal found is real, and it is in the ledger's
  accounting rather than in the note.
- **The Wave 4 image pin has decayed a second time.** F2C-05 asks for the `6a504b4` images.
  Read 2026-08-31, neither image carries that tag: the `plumbline` repository holds
  `0117848d`…`c9391033`, with current `main` (`490beac4`) present and `6a504b4`
  (2026-08-26) already collected. This is A2.13 recurring in exactly the way A2.13 said a
  blocked wave would produce it. Decision 17 stops carrying a SHA at all. The registry also
  holds one repository and the second image is `worker`, not `ingestion-worker`; F2C-05 is
  corrected below on both points.
- **Autonomy envelope added to §4**, the ordered chain to §6, decisions to §9 as 5–17. The
  envelope trades *ask before* for *audit after*. That trade holds only while the residual
  uncertainty in each decision is written down rather than resolved quietly, which is why
  the recording clause is normative and not advice.

### Amendment 6 (2026-08-30, sequencing `make e2e-cloud`)

Answers the ordering question and fixes what asking it exposed.

- **Order: harness, then runbook.** `make e2e-cloud` is written and merged first; F2C-09's
  runbook correction follows and is written *from the harness as built*. Writing the
  runbook first would document intent and let the harness diverge from it silently — the
  error class that produced F2C-01, the #61 claim and F2C-23's apply-path assertion.
  F2C-09 conflated two layers and is corrected below: the **decision** is already recorded
  (Decision 2), the **harness** sets the flag, the **runbook** documents it.
- **F2C-04 was reported and accepted as satisfied while half of it was open.** The
  `make e2e-cloud` clause sits in the task body, and the Amendment 2 correction touched only
  the acceptance criterion, so nothing recorded the open half. It is Lane A work standing
  between here and F2C-06 arming. §6 corrected accordingly.
- **Running the harness against the cloud is not "another send-shaped action"** — it is
  F2C-11, and it is already gated by Wave 4 arming. But the harness's *first* cloud
  execution is the DoD 7b exam, so writing it creates a way to spend that exam by accident.
  Constraint added below: write it, merge it, do not run it against the cloud until F2C-11.
- **§4's send rule was ambiguous.** "Publishing" read as "publishing a message"; it meant
  publishing outside the project. Reworded below around the test that actually matters —
  whether the effect reaches a party outside the project.
- **ADR-0006 wording corrected to the executor's, which is more precise.** Not a gap this
  directive fills in a defective ADR: the boundary is correctly drawn for its own path, and
  the DLQ path was never inside it. An accepted ADR is not implied defective in passing.

### Amendment 5 (2026-08-30, permission and send boundaries)

Answers two questions raised during F2C-08 and generalises both so they do not recur
per-task.

- **Send-shaped actions need a per-instance go-ahead even when an approved directive names
  them.** Added to §4. The executor was right to stop: a directive approves a plan, not the
  moment of firing. This is the same shape as Lane B — the plan is approved, the apply is
  still armed separately.
- **F2C-14 is also send-shaped** and nobody had noticed. The drill fires a real alert into
  a real inbox. Flagged below so it is not discovered mid-drill.
- **F2C-08's API read stays an API read when a human runs the command.** Provenance clause
  added below. Reading the policy out of `pubsub.tf` would be reading intent, not state,
  which is the substitution this whole task exists to refuse.
- **Deny-list shape defect recorded, deliberately not fixed during F2.** See below.

**Deny-list shape defect.** The Lane A permission layer allows reading Cloud Run services
from the API (F2C-04b did exactly that) and denies reading monitoring policies from the
API. Same class, opposite verdicts: the list is enumerated, not principled. It will recur
one command at a time — Scheduler reads in F3, uptime-check reads in F4.
*Not fixed here, on purpose.* DoD 12 requires that no gate, allowlist or protection rule was
loosened during the phase. The `.claude/settings.json` deny-list is a different artefact
from the Terraform resource-type allowlist DoD 12 names, and resolving the tension by that
technicality is worse than the one manual step it saves. The shaped rule — read-only
`describe`/`list` on project resources is Lane A; anything that mutates, sends, spends, or
touches billing or secrets is not — goes to F3 entry with the `CLAUDE.md` principles work
already queued there.
*Also correct:* refusing to retry the same read under a different `gcloud` spelling. A deny
attaches to the intent, not to the string.

### Amendment 4 (2026-08-30, post-measurement)

Closes #91. Two corrections and one refinement, all against this directive rather than
against the work.

- **F2C-23's apply-path claim is withdrawn — it was an assumption, and it was wrong.**
  A dry-run against real BigQuery with the pre-fix comment and a three-column body returns
  `Query successfully validated.` Production parses the comment correctly. `bigquery.tf`
  reaches BigQuery, not the emulator, so the trap never sat on the apply path. The claim was
  derived from the architecture rather than measured, which is the failure this project
  names first; the measurement cost nothing because a dry-run creates nothing.
- **F2C-23's premise is also withdrawn: there is no scanner of ours to fix.** `seed.py`
  POSTs the file verbatim via `read_text()`; every match under `scripts/` is plain text
  inside a comment. The misparsing parser is `goccy/bigquery-emulator` 0.8.1, third-party
  and already at its latest release. Rewritten below.
- **§7 criterion 2** still said "three Cloud Run services" after Amendment 3 corrected
  F2C-04b to two. One site fixed, the other left. Corrected below, and see the hygiene rule.
- **F2C-08** refined: an API read proves configuration, not delivery. Split below.

**Amendment hygiene rule, effective now.** After any amendment, grep the document for every
other occurrence of the changed claim before shipping. Amendment 3 fixed F2C-04b and left
criterion 2; that is the same one-site-of-two error twice over in this directive, and it is
mechanically preventable.

**Not silently corrected.** The executor raised #91 with the measurement attached rather
than editing an approved directive. That is the required behaviour and the reason this
amendment exists rather than a quiet diff.

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
  *Superseded by Amendment 4: there is no scanner of ours; the defect is in the emulator.*
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

**Send-shaped actions (Amendment 5, reworded by Amendment 6).** The test is whether the
effect **reaches a party outside the project** — an inbox, the public web, a vendor. Those
require a per-instance go-ahead even when this directive names them, because naming an
action in an approved plan is not arming it. Everything confined to the repo and to the
project's own GCP state is covered by the directive and needs no further confirmation, and
that explicitly includes publishing OTLP into our own collector: it reaches nobody outside,
and it is gated by Wave 4 arming instead. The no-mid-phase-interruptions property holds for
all of it. In F2 the send-shaped actions are exactly three: F2C-06 (dispatch), F2C-08.2
(channel test) and F2C-14 (the drill's alert).

**Autonomy envelope (Amendment 7).** Inside this directive the executor's default is to
decide and record. Asking is available only for Class 3.

*Class 1 — decide, record, proceed.* Implementation shape inside an approved task: file
layout, naming, language idiom, test structure, helper decomposition. Fixture design,
naming and manifest entries under the W3C.2 provenance rule. Branch selection inside a
documented runbook's error tree. A choice between Terraform expressions that produce an
identical plan. Wording of non-normative documentation. Re-running a failed CI job when
neither the rule nor the code changed. A choice between two measurement methods where both
read from the API.

*Class 2 — decide, record, proceed, and open an issue.* A finding that changes a task's
method but not its acceptance criterion. A spec defect correctable without touching
normative text elsewhere. Discovered work inside the phase's scope that no task names.
Never chat-only: decided-but-uncommitted normative text belongs in an issue, and this
project has already paid once for a directive that lived only as a chat snapshot.

*Class 3 — stop, report, do not decide.* A plan diff outside the wave's declared resource
set. Any finding that contradicts an Accepted ADR. Any ADR status flip. Any edit to
`docs/eval-plan.md`. Any change to `.claude/settings.json` or to what a gate A–H asserts.
Any send-shaped action, per the paragraph above. Any path that would produce evidence
weaker than a DoD item specifies. Any circumstance in which the DoD 7b exam could be spent
outside F2C-11. Spend > $0.00 on two consecutive days (Decision 16).

Class 3 is a stop, not a request for permission to continue: the report names the trigger
and the state at the stop, and does not propose a workaround in the same breath.

**Recording is what makes the envelope safe.** For Classes 1 and 2 the decision-log entry
names the decision, the alternative not taken, and the residual uncertainty. The last of
those is the load-bearing one: the envelope substitutes *audit after* for *ask before*, and
an entry that records only the outcome leaves nothing to audit. Amendment 7 is itself the
worked example — four of its own proposed claims were wrong against the repo, and they were
found by reading rather than by asking.

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

**F2C-04 — Wave 4 Terraform. Acceptance corrected by Amendment 2; split by Amendment 6.**
Two halves, only the first of which is done:

1. *Terraform — satisfied.* `bigquery.tf` reads the SQL files, so the views enter the plan.
2. *`make e2e-cloud` — open, Lane A, prerequisite of F2C-06 arming.* The spec requires it
   merged before arming, and the reason is not convenience: the first delivery is DoD 7b's
   exam, and an exam executed by an ad-hoc command is weaker evidence than one executed by
   reviewed, committed code. It also carries the `synthetic=true` flag (Decision 2), so it
   is the artefact F2C-09's runbook correction documents.
   *Constraint:* write it and merge it; **do not run it against the cloud before F2C-11.**
   Its first cloud execution is the 7b exam, and the exam can only be taken once. A dry or
   emulator run to validate the harness is fine and is labelled emulator per §8.

*Acceptance:* `terraform plan -detailed-exitcode` in the gated path shows the view
resources and nothing else — no Cloud Run configuration delta; `make e2e-cloud` merged and
unrun against the cloud.
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

1. *Pin decay (A2.13, recurred — Decision 17):* re-derive the pin from current `main` at
   dispatch, then confirm both images carry that tag in Artifact Registry. **Do not confirm
   a SHA written in this directive.** `6a504b4` was named here and, read on 2026-08-31, had
   already been collected from both images. There is one repository, `plumbline`, and the
   images are `collector` and `worker` — not `ingestion-worker`. Cleanup keeps the last two
   versions and deletes anything older than a day, so a pending wave outlives its own pin;
   that has now happened twice, and the second time the pin was carried in the document
   telling the executor to trust it.
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
*Redaction rule — a scope gap, not a defect in ADR-0006 (Amendment 6):* ADR-0006 places
redaction post-deserialize,
pre-write. A poison message never reaches that stage, so the redaction boundary does not
cover it. Rule: DLQ evidence never contains payload bytes. Archive metadata only —
`message_id`, `publish_time`, delivery attempt count, message attributes, payload size,
SHA-256 of the payload. Write this into the DLQ runbook with an explicit reference to
ADR-0006 and the gap it fills.
*Acceptance:* the procedure is reviewable before any message is published.

**F2C-08 — Verify the DLQ alert before the drill. Split into two claims by Amendment 4.**

1. *Configuration, from the API:* the `num_undelivered_messages > 0` policy exists, is
   enabled, and is bound to a notification channel.
2. *Delivery, proven not read:* send a test notification to that channel. An API read shows
   a channel is configured; it does not show a message arrives. Counting a configuration
   read as proof of delivery is the unproven-control error this directive spends four other
   tasks avoiding. The channel test is independent of the policy, so it costs nothing and
   does not touch the DLQ.
3. *Out of scope here:* that the policy itself fires end-to-end. That is proven only by
   F2C-14, and it is the drill's job, not this task's.

*Provenance (Amendment 5):* if the Lane A permission layer denies the read, a human runs
the command and hands back the **raw, unedited output together with the exact command
line**. That is still reading from the API; a human at the keyboard changes who typed it,
not what was read. Reading the policy definition out of `pubsub.tf` is not a substitute —
that is intent, and this task exists to refuse the substitution of intent for state.
*Send-shaped:* claim 2 requires a go-ahead per §4. Record the channel test's timestamp; it
is needed by F2C-13.

*Acceptance:* both artefacts archived. A drill that discovers a misconfigured alert has
proven nothing about the alert and has already spent the clean-DLQ precondition.

**F2C-09 — Synthetic walling for the F2 constructed payload. DECIDED 2026-08-30
(Decision 2).**
The constructed OTLP used for DoD 3 carries resource attribute `synthetic=true`. Without
it, the rows land in `spans_real` and contaminate F4's 14-day real-source window, which
F4 has no cheap way to clean afterwards.
*Consequences, now binding:*

1. DoD 3 is verified against `spans_deduped` under a partition filter.
2. `spans_real` is asserted to **exclude** those rows — the first live test of the
   walled-off-synthetic invariant, taken while it is free.
3. The flag is set by `make e2e-cloud` (F2C-04.2), not by the runbook. Three layers, in
   order: the **decision** is recorded here and needs nothing further; the **harness** sets
   the flag; the **runbook** documents it and names which view proves which claim.
   *Sequencing (Amendment 6):* the runbook correction is written after the harness is
   merged, from the harness as built — not before it, from intent.

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
*Added by Amendment 5:* leave a clear gap between F2C-08's channel test and the drill, and
record both timestamps. Two notifications arriving close together into the same inbox are
not separable after the fact, and attribution is the entire point of this task.

**F2C-14 — Execute the poison drill. Closes DoD 4. Send-shaped (Amendment 5): needs its
own go-ahead — the drill fires a real alert into a real inbox.**
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

**F2C-23 — Strip comments in the seeder; record the emulator divergence. Rewritten by
Amendment 4 (#91). Lane A, off the critical path.**
W2.16 found that a `--` comment containing the two keywords opening the partitioning clause
suppresses view creation, and that a second site survived only because a `;` followed it.
Measurement then relocated the defect: real BigQuery validates the pre-fix comment; only
`goccy/bigquery-emulator` 0.8.1 misparses it, and that is its latest release.
*Standing rejection, unchanged:* a gate forbidding those keywords in `analytics/sql/*.sql`
comments encodes the wrong invariant. F2C-02 mandates an explanatory premise comment in
exactly these files; a keyword ban makes the file hostile to the documentation this
directive requires.
*Action, per #91:* strip `--` line comments in `seed.py` before the file is POSTed. This is
the faithful reading of the original intent and it is in our code, where the third-party
parser is not. Once it lands, revert the circumlocution in `002` to plain wording — that
plain comment is the artefact F2C-02 asked for, and the workaround currently prevents it.
Keep the marker referencing W2.16 and #91 until the strip lands, so the awkward phrasing is
not "tidied" back into the trap; drop the marker with the workaround.
*Record, separately from the fix:* this is an emulator/production divergence, not a bug in
our code. The observed direction is false-red — CI fails on SQL production accepts, which
cost four probes. **The unobserved direction is the one that matters: CI green on SQL
production would reject.** It is unmeasured and out of scope for F2. Architecture §8 rests
the whole local-first model on emulator fidelity, so record the divergence with its named
instance in the closure note and let F3 decide whether emulator fidelity needs a test of its
own. Do not chase it here.
*Priority:* not a Wave 4 blocker and not on the apply path. Land it before the closure note
if it fits; carry it forward if it does not. No urgency is manufactured for it.

### Track G — Closure

**F2C-20 — DoD 11.** Close the decision log: D1–D6, W0.\*–W3.8, A2.1–A2.13, plus entries
created by this directive (F2C-02 premise, F2C-09 synthetic decision, F2C-07 redaction
rule, F2C-05 permission ledger, W2.16 and W2.17, Decisions 1–4, and the Amendment 2
through Amendment 6 corrections, W2.18 through W2.20, and the deny-list shape defect).
Close #63 and #47; #91 closes with F2C-23.

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

**Revised critical path after Amendment 1, corrected by Amendment 6.** F2's own critical
path is not two human actions. `make e2e-cloud` (F2C-04.2) is unwritten Lane A work
standing between here and arming, so the path is: write and merge the harness → arm →
first delivery. The #82 check is spent; Wave 4 arming remains. But the *project's* critical path to
2026-10-05 no longer runs through F2 at all — it runs through the Adjudicator
ground-truth-labelability question → Freeze A → F3 exit → emitter instrumentation → C7.
F2 completion has roughly five weeks of runway against that date; F3 entry, which is
blocked on an unscheduled design question, does not. The snapshot's claim that F3 is the
chain's only slack inverts this: F3 is not slack, it is the binding constraint.

### The ordered chain (Amendment 7)

Lane A steps need no approval and are not to be batched into a question. Ordering binds
wherever a step's precondition names a prior step.

**Stage 1 — Lane A, unblocked.**

| # | Task | Precondition | Done when |
|---|---|---|---|
| 1 | Commit Amendment 7 as v1.7; decisions 5–17 into §9 | — | v1.7 in repo, its SHA recorded in the decision log as v1.3–v1.6 were |
| 2 | `scripts/state-readout.sh` (Decision 5) + first run archived | 1 | Artefact carries every reading in Decision 5; command and raw output archived under `docs/evidence/` |
| 3 | F2C-23: seeder fix, closing #91 | — | Emulator no longer parses comments as code; the W2.16 probe shape is the regression test |
| 4 | F2C-04.2: harness, both entry points (Decisions 6–13) | 1 | Merged. **Not run against the cloud.** Emulator and dry runs labelled emulator per §8 |
| 5 | F2C-09: runbook correction, derived from the harness as built | 4 | Names which view proves which claim; sequencing per Amendment 6 |
| 6 | F2C-05: pre-arm flight check — pin re-derived from `main` (Decision 17), every `setIamPolicy` permission read from the API, apply-identity ledger closed | 2 | Ledger closed; any missing grant recorded as a finding, not routed around |

**Stage 2 — Lane B gate.**

| # | Task | Lane | Note |
|---|---|---|---|
| 7 | Wave 4 plan + dispatch | A | Empty-plan guard and fixture provenance apply as they stand |
| 8 | `gcp-production` environment approval | **C — human** | Cannot be delegated; delegating it deletes Lane B |
| 9 | Apply | A | Post-apply `No changes` plan retained as fixture |

**Stage 3 — post-apply, Lane A.**

| # | Task | Precondition | Done when |
|---|---|---|---|
| 10 | F2C-11: first delivery, `PLUMBLINE_E2E_TARGET=cloud` (Decision 10). **DoD 7b exam** | 9 | Google-signed token accepted, or the error-tree branch named. No blind retry |
| 11 | F2C-12: DoD 3 evidence (Decision 13) and #61 closure — deployed view read from the API shows the three-column `PARTITION BY`, partition-filtered read succeeds | 10 | Both claims measured, not asserted |
| 12 | Drain DLQ, record depth 0 | 11 | Depth read from the state readout |

**Stage 4 — Lane C gate, then the drill.**

| # | Task | Lane | Note |
|---|---|---|---|
| 13 | F2C-08.2: channel test | **C — human go-ahead** | Send-shaped. Send timestamp recorded (Decision 14) |
| 14 | ≥ 30 min separation | — | Or a distinguishing marker, if the channel admits one (Decision 14) |
| 15 | F2C-13/14: `make e2e-cloud-drill` — poison → DLQ → alarm → triage archive. **DoD 4** | A | Archive per F2C-07's enumeration: `message_id`, `publish_time`, attempt count, attributes, size, SHA-256. Nothing else |

**Stage 5 — closure.**

| # | Task | Done when |
|---|---|---|
| 16 | F2C-20: decision log closed. **DoD 11** | Every decision 5–17 present with its residual uncertainty |
| 17 | Re-derive DoD 1, 2, 5 and 12 at closure | Four items measured at closure, none carried. The note already carries their placeholders |
| 18 | F2C-10: fill the note's **16** placeholders by measurement | No placeholder filled by deciding that a measurement would have passed |
| 19 | Close #63, #47, #91. Record carried obligations: #68, DoD 8/9/10/13, C1–C7, the F4 uptime-check path as **open** (§2), the Lane A deny-list shape defect, and the unmeasured direction of the emulator/production divergence | Every skipped mandatory CI job named in the closure note |
| 20 | F2C-22, after F2 exit: break-glass runbook written **and dry-run**, then standing apply roles removed from human principals | Order binds. Removing access against an untested recovery path repeats F2C-08's error class |

## 7. Acceptance criteria — F2 exit

1. DoD 3, 4, 7b, 8, 9, 10, 11 satisfied, each **measured at closure**, none carried from a
   prior summary (spec §7.2 CN4).
2. DoD 5, 6, 12 **re-measured** at closure rather than inherited from the 2026-08-30
   snapshot: `terraform plan -detailed-exitcode` → 0; DoD 6 evidenced per F2C-04b (API read
   of the two deployed Cloud Run services, plus the dated `Cannot find service` record for
   `analytics-api`, plus a captured guard rejection), not from a plan
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
8. Amendment 7 committed as v1.7, with decisions 5–17 carrying real numbers in §9 and each
   carrying its residual uncertainty.
9. `scripts/state-readout.sh` produces one artefact answering every reading in Decision 5.
   No remaining F2 verification requires a human to paste command output; where one still
   does, the blocking rule is named rather than worked around.
10. `make e2e-cloud` and `make e2e-cloud-drill` merged, unrun against the cloud, with
    Decisions 6–13 present **in code** rather than in the runbook that describes the code.
11. DoD 3, 4 and 7b measured after Wave 4, each by a query or an API read, none by an apply
    having succeeded.
12. Closure note complete: 16 placeholders filled by measurement, C1 holding a date rather
    than a ceiling, carried obligations enumerated.
13. Period bill consistent with the phase's thesis, and the two-day escape hatch
    (Decision 16) either unfired or fired with its incident note written.

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
- **Harness self-tests run in both directions (Amendment 7).** The stage-0 provenance check
  must fail against a deliberately mismatched view definition and pass against the deployed
  one. The cloud-target guard (Decision 10) must refuse without the arming variable. The
  volatile-field allowlist (Decision 12) must fail when a non-allowlisted field differs. A
  check that has never been shown to fail is not yet evidence.
- **The unmeasured direction stays named.** CI green while production would reject is not
  retired by a harness dry run, and the closure note says so rather than omitting it.
- **No existing gate's assertion changes.** A newly red job is a finding, not a threshold.

## 9. Decisions of record

Approved by Lane C on 2026-08-30. These are decision-log entries, not proposals.

| # | Decision | Recorded outcome | Constraint attached |
|---|---|---|---|
| 1 | Merge #82 | Approved in advance | Void if F2C-01 shows rounding → STOP, hand back (F2C-03) |
| 2 | `synthetic=true` on the F2 constructed payload | Decided | DoD 3 proves via `spans_deduped`; `spans_real` exclusion asserted (F2C-09) |
| 3 | Account upgrade ≤ 2026-09-28 | Approved as ceiling | Concrete date still unpinned; C7 added (F2C-18, F2C-19) |
| 4 | Remove standing human apply roles + break-glass runbook | Approved | After F2 exit; runbook written and dry-run first (F2C-22) |

### Decisions 5–17 (Amendment 7, 2026-08-31)

Recorded with the alternative not taken and the residual uncertainty, per §4. An entry
carrying only its outcome does not satisfy the envelope.

**Decision 5 — read-only state verification is a script in the repo, not a CI workflow and
not a deny-list change.** `scripts/state-readout.sh` performs read-only API calls and emits
one structured JSON artefact: Cloud Run service configs per service; IAM bindings for every
principal named in the pending plan's `setIamPolicy` calls; deployed BigQuery view DDL;
Pub/Sub subscription config including dead-letter policy and max delivery attempts; DLQ
undelivered depth; Artifact Registry tags for `collector` and `worker`; BigQuery row counts
by `synthetic` and by run id over an explicit partition window.
*Alternative not taken:* a `workflow_dispatch` job authenticating via WIF, for the run
number. Rejected because its premise was false — the deny-list carries no monitoring rule,
and every reading above was performed from Lane A on 2026-08-31 — and because the CI
identity's read grants are themselves unverified, so the workflow would add a new
unmeasured dependency to the critical path in order to solve a problem that does not exist.
Widening `.claude/settings.json` was also not taken, for the reason the proposal gave and
which survives: DoD 12 asserts nothing was loosened across F2.
*Residual uncertainty:* a local run carries a paste rather than a run number. F2C-08's
provenance clause already holds that an API read stays an API read regardless of who runs
it, so this weakens reproducibility rather than validity — the script is checked in so a
third party can re-run it. If a run number is later wanted, the same script wires into CI
unchanged.

**Decision 6 — the corpus carries a run-scoped identity.** Every span carries resource
attribute `synthetic=true` (Decision 2, unchanged) and `plumbline.e2e_run_id`, run-unique,
emitted as a resource attribute so it lands in the lossless `attributes` column. All
harness assertions scope to that value.
*Alternative not taken:* deleting rows between runs. Rejected — deletion in a
`require_partition_filter` table is awkward and is a mutation on the phase's only real data.
*Residual uncertainty:* the corpus accumulates. Nothing prunes it inside F2, and the table's
growth is bounded only by how often the harness runs.

**Decision 7 — the partition predicate is structural.** Every harness query goes through one
helper taking an explicit `(start_time_lower, start_time_upper)` window as a required
argument; no code path can issue a query without one. The window derives from the run's own
emission timestamps, never from `CURRENT_DATE()`.
*Alternative not taken:* a convention plus review. Rejected because `require_partition_filter`
rejecting a missing predicate is the weaker of the two invariants — a broad scan satisfies
the filter and still burns the query budget. The helper enforces both.
*Residual uncertainty:* the helper binds the harness only. Ad-hoc console queries remain
outside it.

**Decision 8 — stage 0 is view-definition provenance.** Before sending anything the harness
reads deployed view DDL from the API and compares it to the repo SQL; a mismatch aborts with
a message naming both.
*Alternative not taken:* trusting the apply. Rejected because a stale view fails the golden
diff with a normalization-shaped error that is really a deployment-shaped one, and this phase
has already spent four days on one misread failure (W2.16). Measured 2026-08-31, the cloud
view is still two-column — `PARTITION BY trace_id, span_id` — while the repo SQL is
three-column, so the mismatch this check exists for is present right now.
*Residual uncertainty:* the comparison is textual. A semantically equivalent reformatting by
the API would abort a run that should have proceeded.

**Decision 9 — two entry points, one tool.** `make e2e-cloud` runs the happy path;
`make e2e-cloud-drill` publishes the poison fixture and verifies DLQ depth and alarm. Both
ship in the same PR and both are merged before arming.
*Alternative not taken:* a single entry point. Rejected because the drill requires DLQ
drained to zero and a recorded separation from the F2C-08.2 channel test, neither of which
holds at first delivery; one entry point would fire the DoD 7b exam and the DoD 4 drill
together and weaken both.
*Residual uncertainty:* two entry points share one code path, so a regression in the shared
half shows up in whichever runs first.

**Decision 10 — the cloud target requires explicit arming.** The default target is the
emulator. Cloud execution requires `PLUMBLINE_E2E_TARGET=cloud` plus a run id on the command
line; without both the target exits non-zero and prints why.
*Alternative not taken:* relying on Amendment 6's written prohibition. Rejected because a
forbidden action guarded by a remembered rule is this project's named anti-pattern, and the
action here spends a once-only exam.
*Residual uncertainty:* the guard stops accident, not intent.

**Decision 11 — machine-readable stage output.** The harness writes a result JSON whose
`stage` field is one of `view_provenance`, `publish`, `push_auth`, `normalize`, `write`,
`query`, `complete`; on failure the field names the stage reached.
*Alternative not taken:* human-readable logs plus interpretation. Rejected because the
four-branch fault tree in `wave4-first-delivery.md` exists so that triage of the 7b exam is
not improvised under pressure; aligning output to the tree's branches makes the runbook
mechanically reachable.
*Residual uncertainty:* the stages are the ones known today. A failure between two of them
reports the earlier stage.

**Decision 12 — golden diff with a checked-in volatile-field allowlist.** Cloud-normalized
rows are diffed against the same corpus normalized locally. Excluded fields live in one
checked-in constant — at minimum `ingest_time`, and `api_key_id` only if the two paths
legitimately differ. Any field not on the list that differs is a failure.
*Alternative not taken:* inline exclusions at the comparison site. Rejected because an inline
exclusion is where a real difference gets waved through at 2am; a named list makes waving it
through require a commit.
*Residual uncertainty:* whether `api_key_id` legitimately differs is not yet measured. It is
decided at first cloud run, and the reason goes in the constant.

**Decision 13 — DoD 3's walling proof is a query.** Two assertions against `spans_deduped`
scoped to the run id: emitted span count equals distinct `(trace_id, span_id)` count, and the
count of rows with `synthetic` not true is zero.
*Alternative not taken:* the harness reporting that it set the flag. Rejected — that proves
what was sent, and DoD 3 is a claim about what landed.
*Residual uncertainty:* the second assertion scopes to the run id, so it proves this run wrote
no unflagged rows, not that the table contains none.

**Decision 14 — channel test and drill are separated by recorded timestamps, and by a marker
where one is available.** F2C-08.2's channel test executes first, its send timestamp recorded
from the command's own output; the drill follows by at least 30 minutes. If the channel
test's notification admits any distinguishing marker it carries one, and the marker rather
than the timing is the attribution. The executor records which of the two applied.
*Alternative not taken:* timing alone. Rejected because the drill's alert already carries
`plumbline_drill=f2-dod4`, and whether the channel test can carry anything comparable is worth
one check rather than one assumption.
*Residual uncertainty:* if no marker is available, attribution rests on a 30-minute gap and two
recorded timestamps. That is derivable, not identical.

**Decision 15 — C1's pinning is a closure gate.** The closure note cannot be completed while
C1 holds a ceiling instead of a date; the placeholder accepts a date, and `≤ 2026-09-28` is
not a valid value. **Recommended: 2026-09-21.** C3 opens no earlier than 2026-10-05 (#74); C2
is a live-fire immediately after the upgrade; a failed live-fire plus re-attach plus retry
needs roughly two working days. Pinning at the ceiling leaves seven days including a weekend
to absorb a failure; pinning a week inside leaves the same absorption budget plus a week of
slack before the ceiling is breached.
*Alternative not taken:* leaving the ceiling and reminding. Rejected because an unpinned
ceiling drifts silently, and this converts drift into a blocked closure.
*Residual uncertainty:* the date remains Lane C. This makes drift visible; it does not pick
the date, and F2 closure is now coupled to a Lane C action that has no scheduled session.

**Decision 16 — the two-day spend escape hatch is armed for the delivery window.** From
arming until the closure note, the state readout includes gross cost for the period, and any
spend > $0.00 on two consecutive days triggers the incident note `architecture.md` §7 already
requires.
*Alternative not taken:* relying on the kill-switch. Rejected because the kill-switch has been
fire-tested but has never seen an actual bill; the escape hatch exists for exactly this moment
and is currently a sentence in a document nobody is scheduled to read.
*Residual uncertainty:* billing reads are Lane C — `Bash(gcloud billing:*)` is denied and that
denial is correct. The daily figure therefore arrives by a human action, and the hatch is only
as timely as that action.

**Decision 17 — the Wave 4 pin is re-derived at dispatch, never carried.** F2C-05 re-derives
the pin from current `main` and confirms both images carry that tag; no SHA written in a
directive is confirmed as a pin.
*Alternative not taken:* updating `6a504b4` to `490beac4`. Rejected because it repeats the
defect one commit later — retention keeps the last two versions and deletes anything older
than a day, and Wave 4's wait is measured in days. Widening retention was rejected in A2.13
and is not reopened.
*Residual uncertainty:* re-deriving at dispatch assumes an image exists for current `main`.
If `deploy.yml` has not pushed one, F2C-05 fails on a missing image rather than a stale pin,
which is a better failure but still a failure.

### Remaining Lane C items

1. **Pin C1 to a date.** A ceiling is not a date. Amendment 7 Decision 15 makes this a
   closure gate: F2 cannot close over an unpinned ceiling, and `≤ 2026-09-28` is not a
   valid value for the placeholder. Recommended 2026-09-21, derived there.
2. **Schedule the Adjudicator ground-truth-labelability session.** It gates Freeze A,
   which gates F3, which gates C7, which gates the single calendar block C4 requires. It
   is a separate conversation and it is on the critical path to 2026-10-05 — not F2's
   critical path, the project's.
