# F2 — Completion note

**Phase:** F2, Minimal GCP Footprint · **Status:** *DRAFT SKELETON — not a closure claim*
**Date:** *(placeholder — filled at closure)* · **Spec:** [`F2-minimal-gcp-footprint.md`](F2-minimal-gcp-footprint.md)
**Directive:** [`F2-completion-directive.md`](F2-completion-directive.md) v1.7 (SHA recorded
in the decision log at commit)
**Decisions:** [`F2-decision-log.md`](F2-decision-log.md) — D1–D6, W0.\*, W1.\*, W2.\*, W3.1–W3.26,
A2.1–A2.13 · **Directive §9:** Decisions 1–4 (Amendment 4) and 5–17 (Amendment 7), each of the
latter carrying its alternative not taken and its residual uncertainty

> **This document is a skeleton authored ahead of the measurements it will carry**
> (directive F2C-10). Every line marked *(placeholder)* is unmeasured. It is committed
> in this state deliberately: a closure note written after the fact is written against
> a summary, and this phase has already produced three defects of exactly that shape.
>
> **Nothing here marks a DoD item satisfied.** Filling a placeholder means running the
> measurement, not deciding the measurement would have passed.

## 0. The rule this note is written under

**CN4 — provenance for status claims.** Any claim in this note that an item is open
must cite **where and when it was verified open**. Carrying a status forward from a
prior document is not verification. This phase produced one such error already: the
Wave 1 drift root cause was carried as "unexplained" out of a summary table into a
directive and then into a second directive, after W1.8 had explained and fixed it.

A hand-authored status table is a hand-authored fixture, and it fails the same way.

## 1. Definition of Done

| # | Item | Status | Measured where, and when |
| --- | --- | --- | --- |
| 1 | G1 — five facts, spec §7 item 1 as amended (Amendment 2) | **3 of 5; not closed** | [`f2-dod1-five-facts.md`](../evidence/f2-dod1-five-facts.md), 2026-09-01, fact by fact. **1.1** #33 closed `2026-08-21T20:35:09Z`. **1.2** live fire passed on Attempt 3, `billingEnabled: false` at the API, idempotent under redelivery. **1.3** archived in `kill-switch.md` §4, all three attempts; the console screenshot #33 asked for is a recorded deliberate omission. **1.4 open** — billing attached is a present-tense claim and went false five times after the item was recorded; current state unread by Lane A (`.claude/settings.json` denies `Bash(gcloud billing:*)`). **1.5 open** — repository side measured (`killswitch.tf:284` `INCLUDE_ALL_CREDITS`, Gate H green on run `33475352691`), live side unread, same denial. The earlier [re-derivation](../evidence/f2-dod-1-2-5-12-rederived.md) measured §3's ordering clause, which is not this item |
| 2 | G2 — #44 closed with ordering evidence | **satisfied** | [re-derived](../evidence/f2-dod-1-2-5-12-rederived.md), 2026-09-01 — `f7d6ca3` at `2026-08-21T19:37Z`, five days before the subscription that binds it; both obligations verified in current form |
| 3 | Constructed OTLP lands in cloud BigQuery through the views, every row `synthetic = true` | **satisfied** | [`f2-dod3-first-delivery.md`](../evidence/f2-dod3-first-delivery.md), 2026-09-01 — `spans_deduped` scoped to two runs: 13 rows each, `rows_seen = distinct_spans`, `unflagged = 0` |
| 4 | Poison reaches the cloud DLQ, alert fired, triage archived | **satisfied** | [`f2-dod4-drill.md`](../evidence/f2-dod4-drill.md), 2026-09-01 — poison published `05:23:14Z`, dead-lettered `05:25:02Z` after 5 attempts, depth 0→1, alert delivered. Archive digest matches the published payload byte for byte |
| 5 | Every resource Terraform-owned, final plan clean, zero out-of-path creations | **satisfied, with one stated exception** | [re-derived](../evidence/f2-dod-1-2-5-12-rederived.md), 2026-09-01 — `No changes` on run `33475352691`; every resource enumerated from the API. The Eventarc-created subscription is not Terraform-declared and is named as such |
| 6 | Cloud Run inside guardrails, guard shown to evaluate them | **satisfied** | [`f2-dod6-cloud-run-guardrails.md`](../evidence/f2-dod6-cloud-run-guardrails.md), 2026-08-31 — API read plus captured guard rejection, run `33390722393` |
| 7a | Push transport established | **satisfied** | Wave 3, run `32969025343` |
| 7b | Push transport exercised — a real Google-signed token accepted | **satisfied** | [`f2-dod3-first-delivery.md`](../evidence/f2-dod3-first-delivery.md) §1, 2026-09-01 — worker `POST /push - 204` after the `custom_audiences` fix. The first attempt failed at branch A ([`f2-dod7b-first-delivery.md`](../evidence/f2-dod7b-first-delivery.md)) |
| 8 | Verification B — a real notification reading `costAmount = 0.00` | *(placeholder)* | |
| 9 | Credit-lag procedure live with one data point | *(placeholder)* | |
| 10 | Period invoice fully credit-offset | *(placeholder)* | |
| 11 | Decision log complete | **satisfied** | F2C-20, 2026-09-01 — 73 entries across five series, `W3.1`–`W3.26` unbroken; directive §9 Decisions 5–17 checked mechanically to carry both an alternative not taken and a residual uncertainty. #47, #63, #91 and #102 closed against evidence |
| 12 | Gates A–H green, nothing loosened | **satisfied** | [re-derived](../evidence/f2-dod-1-2-5-12-rederived.md), 2026-09-01 — nine gate assertions green on run `33475352691`, all ten jobs run and none skipped; `invariant-gates.sh` unchanged since before #82, `.claude/settings.json` untouched all phase |
| 13 | **Verification C** | **open by design** | see §4; not a phase-exit item |

