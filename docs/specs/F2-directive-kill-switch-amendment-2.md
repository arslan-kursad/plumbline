# F2 Directive — Kill-switch Amendment 2 (#71)

**Version:** 1.0 · **Date:** 2026-08-25 · **Executor:** Claude Code (Lane A) + human (Lanes B, C)
**Governing decision:** ADR-0004 Amendment 2 (text supplied with this directive, verbatim)
**Branch:** `fix/kill-switch-amendment-2` · **PR title:** `fix(infra): kill-switch trigger on net-of-all-credits with epsilon threshold (#71)`
**Repo target:** `docs/specs/F2-directive-kill-switch-amendment-2.md`

---

## 1. Purpose

Implement ADR-0004 Amendment 2 so billing can be safely re-attached and Wave 2 armed.
Billing is currently detached (false positive, 2026-08-25 17:11). Nothing in Wave 2
proceeds until the verification in §6 passes.

## 2. Out of scope

- Any Wave 2 Cloud Run apply (Lane B, separate arming).
- #61 canonical views (ADR-0007, separate directive).
- F2 spec DoD amendment for #74 (separate artifact).
- Billing account upgrade (Lane C, human decision, not before October).
- `docs/eval-plan.md` — do not open, do not touch.
- Flipping the status of ADR-0004 Amendment 2. It is authored as `Proposed`; the
  flip is a review output on merge.

## 3. Context files (read before starting)

- `docs/adr/ADR-0004-zero-cost-guardrails.md` — Amendment 1 (what is being superseded).
- `docs/runbooks/kill-switch.md` — Wave 0 live-fire procedure and synthetic message
  format; re-attach procedure.
- `infra/terraform/` — existing `google_billing_budget`, `billing-alerts` topic,
  function resources, plan-guard script.
- Function source (kill-switch) — current `costAmount` parsing and detach path.
- `docs/architecture.md` §7 — cost guardrails table.

## 4. Work items

### W1 — Terraform: kill-switch budget filter
- Kill-switch `google_billing_budget`: set
  `budget_filter.credit_types_treatment = "INCLUDE_ALL_CREDITS"`; remove the
  `credit_types` list entirely.
