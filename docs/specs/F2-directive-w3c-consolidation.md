# F2 — Directive W3.C: Post-Wave-3 Consolidation & Wave 4 Pre-Arming

**Version:** 0.1 · **Status:** Handoff (single approval artifact) · **Date:** 2026-08-26
**Lane:** **A only** — autonomous repo work, self-merge after green CI + all gates.

Filed under `docs/specs/` beside
[`F2-directive-kill-switch-amendment-2.md`](F2-directive-kill-switch-amendment-2.md),
which is where this repository keeps directives. The handoff proposed
`docs/directives/`; creating it would have been a second convention for one file,
which §1 of the directive itself forbids. The other path adjustments are recorded
in the execution note at the end.

---

## 1. Purpose

Wave 3 applied cleanly (run `32969025343`, `4 added, 1 changed`, fingerprint matched,
post-apply `No changes`). The `traces` → `ingestion-worker` OIDC push subscription is
live and verified from the API. Wave 4 arming is blocked on a human decision (#82 / D4)
and is **not** in scope here.

This directive consolidates what Wave 3 exposed and prepares Wave 4 so that its
execution is a rehearsed procedure rather than an improvised one. Three of its items
close defect *classes*, not instances:

- an empty plan can currently reach the Lane B approval gate;
- plan-guard fixtures are hand-authored and therefore under-specified against any check
  written after them;
- the apply identity holds grants broader than the waves that motivated them, and Wave
  3's clean apply is explained by that breadth.

## 2. Out of scope

- Any `terraform apply`, any Lane B action, any Wave 4 arming.
- Publishing any message to `traces` or any other topic. The worker's OIDC validator
  must first see a real Google-signed token as **Wave 4's first delivery**, inside the
  gated path, not as a side effect of this work.
- Narrowing or removing any IAM grant (requires an apply; ledger only here).
- Resolving #82 / D4, or flipping any ADR status.
- Changing what any existing plan guard or CI gate **asserts**. Fixture provenance work
  must not alter a single assertion.
- Any edit to `docs/eval-plan.md`.
- Normative F2 DoD text beyond item 7. Verification C, the promotional-credit sentence,
  and the Verification-C ∥ F4 calendar-block sentence are authored in the design layer
  and arrive in a separate directive.

## 3. Work items

| Item | Subject | Landed as |
| --- | --- | --- |
| W3C.1 | `deploy.yml` refuses an empty plan; the plan's provenance is stamped above the gate | `scripts/ci/plan-nonempty-guard.sh`, `plan_nonempty.py`, `deploy.yml` |
| W3C.2 | Fixture provenance: rule, tool, manifest, gate | `scripts/ci/scrub_plan.py`, `fixture_provenance.py`, `testdata/README.md`, `testdata/fixtures.manifest.json` |
| W3C.3 | #63 reconciled; the same-commit rule written down | issue #63, `.github/workflows/README.md` |
| W3C.4 | F2 DoD item 7 split into 7a/7b | `F2-minimal-gcp-footprint.md` §7 |
| W3C.5 | Wave 4 first-delivery and dead-letter triage runbook | `docs/runbooks/wave4-first-delivery.md` |
| W3C.6 | Apply-identity permission ledger | `docs/runbooks/apply-identity-ledger.md` |
| W3C.7 | `/healthz` recorded as unexplained; F4's uptime check bound | `docs/runbooks/collector-endpoints.md` |
| W3C.8 | F3 entry note: the guards will deny `analytics-api` by design | architecture §7 (v0.12) |

## 4. Acceptance criteria

1. `deploy.yml` fails on a `no-op`-only plan and passes on a real non-empty plan; the
   pre-gate job summary carries ref, SHA, and the plan's change counts.
2. `scrub_plan.py` exists, is idempotent, removes no keys, and is the documented sole
   path from captured plan to fixture; the fixture rule is written into the repo.
3. `fixtures.manifest.json` covers every fixture with honest provenance; the CI gate
   rejects a new or modified fixture lacking `provenance: captured` and a same-commit
   manifest entry.
4. No guard assertion changed anywhere in this directive's diff.
5. #63 reflects Wave 2's applied state with evidence; the same-commit reconciliation rule
   is written down.
6. F2 DoD item 7 replaced by 7a/7b, with the deliberate-non-publication note.
7. `wave4-first-delivery.md` exists with pre-flight (both DLQ grants named), the
   four-branch decision tree, success signature, base-table-only verification including
   the dedup premise check, and DLQ triage.
8. `apply-identity-ledger.md` exists with the seed rows and the finding stated as an
   argument for narrowing.
9. `/healthz` recorded as unexplained; F4 uptime check binding decided with rationale.
10. F3 entry note present.
11. Nothing published to any topic. No apply. No ADR status flip.

## 5. Execution note — where this deviated, and why

Recorded here rather than in a pull request description, because a deviation that lives
only in a merged PR body is a deviation nobody can find later.

### Paths adjusted to existing convention

The directive named four paths that do not exist in this repository. §1 forbids
inventing a second convention, so each was placed where its neighbours already live:

| Directive | Landed | Reason |
| --- | --- | --- |
| `docs/directives/F2-W3C-consolidation.md` | `docs/specs/F2-directive-w3c-consolidation.md` | The only existing directive is `docs/specs/F2-directive-kill-switch-amendment-2.md` |
| `tools/scrub_plan.py` | `scripts/ci/scrub_plan.py` | No `tools/` exists; every guard and its self-test lives in `scripts/ci/`. W1.7 already declined to create `tools/` for `keyctl` |
| `infra/terraform/testdata/README.md` | `scripts/ci/testdata/README.md` | The fixtures are there |
| "the wave runbook" (W3C.3) | `.github/workflows/README.md`, `deploy.yml` section | No wave runbook exists; the arming procedure is documented with the workflow that performs it |
| "the collector runbook" (W3C.7) | new `docs/runbooks/collector-endpoints.md` | No collector runbook existed. Named for its scope rather than `collector.md`, which would imply coverage it does not have |
| "F3 entry conditions" (W3C.8) | architecture §7 | No F3 spec exists yet. §7 is where both guards are described and where an F3 author adding a resource type is already reading |

### Two premises that did not hold

**`docs/adr/ADR-0007-canonical-dedup-views.md` does not exist.** §3 lists it as required
reading. Architecture §10 records ADR-0007 as *reserved — not written*; the file is
created by #82, which is unmerged and is the maintainer's decision (D4). The premise
check W3C.5 asks for is nonetheless well defined and was written from the sources that
do exist — #61, #82's measurements, architecture §4.1 and §3.3 — and the runbook states
the ADR's actual status rather than citing it as an accepted record.

**The truncation-vs-rounding question is not open.** §7 lists it as carried over from a
prior session. #82 settled it against the code: `Timestamps.FromUnixNanos` truncates by
integer division on a `ulong`, its remarks already say *"dropped, not rounded"*, there is
no `Math.Round` on the path, and the golden test pinning it was proven to fire on a
one-microsecond boundary. It remains a Wave 4 *correctness dependency* through #82's
merge, which is what the blocked table should say.

### One instruction that measurement contradicted

W3C.7 asks that F4's uptime check bind `/health`. Measured against the deployed
collector on 2026-08-26, `/health` reaches the container and returns Go's
`404 page not found`: the collector registers exactly two routes, `/healthz` and
`/v1/traces`, and nothing at `/health`. Binding an uptime check there would monitor a
404 — green only if configured to accept 404, at which point it asserts that Google's
edge is up rather than that the collector is.

The runbook records the measurement and lays out the three options — bind `/v1/traces`
and accept its `405`, register a second health route at a path the edge does not
intercept, or establish why `/healthz` is intercepted — without choosing. Each is a
collector change or an architecture decision, and both are outside this directive's
scope. **The binding is therefore recorded as undecided rather than written down wrong.**

## 6. Blocked / not carried by this directive

| Item | Owner | Note |
|---|---|---|
| #82 merge, D4 | Human | Wave 4 arming depends on it; it also files ADR-0007 |
| F2 DoD: Verification C, credit sentence, Verification C ∥ F4 calendar block | Design layer | Separate directive; not composed here |
| Standing apply-role removal, break-glass runbook | Blocked on the ledger + an apply | The ledger is the input, not the action |
| Wave 1 drift root cause | Open | Still unexplained beyond "the second apply was clean" |
| F4 uptime-check path | Open | See §5; `/health` is not available as specified |