## 2. CN1 — the credit sentence

F2's $0.00 is **credit-offset**, not gross zero. Free Tier usage is credit-implemented
in GCP, so gross cost is non-zero during entirely free operation (ADR-0004 Amendment 4).

**F2's billing evidence does not establish the project's zero-cost claim.** Items 8, 9
and 10 establish that the period was fully credit-offset while a promotional trial
credit was active. That is a different sentence, and item 13 is the one that carries
the claim.

## 3. CN2 — the calendar block

**C4: Verification C's 14-day window and F4's continuous-ingest window are one calendar
block.** Both require post-credit operation with ingest running. Planned separately they
cost a month.

| # | Constraint | Status |
| --- | --- | --- |
| C1 | Account upgrade **≤ 2026-09-28** | **pinned: 2026-09-21** (Monday), Lane C decision 2026-09-01. Seven days of slack to the ceiling; the two-working-day retry window for a failed C2 live-fire falls Tue–Wed with no weekend in it |
| C2 | Kill-switch live fire re-run immediately after upgrade, before the window | *(placeholder)* |
| C3 | Window must not straddle 2026-10-05; earliest open 2026-10-05, earliest close 2026-10-19 | *(placeholder)* |
| C4 | The two windows are one block | binding |
| C5 | F3 sits between first delivery and the window | *(placeholder)* |
| C6 | The F4 window carries the human-initiated-session constraint — a staffing constraint | Lane C |
| C7 | F3 exit + three emitters ingest-ready **≤ 2026-10-04** | **blocked, and now dated** — behind Freeze A and the Adjudicator ground-truth-labelability question. Session scheduled **2026-09-02, 10:00–13:00 Europe/Istanbul**, which leaves 32 days to C7 |

## 4. Dated open obligations, carried forward

These are not F2 failures. They are items F2 cannot close, recorded with dates rather
than left to memory.

