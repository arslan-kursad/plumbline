# F2 — Completion note

**Phase:** F2, Minimal GCP Footprint · **Status:** *DRAFT SKELETON — not a closure claim*
**Date:** *(placeholder — filled at closure)* · **Spec:** [`F2-minimal-gcp-footprint.md`](F2-minimal-gcp-footprint.md)
**Directive:** [`F2-completion-directive.md`](F2-completion-directive.md) v1.7 (SHA recorded
in the decision log at commit)
**Decisions:** [`F2-decision-log.md`](F2-decision-log.md) — D1–D6, W0.\*–W3.8, A2.1–A2.13, W2.14–W2.20

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
| 1 | G1 — #33 closed, post-fix live-fire | *(placeholder)* | |
| 2 | G2 — #44 closed with ordering evidence | *(placeholder)* | |
| 3 | Constructed OTLP lands in cloud BigQuery through the views, every row `synthetic = true` | **satisfied** | [`f2-dod3-first-delivery.md`](../evidence/f2-dod3-first-delivery.md), 2026-09-01 — `spans_deduped` scoped to two runs: 13 rows each, `rows_seen = distinct_spans`, `unflagged = 0` |
| 4 | Poison reaches the cloud DLQ, alert fired, triage archived | **satisfied** | [`f2-dod4-drill.md`](../evidence/f2-dod4-drill.md), 2026-09-01 — poison published `05:23:14Z`, dead-lettered `05:25:02Z` after 5 attempts, depth 0→1, alert delivered. Archive digest matches the published payload byte for byte |
| 5 | Every resource Terraform-owned, final plan clean, zero out-of-path creations | *(placeholder — re-measure)* | |
| 6 | Cloud Run inside guardrails, guard shown to evaluate them | **satisfied** | [`f2-dod6-cloud-run-guardrails.md`](../evidence/f2-dod6-cloud-run-guardrails.md), 2026-08-31 — API read plus captured guard rejection, run `33390722393` |
| 7a | Push transport established | **satisfied** | Wave 3, run `32969025343` |
| 7b | Push transport exercised — a real Google-signed token accepted | **satisfied** | [`f2-dod3-first-delivery.md`](../evidence/f2-dod3-first-delivery.md) §1, 2026-09-01 — worker `POST /push - 204` after the `custom_audiences` fix. The first attempt failed at branch A ([`f2-dod7b-first-delivery.md`](../evidence/f2-dod7b-first-delivery.md)) |
| 8 | Verification B — a real notification reading `costAmount = 0.00` | *(placeholder)* | |
| 9 | Credit-lag procedure live with one data point | *(placeholder)* | |
| 10 | Period invoice fully credit-offset | *(placeholder)* | |
| 11 | Decision log complete | *(placeholder)* | |
| 12 | Gates A–H green, nothing loosened | *(placeholder — re-measure at closure)* | |
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
| C1 | Account upgrade **≤ 2026-09-28** | ceiling approved; **date not pinned** — Lane C |
| C2 | Kill-switch live fire re-run immediately after upgrade, before the window | *(placeholder)* |
| C3 | Window must not straddle 2026-10-05; earliest open 2026-10-05, earliest close 2026-10-19 | *(placeholder)* |
| C4 | The two windows are one block | binding |
| C5 | F3 sits between first delivery and the window | *(placeholder)* |
| C6 | The F4 window carries the human-initiated-session constraint — a staffing constraint | Lane C |
| C7 | F3 exit + three emitters ingest-ready **≤ 2026-10-04** | **blocked** — behind Freeze A and the Adjudicator ground-truth-labelability question, which has no scheduled session |

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
  authoring output.
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

- **Emulator results are not cloud results.** `dataset now holds: ['spans',
  'spans_deduped', 'spans_real']` with 13 rows per view is a **local emulator** result.
  Cloud `plumbline.spans` stands at 0 rows. No emulator result satisfies a DoD item
  that names the cloud.
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
- **Skipped CI jobs, named.** *(placeholder — list every required check satisfied by a
  path-filter skip during #82 and Wave 4. A skipped job is not a passing job.)*

## 6. CN3 — Wave 1 drift, root cause recorded

Not "unexplained". W1.8 identifies it as two sources where the API normalises a value
and the configuration insists on writing it back:

1. Monitoring lowercases the notification address, while the secret was written in
   uppercase. Fixed with `lower(var.alert_email)`.
2. `older_than = "0s"` is not persisted and was re-added on every plan run. Fixed with
   `older_than = "86400s"`.

Both named, both fixed, verified by `terraform plan -detailed-exitcode` returning 0
with no changes on 2026-08-30. *(Re-measure at closure per §7 criterion 2.)*

## 7. Numbers

*(placeholder — filled at closure.)*

## 8. Exit review

*(placeholder — C2-style review: this note, D2's scope statement, Verification B
evidence, a decision-log skim.)*