- New variable `detach_threshold` (number, default `5.00`, description: "Net cost in
  billing-account currency at or above which the function detaches billing").
  Passed to the function as env var `DETACH_THRESHOLD`.
- No other change to this budget. Its Pub/Sub binding to `billing-alerts` stays.

### W2 — Terraform: gross-cost alert budget
- New `google_billing_budget` named `gross-cost-alert`:
  - `budget_filter.credit_types_treatment = "EXCLUDE_ALL_CREDITS"`, same project scope.
  - `amount.specified_amount` = variable `gross_alert_threshold` (number, default
    `100.00`), `currency_code` = variable `billing_currency` (default `"TRY"`; must
    equal the billing account currency or the API rejects it).
  - `threshold_rules`: 50% and 100%, `CURRENT_SPEND`.
  - `all_updates_rule`: **no `pubsub_topic`**, `disable_default_iam_recipients = false`
    (email to billing IAM recipients). No monitoring channel, no function.
- Plan-guard: add an assertion that exactly one `google_billing_budget` in the plan
  references the `billing-alerts` topic. Express it against the planned resource
  attribute (`all_updates_rule.pubsub_topic`), not against resource names.

### W3 — Function: epsilon threshold
- Read `DETACH_THRESHOLD` at startup; fail closed at startup if missing or
  non-numeric (log FATAL, exit) — never default silently.
- Decision rule: detach iff `costAmount >= DETACH_THRESHOLD`. Below threshold: log
  `WARN spend reported below detach threshold; no action` with `cost`, `currency`,
  `threshold`, `interval_start`.
- `currencyCode` logged on every decision. `alertThresholdExceeded` remains ignored.
- Isolate the decision into a pure function (input: cost, threshold → output:
  detach bool) and unit-test it: below → false, equal → true, above → true,
  negative/NaN cost → false with error log.

### W4 — Docs
- Append Amendment 2 to `docs/adr/ADR-0004-zero-cost-guardrails.md` verbatim from
  the supplied text. Status line stays `Proposed`.
- `docs/runbooks/kill-switch.md`: add section "Credit lag and promotional period"
  (D4 inertness statement; what a below-threshold WARN means; when to re-attach),
  the two-message live-fire procedure from §6, and evidence placeholders for it.
- `docs/architecture.md` §7: update the kill-switch row to cite Amendment 2; add a
  row `Runaway detection under promotional credit → gross-cost alert budget,
  notification-only (Terraform)`.
- Decision log: entries `A2.1`–`A2.n` for every autonomous choice (variable names,
  threshold rule percentages, log field names, plan-guard implementation). No
  conversational checkpoints.

## 5. Acceptance criteria (Lane A — self-merge after all pass)

1. All existing CI jobs and Gates A–G green; no gate relaxed.
2. Plan-guard passes on the new plan and **fails** on a fixture plan containing a
   second budget bound to `billing-alerts` (add that fixture to the guard's tests).
3. Function unit tests per W3 pass; `DETACH_THRESHOLD` missing → startup failure
   test exists.
4. `terraform plan` shows exactly: one modified budget (filter + variable), one new
   budget, function env change. Nothing else.
5. Zero occurrences of `credit_types` and `FREE_TIER` under `infra/terraform/`
   (grep gate, pattern written so it cannot match itself).
6. Amendment 2 appended, status `Proposed`; runbook and architecture §7 updated.
7. Decision log complete; PR body links this directive and #71.

## 6. Verification (Lanes B and C — after merge, before Wave 2 arming)

Human-armed apply of this change is **Wave 1.5** in the GitHub Environment; it
precedes and is independent of Wave 2.

1. **Lane B:** arm and apply Wave 1.5.
2. **Lane B:** publish synthetic notification with `costAmount = detach_threshold −
   0.01` (same message format as Wave 0) → expected: WARN, no detach. Billing stays
   as is (currently detached — state must not change).
3. **Lane C:** re-attach billing per runbook.
4. **Lane B:** publish `costAmount = detach_threshold` → expected: detach within one
   function invocation. **Lane C** confirms on the billing page.
5. **Lane C:** re-attach again. Observe two consecutive real budget notification
   cycles: function logs show WARN-below-threshold (or no spend), no detach.
6. Archive evidence (logs of steps 2, 4, 5; billing page state) under
   `docs/runbooks/kill-switch.md`. Close #71 with a link to the evidence.

Only after step 6: Wave 2 may be armed.

## 7. Test expectations

- Unit: decision function (W3), startup guard (W3), plan-guard positive and negative
  fixtures (W2).
- Live-fire: §6 steps 2 and 4 are the test; step 5 is the false-positive regression
  check. All three are evidence-archived, none is optional.
- No test asserts trivialities to fake coverage.

## 8. Human-only checklist (Lane C, in order)

1. Revoke `adjudicator-prod` API key (plaintext exposed in chat). Do this before
   anything else; it depends on nothing.
2. Review PR; flip Amendment 2 to `Accepted` on merge.
3. Arm Wave 1.5; execute §6 with Claude Code assisting on Lane B steps only.
4. Do not upgrade the billing account. That decision is separate and gated on #74.

---

## Filing note (added on execution, 2026-08-25)

Three departures from this directive's literal text, each forced and each recorded
rather than absorbed:

1. **The amendment is filed as Amendment 4, not Amendment 2.** Amendment 2 already
   exists in `ADR-0004-zero-cost-guardrails-kill-switch.md` — the 2026-08-21 entry
   on the detach permission model — and `killswitch.tf` and `wif.tf` both cite it by
   number. Every code and configuration reference was written as Amendment 4 to match.
2. **The gross-cost budget has no `all_updates_rule` block.** The directive asked for
   the block carrying `disable_default_iam_recipients = false`. The provider refuses
   it: `all_updates_rule` requires either `pubsub_topic` or
   `monitoring_notification_channels`, so the block cannot exist without giving this
   budget one of the two programmatic paths D3 forbids it. Omitting it yields the API
   default — threshold notifications emailed to billing administrators — which is what
   D3 specifies, and it notifies on the threshold rules rather than on every cost
   update.
3. **Two unverified claims were dropped from the ADR text and its date corrected.**
   The credit's API type string and a citation to "the billing export" could not be
   checked: the credit was read from the console as a one-time trial credit applied at
   net pricing, and this project has no BigQuery billing export. The observation date
   is 2026-08-22 per the function logs, not 2026-08-25. D1 depends on neither claim.

The directive's §5 acceptance criterion 4 — `terraform plan` shows exactly one
modified budget, one new budget and the function env change — **could not be executed
before merge**: billing is detached, so the plan cannot read state from the project's
GCS bucket. It is verified on the Wave 1.5 plan instead, which is the first plan that
can run.

**Sequencing wrinkle in §6, worth knowing before arming.** Step 1 applies Wave 1.5,
and an apply needs billing attached — but step 3 is where billing is re-attached, and
step 2 assumes it is still detached. The workable order is: drop the stale
notification backlog, re-attach, apply Wave 1.5 promptly, then run steps 2, 4 and 5.
The window between re-attach and apply is one notification interval, and during it
the old `> 0` rule is still live.