- **DoD 13 / Verification C** — gross $0.00 after credit exhaustion (13a), the
  kill-switch live fire re-run post-upgrade against a real charge for the first time
  (13b), and both holding across a 14-day window with ingest running (13c). Owner:
  Lane C. **F2 is not re-opened by it**, and the zero-cost claim is not published
  until it closes.
- **C1–C7** — §3.
- **#61** — open until F2C-12. #82 merged the corrected view definitions on
  2026-08-31; it did not deploy them. The cloud views are still the two-column form,
  and #82's own plan says so: `spans_deduped will be updated in-place`. #61 closes on
  a partition-filtered read succeeding against the **cloud** views. A merged fix is not
  a deployed one.
- **#68 / ADR-0008** — left at `Proposed`. A status flip is a review output, not an
  authoring output. **Review scheduled 2026-09-03**, its own session, thirty minutes, and
  deliberately not inside Freeze A on 09-02: the decision needs no evaluation-plan context,
  and the freeze session has none to spare. The three options and their costs are in #68.
  Recorded here because this is unbudgeted work on the critical path to C7 — option 1
  (h2c multiplexing) is a data-plane change plus a deploy and a verification pass, taken
  out of the 32 days before 2026-10-04.
- **#91 / F2C-23** — **fixed 2026-08-31.** The seeder strips SQL comments before POSTing
  a statement, so the stand-in no longer reads prose as code, and the circumlocution in
  `002_spans_deduped.sql` reverted to the plain wording F2C-02 asks for. The divergence it
  worked around is not fixed and is not ours to fix — see the bullet above and
  `local-dev.md`. Carried here only until #91 is closed at F2C-10.
- **`/healthz` interception** — recorded as an unexplained known-unknown, **no date
  attached**. On the collector the exact path `/healthz` is intercepted at the Cloud
  Run layer and never reaches the container, while `/health`, `/healthz/`, `/` and
  `/v1/traces` all do. Cause unknown; recorded rather than closed.
- **F4's uptime-check path — open, and inherited by F4 as a question rather than a
  binding.** W3C.7 asked that the check bind `/health`. Measured 2026-08-26, `/health`
  reaches the container and returns Go's `404 page not found`: the collector registers
  `/healthz` and `/v1/traces` and nothing else, so a check bound there would be green only
  if configured to accept a 404, at which point it asserts that Google's edge is up rather
  than that the collector is. `F2-directive-w3c-consolidation.md` §5 recorded the binding
  as **undecided rather than written down wrong**, and its three options — bind
  `/v1/traces` and accept the `405`, register a second health route at a path the edge does
  not intercept, or establish why `/healthz` is intercepted — are in
  [`collector-endpoints.md`](../runbooks/collector-endpoints.md). Each is a collector change
  or an architecture decision. F4 inherits the open question; it does not inherit a path.

## 5. What is not true, stated plainly

*(placeholder — filled at closure. The items below are already known and are not the
complete list.)*

- **Emulator results are not cloud results, and now both have data.** `dataset now holds:
  ['spans', 'spans_deduped', 'spans_real']` with 13 rows per view is a **local emulator**
  result. Cloud `plumbline.spans` held 0 rows when this line was written; measured
  2026-09-01 it holds **52**, with 26 through `spans_deduped` and 0 through `spans_real`.
  The two agreeing is not the two being equivalent: no emulator result satisfies a DoD item
  that names the cloud, and the divergence below is why.
- **A narrowing predicate that matches nothing reads exactly like a healthy system, and
  this phase produced three.** The run-scoped JSON path addressed the top level while the
  normalizer nests resource attributes under `resource` (W3.11). The harness derived its
  partition window from the clock while the corpus is static at 2026-08-19 (W3.18). The
  state readout's default window did the same (W3.22). **In each case every assertion
  passed over an empty set** — rows equal distinct spans equal zero, unflagged zero, leaked
  zero. A perfect result and no data. Two were caught by querying by hand; none was caught
  by the tool reporting anything. The guards now assert that their predicates *select*
  something, and an empty reading cross-checks the table's own row count and says which case
  it is. **Carried to F3 as a design rule rather than three fixes:** any reading that can
  come back empty must say why it is empty.
- **The emulator/production divergence is real and only half-measured.** W2.16 found
  that a comment suppresses view creation in `goccy/bigquery-emulator` 0.8.1 while real
  BigQuery validates the same text (W2.17, dry-run). The observed direction is
  **false-red**: CI fails on SQL production accepts. **The unobserved direction is the
  one that matters — CI green on SQL production would reject** — and it is unmeasured.
  Architecture §8 rests the local-first model on emulator fidelity. Carried to F3.
- **The Lane A deny-list is enumerated, not principled — and its previous description
  here was wrong.** This note said it "denies reading monitoring policies". It does not:
  `.claude/settings.json` carries no monitoring rule. What it denies is
  `Bash(gcloud alpha:*)`, an entire command surface regardless of whether a call reads or
  writes, and F2C-08.1 was blocked because the command reached for was
  `gcloud alpha monitoring policies list`. Measured 2026-08-31 from Lane A, the GA surface
  is permitted and returns the same reading: `gcloud monitoring policies list` returned the
  `traces-dlq` policy enabled. The shape defect is real and is this — denial by command
  surface rather than by effect — and it is deliberately not fixed during F2, because
  fixing it means editing `.claude/settings.json` while DoD 12 asserts nothing was
  loosened. Shaped rule goes to F3 entry. Corrected under Amendment 7; the earlier wording
  was carried forward without being read against the file, which is the CN4 error class
  this note exists to refuse.
- **Skipped CI jobs, named.** Measured 2026-09-01 across the **38 pull requests merged
  from #82 onward**, reading each PR's own run rather than the push run on `main`:

  | Required check | Skipped | Ran |
  | --- | ---: | ---: |
  | `changed paths` | 0 | 38 |
  | `invariant gates` | 0 | 38 |
  | `ci complete` | 0 | 38 |
  | `local end-to-end` | 29 | 9 |
  | `terraform plan (wif)` | 32 | 6 |
  | `terraform static checks` | 32 | 6 |
  | `images (distroless)` | 33 | 5 |
  | `worker and analytics (.net)` | 34 | 4 |
  | `collector (go)` | 37 | 1 |
  | **`kill-switch function (go)`** | **38** | **0** |

  **`kill-switch function (go)` never ran once.** Thirty-eight required-check green ticks,
  every one of them a path-filter skip, on the test suite for the component the entire
  zero-cost claim rests on. The filters are not wrong — nobody touched that code — but a
  green tick that carried no information thirty-eight times is exactly what *"a skipped job
  is not a passing job"* is about, and DoD 12's "gates green" would otherwise be read as
  covering it.

  **The gap is closed by measurement rather than by argument.** CI run
  [`33477177883`](https://github.com/arslan-kursad/plumbline/actions/runs/33477177883) —
  `workflow_dispatch` on `main` at `ec39569`, which is this note's own commit base — ran
  **all ten jobs with zero skips and all ten succeeded.** Every check listed above has
  therefore passed against the closing tree, once, on the record.

  The habit worth keeping past F2: a path filter makes a required check advisory, and
  nothing in the pull-request view distinguishes *passed* from *did not run*. A dispatched
  full run before a phase closes costs one command.
- **An identifier is not an identity — it proves neither sameness nor difference, and it
  does not stop pointing when its referent is replaced.** Three instances in this phase,
  one shape:

  - **`#68`** — one object with two descriptions, read as two objects. The issue has a
    single meaning in this repository and every reference agrees with it; a design-layer
    document paraphrased it twice, and the two paraphrases were taken for two separate
    obligations. A carried item was invented out of a shared number.
  - **`G1`** — one label over two different claims, read as one claim. Spec §3's gate row
    asserts an ordering (*"No application service deploys before G1."*); spec §7 item 1
    asserts five completion facts and contains no ordering clause. The closure
    re-derivation measured §3's sentence and recorded §7's item as met. Both texts are
    real, and neither is a paraphrase of the other. Measured item by item in
    [`f2-dod1-five-facts.md`](../evidence/f2-dod1-five-facts.md): of the five facts, three
    hold, one is a state claim written as an event claim and went false five times after
    it was recorded, and one is below.
  - **"the corrected credit filter"** — one phrase, two objects, four days apart. Written
    `2026-08-21`, it could only mean ADR-0004 Amendment 1's enumerated `FREE_TIER` filter.
    That filter was falsified in production on `2026-08-22` and superseded by Amendment 4
    on `2026-08-25`. The phrase in §7 item 1 has never been edited, so read with its
    authoring referent it now asserts as a *completion condition* the exact configuration
    **Gate H fails the build for containing**.

  The rules this phase already wrote — separate two events by identity rather than by
  co-existence, and rather than by time — catch none of these, because in all three the
  identifier was present and was the thing that misled.

  **The part worth not softening:** two of the three surfaced inside remediation artefacts.
  `f2-dod-1-2-5-12-rederived.md` exists to stop a status being carried forward, and it
  carried one across sections instead of across documents. A control failing in the shape
  it was built to prevent is worth more than a control simply failing.

  **Carried to F3 as a design rule:** a normative sentence names its referent by version or
  by location, never by a bare label — `ADR-0004 Amendment 4's credit filter`, not "the
  corrected credit filter"; `spec §7 item 1`, not `G1`. Where a label is load-bearing and
  shared, the document says which of its senses it means.

## 6. CN3 — Wave 1 drift, root cause recorded

Not "unexplained". W1.8 identifies it as two sources where the API normalises a value
and the configuration insists on writing it back:

1. Monitoring lowercases the notification address, while the secret was written in
   uppercase. Fixed with `lower(var.alert_email)`.
2. `older_than = "0s"` is not persisted and was re-added on every plan run. Fixed with
   `older_than = "86400s"`.

Both named, both fixed, verified by `terraform plan -detailed-exitcode` returning 0
with no changes on 2026-08-30. **Re-measured 2026-09-01** per §7 criterion 2: CI run
[`33475352691`](https://github.com/arslan-kursad/plumbline/actions/runs/33475352691) reports
`No changes. Your infrastructure matches the configuration.` The drift has not returned
across Wave 4's apply, the `custom_audiences` apply, or the image-pin bump.

## 7. Numbers

Measured 2026-09-01. **The billing row is deliberately absent, not forgotten** — DoD 8, 9
and 10 are evaluated against a period that has not closed, and a number written here before
then would be the substitution this note exists to refuse.

| | |
| --- | --- |
| Rows in cloud `plumbline.spans` | 52 |
| Through `spans_deduped` | 26 |
| Through `spans_real` | **0** — the walling holds |
| Deliveries | 5 runs: one refused at branch A, three of `w4-third-delivery`, one of `w4-second-delivery` |
| Dead-lettered messages | 8 — 7 from the failed first delivery, 1 from the drill |
| Decision-log entries | 78, across five series |
| Evidence documents | 16 |
| Runbooks | 12 |
| Pull requests merged from #82 | 43 |
| Invariant gates | 9, all green with none skipped on run `33477177883` |
| Harness guard tests | 63 |
| Seeder tests | 11 |
| Normalization / worker tests | 114 |
| API keys issued during Wave 4 | 4 — 3 revoked, 1 pre-existing and untouched |
| Period cost | *(not measurable until the period closes — see the note above)* |

## 8. Exit review

*(placeholder — C2-style review: this note, D2's scope statement, Verification B
evidence, a decision-log skim.)*
