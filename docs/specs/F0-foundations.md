# F0 — Foundations: Work Package Spec

**Version:** 0.6 · **Status:** Proposed (awaiting sign-off) · **Date:** 2026-08-19
**Phase budget:** ~8 h · **Executor:** Claude Code (implementation) + human (billing/manual steps)
**Repo target:** `docs/specs/F0-foundations.md` (replaces v0.1 in place)

---

## 0. Project constants (RESOLVED)

### 0.1 Naming

Project name: **`plumbline`** (decided 2026-08-18, human sign-off). All derived names
follow from it and are fixed here:

- Repository: `arslan-kursad/plumbline`
- Go module: `github.com/arslan-kursad/plumbline/collector`
- .NET solutions: `Plumbline.Worker`, `Plumbline.Analytics`
- Container images: `collector`, `ingestion-worker`, `analytics-api` under the
  `plumbline` Artifact Registry repo
- BigQuery dataset: `plumbline` (replaces the pre-decision working name; underscores
  unnecessary, single word is a valid dataset ID)

The pre-decision working name must not appear anywhere in the repository, in any
casing or separator variant. Enforcement: W1.1 grep, zero occurrences.

### 0.2 Repository visibility: **public** (decided 2026-08-18)

The repository is public from F0 onward, not flipped at F5.

Rationale:
- GitHub Pages is available on public repositories under GitHub Free; publishing Pages
  from a private repository requires a paid plan. The Trace Waterfall SPA
  (architecture §2.7, §3.5) depends on Pages, so a private repository would force either
  a paid plan — violating the "no paid SaaS anywhere in the loop" invariant — or an
  architecture change discovered at F4.
- GitHub Actions minutes are unmetered for public repositories and capped on Free for
  private ones. F1–F3 run Go + two .NET + Terraform jobs on every PR.
- The project's stated positioning is a live case study. A repository opened only after
  completion discards the visible-process value that is part of the deliverable.

Consequences, all handled in W1.1 and W6:
- The visibility flip happens **before** W6 begins, so WIF and CI are validated in their
  final security posture rather than a temporary one.
- WIF provider attribute conditions and fork-PR workflow posture become explicit
  acceptance criteria (W6), not implementation detail.
- Branch protection on `main` is enabled (free for public repositories): PR required,
  force-push denied, status checks required once W6 is green.

### 0.3 License: **Apache-2.0** (decided 2026-08-18)

Replaces the MIT license committed in W1. The target ecosystem (OpenTelemetry / CNCF)
standardizes on Apache-2.0; the explicit patent grant removes friction for corporate
readers of a reference implementation. Changing this is free while the project has a
single author and becomes expensive afterward.

- `LICENSE` carries the standard Apache-2.0 text with the appendix boilerplate
  completed — year and copyright owner — which is what the GitHub license template
  produces. No `NOTICE` file in v0.1: there are no third-party attributions to carry.
- No per-file license headers in v0.1 (noise for a solo repository). Revisit only if
  external contributors appear; that would be a spec change, not a silent addition.
- `README.md` license section and any package metadata updated to match.

---

## 1. Purpose

Establish the project skeleton and the zero-cost safety envelope **before any pipeline
code exists**: repository scaffold with Claude Code governance files, the design corpus
imported as the repository's source of truth, ADR rationale write-ups, a pre-registered
evaluation plan draft, a GCP project whose billing kill-switch has been **live-fired**,
a Terraform skeleton, and a green CI pipeline authenticated via Workload Identity
Federation (no exported SA keys).

## 2. Out of scope

- Any collector / worker / analytics / eval implementation code (F1+).
- Terraform for Pub/Sub, BigQuery, Firestore, Cloud Run application services (F2).
  F0 Terraform covers only: state backend, provider pinning, kill-switch resources,
  project-level quota/guardrail settings.
- Freezing `eval-plan.md` (draft in F0; Freeze A is the F1 entry gate, Freeze B is at F3
  — see W3).
- Dashboards, SPA, load generator (F4).
- A deploy-capable CI identity. F0 CI authenticates read-only (build, validate, plan).
  The deploy service account and its branch-scoped binding land in F2; only the binding
  *pattern* is documented here.

## 3. Context files (read before starting)

- `docs/architecture.md` — §7 (cost guardrails), §6.1 (WIF row), §8 (deployment).
- `docs/project-brief.md` — Phases (F0 DoD), Zero-cost invariants.
- ADR-0001 (Accepted) — scope constraint on all future work.

Until W1.1 merges, these files exist only as external snapshots. **W2 must not start
before W1.1 is merged**: ADR-0002..0005 cite architecture sections by number, and citing
a document that is not in the repository produces dangling references.

## 4. Work items

### W1 — Repository scaffold
Monorepo layout:

```
/collector/            # Go module (empty main + README stub)
/worker/               # .NET 8 (empty solution + project stubs)
/analytics/            # .NET 8 (empty solution + project stubs)
/normalization/mappings/v1.41/   # placeholder README, no YAML yet (F1)
/infra/terraform/      # W5
/docs/                 # architecture.md, project-brief.md, adr/, specs/, runbooks/, eval-plan.md
/scripts/ci/           # invariant gate scripts (W6)
/.github/workflows/    # W6
CLAUDE.md              # advisory contract for Claude Code (content: Appendix A)
.claude/settings.json  # enforced constraints (deny-list per Appendix A)
LICENSE (Apache-2.0), README.md (stub), .gitignore, .editorconfig
```

Constraints: everything in the repo is English-only without exception (code, comments,
identifiers, commits, branches, PRs, docs, logs, test names). Conventional Commits.

**Status:** merged content complete except §0.3 license replacement, which is folded
into the W1 branch alongside W1.1.

### W1.1 — Source-of-truth import (blocks W2)

The design corpus currently lives outside the repository. The stated working model is
that `docs/` is the single source of truth and external Project Knowledge holds
snapshots; today that relationship is inverted. W1.1 corrects it.

Delivered on the **same branch and PR as W1** — this is W1's acceptance criterion 1,
not a new work package.

1. Import `docs/architecture.md` and `docs/project-brief.md` into the repository.
2. Apply at import time (not as a follow-up commit):
   - BigQuery dataset renamed to `plumbline` in architecture §4.1 and every other
     occurrence, including the §1 diagram.
   - Project Brief architecture summary and any naming references aligned to §0.1.
   - Architecture §7 cost-guardrail row for the BigQuery write path rewritten per W6.2
     below. The existing wording ("Code review + CI grep gate") describes a control that
     cannot detect the violation it targets; importing it unchanged would enshrine a
     known-defective guardrail.
   - Repository visibility and license (§0.2, §0.3) recorded where the architecture or
     Brief makes assumptions about them (Pages data path, zero-cost invariants).
3. Bump `architecture.md` to v0.2 with a dated changelog entry naming the three changes
   above. ADR index and open questions carry over unchanged.
4. Add a precedence note to `README.md`: `docs/` is authoritative; external snapshots
   that disagree are stale by definition.
5. Grep the repository for the pre-decision project name, case-insensitively, in the
   pattern `agent[-_. ]?lens` — which covers every separator variant including its
   underscored dataset form: zero occurrences.

### W2 — ADR-0001..0005 rationale write-ups
Decisions are already fixed in `docs/architecture.md`; each ADR adds context,
alternatives considered, and consequences. One file per ADR under `docs/adr/`, format of
ADR-0001.
- ADR-0001: OTLP wire-format preservation, wire-only scope (arch §3.1). Accepted in the
  architecture index since v0.1 but never written as a file; it is the constraint every
  later spec cites, and it defines the ADR format for this repository.
- ADR-0002: Pub/Sub contract & at-least-once + downstream dedup (arch §3.2–3.3).
- ADR-0003: mappings as in-repo versioned YAML, build-time embedded (arch §5).
- ADR-0004: zero-cost guardrails & kill-switch design (arch §7). **Must record** why a
  literal-string grep is insufficient as the BigQuery write-path control and why the
  forbidden-dependency check is the load-bearing one (see W6.2).
- ADR-0005: static JSON export as v0.1 SPA data path (arch §3.5).
Status moves Proposed → Accepted on PR merge after human review.

### W3 — `docs/eval-plan.md` draft (pre-registration)
Draft only; freezing is a separate, explicit human action, and it is **two-stage**
(eval plan §2). A single freeze before F1 is not achievable: the practical-significance
thresholds are functions of a baseline variance estimate, and no agent data exists at the
F1 entry gate. Freezing constants there would produce arbitrary numbers presented as
pre-registration.
- **Freeze A** — human action at the F1 entry gate, gating F1 code. Fixes criteria,
  metrics, endpoints, statistical tests, decision rules, threshold *formulas*, rubric
  text, dataset spec and splits, degradation catalog, experiment design.
- **Freeze B** — at F3, before the first seeded-regression run. Fills **only** the numeric
  constants that the Freeze-A formulas produce from the baseline calibration run. It may
  not add or remove endpoints, change tests or decision rules, alter the rubric, or
  reweight metrics.

Must contain:
- The four success criteria from the Brief, made measurable (exact thresholds — or, where
  a threshold is a Freeze-B constant, the formula and the calibration input it consumes —
  measurement method, data source for each).
- Seeded-regression experiment design: baseline agent, degradation applied,
  pre-registered detection threshold, pass/fail rule for the gate.
- Judge-tier agreement measurement plan (Ollama vs Gemini Flash).
- A "Changes after freeze require an ADR" clause.

### W4 — GCP project bootstrap + billing kill-switch (human + Claude Code mixed)
Human-only: create GCP project, link billing account, grant Terraform SA/WIF
permissions, and physically confirm the kill-switch test.
Claude Code: Terraform + function source for the kill-switch chain:
budget alert → Pub/Sub topic (`billing-alerts`) → Cloud Function (Gen2, smallest,
us-central1) calling `projects.updateBillingInfo` to detach billing.
- Budget threshold: alert at any spend > $0.
- **Live-fire test is mandatory** (trigger by publishing a synthetic alert message to
  the topic). Evidence (logs + billing page screenshot) archived under
  `docs/runbooks/kill-switch.md`, including the manual re-attach procedure.
- Project-level custom BigQuery query quota set (value per arch §7; document chosen
  number in the runbook).

### W5 — Terraform skeleton
- Remote state: GCS bucket (us-central1, versioning on) — stays within 5 GB free tier.
- Pinned `google` provider + Terraform version; `required_providers` locked.
- Only kill-switch + quota + state resources in F0.
- CI check (W6) runs `terraform fmt -check` and `terraform validate`; a plan-diff
  guard script asserts: no resource types outside the allowlist (arch §7), no Cloud
  Run config with `min_instances > 0` or `max_instances > 2` (activates in F2 but the
  check ships now).

### W6 — GitHub Actions via Workload Identity Federation

#### W6.1 — WIF and fork-PR posture

The repository is public (§0.2), so the identity binding must be explicit rather than
relying on default GitHub behavior.

- WIF pool + OIDC provider for `token.actions.githubusercontent.com`.
- Attribute mapping includes at minimum `assertion.repository`,
  `assertion.repository_owner`, `assertion.ref`.
- **Provider-level attribute condition** pins both repository and owner:
  `assertion.repository == 'arslan-kursad/plumbline' && assertion.repository_owner == 'arslan-kursad'`.
  A pool/provider without an attribute condition is treated as a defect, not a default.
- F0 ships one service account, `ci-readonly`: Terraform state read/write, resource read,
  no mutating IAM. Its principalSet is scoped by the repository attribute.
- The F2 deploy identity pattern is documented here but not created: a separate
  `ci-deploy` SA whose principalSet additionally requires
  `attribute.ref == 'refs/heads/main'`.
- No SA key JSON anywhere — enforced by Gate C below, not by convention.

Workflow-level rules:
- `pull_request_target` is not used in any workflow file (Gate D, scoped to
  `.github/workflows/` — the only location GitHub reads workflows from).
- Top-level `permissions:` is `contents: read`. `id-token: write` is granted only on the
  single job that authenticates to GCP.
- That job is additionally guarded by
  `if: github.event.pull_request.head.repo.full_name == github.repository`, so a fork PR
  cannot reach the cloud identity even if GitHub's default token scoping changes.
- Repository Actions setting: require approval for workflow runs from all outside
  contributors.

#### W6.2 — Cost-invariant CI gates (replaces the v0.1 `insertAll` grep)

The v0.1 gate grepped the repository for the literal string `insertAll`. That control is
defective in both directions: the .NET BigQuery client exposes the streaming insert path
as `BigQueryClient.InsertRow` / `InsertRows` / `InsertRowsAsync` and never surfaces the
literal REST method name, so a real violation in `worker/` would pass; meanwhile
`CLAUDE.md` legitimately contains the string and would fail. A gate that cannot fail on
the violation it targets is worse than no gate, because it is trusted.

**Pattern notation (applies to every gate).** Forbidden-string patterns are written in a
form that does not match their own textual representation; a character class around a
single literal character is sufficient (`private[_]key`, `agent[-_. ]?lens`). This holds
both in the gate scripts and in this specification. Consequence: no gate requires an
exclusion list, no gate can be defeated by adding a path to one, and a whole-repository
scan stays whole-repository. Gate B is path-scoped for an unrelated reason — it targets a
property of source code, where a match in documentation is not a defect.

Gates live in `scripts/ci/invariant-gates.sh`, are runnable locally, and exit non-zero
printing offending `path:line`.

- **Gate A — forbidden dependency (load-bearing).** Fail if any `*.csproj` or
  `Directory.Packages.props` references `Google.Cloud.BigQuery.V2`. The only permitted
  BigQuery write dependency is `Google.Cloud.BigQuery.Storage.V1`. If the package is
  absent, the forbidden API surface does not exist regardless of symbol naming.
- **Gate B — path-scoped symbol scan (secondary).** Over `collector/**/*.go`,
  `worker/**/*.cs`, `analytics/**/*.cs` only: `insertAll`, `tabledata.insertAll`,
  `InsertRow(`, `InsertRows(`, `InsertRowsAsync(`, `.Inserter(`. Scope is a path
  allowlist, not a file denylist — documentation will keep naming these symbols and must
  never need an exclusion entry.
- **Gate C — no exported service account keys.** Whole repository, no exclusions:
  `"private[_]key"` and `"type"\s*:\s*"service[_]account"`. Scope stays whole-repository:
  a leaked key can land in any path, so narrowing this gate would be a regression.
  Gate C is a detection backstop behind W6.4, not the control.
- **Gate D — no `pull_request_target`** in `.github/workflows/`.
- **Gate E — retired project name.** Whole repository, case-insensitive:
  `agent[-_. ]?lens`. Value here is documentation hygiene rather than correctness — a
  stale dataset name would fail loudly at query time — but the repository is public and
  is itself the case study. Live reintroduction vector: documents re-derived from
  external snapshots that predate the rename.

#### W6.3 — Pipeline

`ci.yml`, path-filtered jobs: Go build/vet (collector), .NET build (worker, analytics),
Terraform fmt/validate + plan-diff guard, invariant gates. English-only linting of docs
is out of scope (manual review). All jobs green on empty scaffolds.

#### W6.4 — Repository-level secret controls

Enable GitHub secret scanning and **push protection** (free on public repositories).
Push protection rejects the commit at push time, before the secret reaches history;
Gate C runs in CI, after the push has already happened. Recorded in ADR-0004 alongside
the Gate A / Gate B asymmetry: for every invariant, the spec names which control
prevents and which merely reports.

Repository security settings are configured manually (adding a GitHub Terraform provider
for three toggles is disproportionate; the "nothing hand-created" rule in architecture §8
scopes to GCP resources). Baseline at F0 start, verified via the repository API:
`secret_scanning`, `secret_scanning_push_protection`, and
`secret_scanning_validity_checks` all disabled. All three are enabled in W6.4 and the
post-change API output is archived in `docs/runbooks/repository-settings.md` alongside
the kill-switch evidence.

The baseline above is verified, not assumed — `gh api repos/arslan-kursad/plumbline
--jq '.security_and_analysis'` on 2026-08-18 returned `disabled` for all three.

**Fourth setting — `secret_scanning_non_provider_patterns`, also enabled in W6.4.**
Provider patterns match known vendor key formats. This repository's real future exposure
sits outside them: plumbline mints its own API keys (architecture §6.3 — generated once,
shown once, stored hashed), and those carry no provider signature. The concrete collision
point is F1, where golden-file fixtures will contain OTLP payloads with key-like strings.
Both outcomes are the wanted ones: either a real leak is caught, or the fixtures are
forced to use values that are obviously fake and marked as such — the discipline a public
repository should have anyway. Noise cost is low and alerts are dismissible. Extend the
archived evidence in `docs/runbooks/repository-settings.md` to cover all four settings.

**Runbook scope — the inventory is wider than W6.4.** A setting changed outside any work
package is drift unless it is written down, and "drift = bug" is this project's own rule.
`docs/runbooks/repository-settings.md` is the complete inventory of manually managed
repository settings, not only those touched by W6.4. Each entry records the setting,
its state, the date and reason it was changed, and the API evidence. Settings changed
outside a work package are recorded the same way — Dependabot alerts was enabled during
an F0 design session (see issue #2), ahead of §W6.6, to close the exposure window on a
public repository; auto-update PRs remain disabled until F1.

#### W6.5 — Branch protection: scope and recovery

`main` protection is enabled with `enforce_admins=true` and zero required approvals.
Zero is deliberate: a single-author repository cannot self-approve, and requiring one
approval would deadlock every merge. State the consequence plainly — the PR requirement
does not produce review. What it produces is CI execution before `main` and a recorded
diff. Review in this project is a process commitment (propose → confirm), not a
mechanically enforced one. A reader of a public case study must not infer otherwise.

Once required status checks are added, a broken workflow file can deadlock `main`:
the fix cannot merge because the check it repairs is failing. `enforce_admins` blocks
rule bypass, not rule modification, so the escape is to disable protection, merge the
fix, and re-enable. Every use of that escape is logged in
`docs/runbooks/branch-protection.md` with date, PR, and reason — an undocumented
disable/re-enable cycle is exactly the silent degradation this project rejects.

#### W6.6 — Dependency-vulnerability posture

A separate item, deliberately not part of W6.4. W6.4 is about secrets; this is supply
chain. Keeping them in one bullet would blur two different threat classes, so this lands
as its own spec item and hangs off the F5 threat model rather than off W6.4. Two distinct
controls, often confused:

- **Dependabot alerts** (endpoint `/vulnerability-alerts`) — information only, produces
  no pull requests. Enabled on 2026-08-18: the endpoint returned `404` (disabled) before
  and `204` (enabled) after. Free and silent, and a public case study with vulnerability
  alerts switched off reads as careless.
- **Dependabot security updates** (`security_and_analysis.dependabot_security_updates`,
  the field measured earlier) — this is the one that opens automatic PRs. **Deferred to
  F1**, and deferred in writing rather than silently omitted: on an empty scaffold the
  benefit is zero while the cost is real, since a ~90-hour part-time budget cannot absorb
  review-queue churn. Verified still `disabled`. Enable it once F1 creates an actual
  dependency surface.

## 5. Acceptance criteria (Definition of Done)

1. Naming decision (`plumbline`) applied everywhere; zero occurrences of the
   pre-decision name in the repository — pattern `agent[-_. ]?lens`, case-insensitive,
   covering every separator variant including its underscored dataset form.
2. Repo scaffold merged to `main`; `CLAUDE.md` + `.claude/settings.json` present;
   `LICENSE` is Apache-2.0.
3. **W1.1 complete:** `docs/architecture.md` (v0.2) and `docs/project-brief.md` in the
   repository with the dataset rename and the §7 guardrail correction applied at import;
   `README.md` states `docs/` precedence.
4. Repository is public; `main` branch protection enabled (PR required, force-push
   denied, required status checks once CI is green), **and** its scope and recovery
   procedure recorded in `docs/runbooks/branch-protection.md` per W6.5 — including the
   statement that the PR requirement does not by itself produce review.
5. ADR-0001..0005 in `docs/adr/`, 0002–0005 Accepted after review; ADR-0004 records the
   grep-insufficiency rationale.
6. `docs/eval-plan.md` present on `main` with Status `DRAFT — NOT FROZEN`; Freeze A is a
   separate, explicitly tagged human action and is **not** part of F0.
7. **Kill-switch live-fired**: billing detached by the function during the test,
   evidence archived, re-attach runbook written. Billing re-attached afterward.
8. CI pipeline green on `main` via WIF; WIF provider carries the repository+owner
   attribute condition; zero exported SA keys in repo or GitHub secrets.
9. Gates A–E active **and each proven to fail** — see §6.
10. `terraform plan` clean; state in GCS backend.
11. GCP bill for the period: **$0.00**.

## 6. Test expectations

- No unit tests in F0 (no product code). Placeholder test targets may exist so CI
  jobs are real, but must not assert trivialities to fake coverage.
- Kill-switch: one documented live-fire with archived evidence — this is the test.
- **Gates A–E: each proven by a deliberate local violation** (temporary commit on a
  throwaway branch, gate observed failing, revert). A gate verified only against a clean
  tree is unverified. Evidence recorded in the F0 completion note; the same philosophy as
  the kill-switch live-fire.
- CI: link to green run on `main` recorded in the F0 completion note.

---

## Appendix A — CLAUDE.md required content (created in W1)

Advisory contract for Claude Code; `.claude/settings.json` enforces the mechanical
subset (file-path deny rules, command deny-list). Minimum content:

- **Language:** English only in every repo artifact, no exceptions.
- **Cost invariants (hard):** the BigQuery write path is Storage Write API only — the
  legacy streaming insert API and its client package are forbidden; never create
  Terraform outside the resource-type allowlist; Cloud Run always `min_instances=0`,
  `max_instances<=2`, us-central1; no topic-level Pub/Sub retention.
- **Boundaries:** collector never parses span semantics; worker never mutates raw
  OTLP bytes before deserialization; mappings live only in
  `normalization/mappings/` (never Firestore, never env config).
- **Process:** one spec = one branch = one PR; Conventional Commits; golden-file
  tests accompany any normalization change; no scope beyond the active spec —
  discovered work is proposed back as a spec change, not silently implemented.
- **Docs:** `docs/` is the single source of truth; contradictions are raised, not
  resolved unilaterally.
- **Public repository:** every commit is world-readable on push. No secrets, no
  customer data, no internal hostnames, ever — including in test fixtures.

---

## Changelog

**v0.6 — 2026-08-19** (supersedes v0.5) — W4/W5 implementation.

1. §W6.1 corrected: Gate D's scope was stated as the whole repository there and as
   `.github/workflows/` in §W6.2. The path-scoped statement is authoritative — the
   string is a property of workflow files, GitHub reads workflows from that path
   only, and a mention in documentation is not a defect. Same exemption already
   granted to Gate B in §W6.2. Closes issue #4, whose blocking condition was that
   this merge precede W6 implementation.
2. **W5's plan-diff guard was unimplementable as written and is now implementable.**
   It asserts "no resource types outside the allowlist (arch §7)"; architecture §7
   named an allowlist it did not contain, as does `CLAUDE.md`. The list now exists
   as architecture §7.1 (v0.4), and the guard parses that section rather than
   keeping a second copy.
3. The guard carries three assertions beyond the two this spec named — region,
   Pub/Sub topic retention, and the existing Cloud Run scaling bounds extended to
   Cloud Functions Gen2, which run on Cloud Run and were otherwise unchecked. Each
   enforces a `CLAUDE.md` hard invariant that had no mechanical control; recorded
   in architecture §7.1 rather than left as undocumented strictness.
4. W4 implementation decisions, recorded because each is a place where the spec's
   wording and the platform's behaviour do not line up one-to-one:
   - "Budget threshold: alert at any spend > $0" is implemented as budget
     `all_updates_rule` — a notification on every cost update — plus a strictly
     greater than zero comparison in the function. The Budget API has no zero
     threshold, so the threshold rule alone could not express the requirement.
   - Credits are excluded from the budget filter: a trial credit must not mask
     gross spend.
   - The BigQuery custom query quota value W4 leaves to be chosen and documented
     is **20480 MiB/day (20 GiB)**, against a 200 TiB/day platform default; the
     arithmetic against the 1 TiB/month free query tier is in
     `docs/runbooks/kill-switch.md` §6.
   - A `bootstrap/` module with local state creates the GCS state bucket, since
     the root module's backend cannot be a bucket that module has yet to create.
   - The kill-switch identity can detach billing and cannot re-attach it, making
     the re-attach procedure human-only by construction rather than by convention.
5. Acceptance criteria 7, 8, 10 and 11 remain open after this work package by
   construction: they require a GCP project, a linked billing account, and an
   observed live-fire, none of which can be produced from the repository.

**v0.5 — 2026-08-19** (supersedes v0.4)

1. Acceptance criterion 6 rewritten. "Draft PR open (not frozen)" was inconsistent with
   the rest of the design on three counts: eval plan §2 defines Freeze A as an annotated
   tag plus the file's SHA-256, and a file that is not on `main` cannot be tagged;
   CLAUDE.md makes `docs/` the source of truth, so declaring F0 done while
   `docs/eval-plan.md` exists only on a branch contradicts it; and an open PR is not a
   durable state — it rots and conflicts once F1 starts. The draft property is carried by
   the file's own `Status: DRAFT — NOT FROZEN` header, which survives the merge, rather
   than by the review state of a pull request.
2. §2 out-of-scope entry aligned with the two-stage freeze introduced in v0.4; it still
   said "freeze is the F1 entry gate", which is true of Freeze A only.

**v0.4 — 2026-08-19** (supersedes v0.3)

1. W3 freeze mechanics corrected to two stages. v0.3 assumed one freeze, before F1 code.
   The delivered `docs/eval-plan.md` v0.1 draft (§2) splits it: Freeze A at the F1 entry
   gate still gates F1 code, while Freeze B at F3 fills the numeric constants that cannot
   exist before a baseline calibration run. Without the split, the eval plan and this spec
   contradict each other on when thresholds become binding, and the pre-registration claim
   would rest on constants invented rather than measured. Freeze B is bounded: constants
   only, no change to criteria, endpoints, tests, rules or rubric.
2. W3 first required item reworded accordingly — a criterion whose threshold is a Freeze-B
   constant states the formula and its calibration input instead of a number.

**v0.3 — 2026-08-18** (supersedes v0.2)

1. Pattern notation convention added to W6.2: forbidden-string patterns are written so
   they cannot match their own representation. Replaces the descriptive-phrasing
   workaround applied during the W1.1 import; literals are restored in W1.1 item 5 and
   acceptance criterion 1.
2. Gate C corrected to self-non-matching patterns; scope stays whole-repository —
   path-scoping a secret scan would be a regression.
3. Gate E added (retired project name), W6.4 added (push protection as the preventive
   control behind Gate C). Acceptance criterion 9 and §6 now read Gates A–E: a gate that
   exists but is not required to be proven failing is the defect class §W6.2 was written
   to remove.
4. W6.4 extended: repository security settings are named as manually owned with archived
   evidence, since the "nothing hand-created" rule in architecture §8 scopes to GCP
   resources; the F0-start baseline is recorded.
5. W6.5 added: branch protection scope and recovery — the PR requirement does not produce
   review, and the deadlock escape for a broken workflow file is documented rather than
   discovered under pressure. Acceptance criterion 4 extended accordingly.
6. Dependency-vulnerability posture recorded as a separate item from W6.4: alerts enabled
   at F0, automatic security-update PRs deferred to F1 in writing. Secrets and supply
   chain are distinct threat classes and are specified separately.
7. W2 scope corrected to ADR-0001..0005. ADR-0001 was Accepted in the architecture index
   but had no file; acceptance criterion 5 already required one, and `docs/adr/README.md`
   referred to a format defined by a document that did not exist.
8. §0.3 wording corrected: the LICENSE file carries the standard Apache-2.0 text with the
   appendix boilerplate filled in (year and copyright owner), which is what the GitHub
   license template produces; "unmodified" overstated it. No NOTICE file in v0.1 — there
   are no third-party attributions to carry.
9. Architecture bumped to v0.3 on this branch: §2.3 write-path contract, §10 ADR index and
   open question 5, §11 changelog.

**v0.2 — 2026-08-18** (supersedes v0.1, same date)

1. §0 expanded from "Naming decision" to "Project constants": repository visibility
   fixed to **public** (§0.2) and license changed from MIT to **Apache-2.0** (§0.3),
   with rationale. Driver: GitHub Pages on Free requires a public repository, so the
   SPA data path (arch §3.5) is incompatible with a private repository under the
   zero-cost invariant.
2. **W1.1 added** — import of `architecture.md` and `project-brief.md` into `docs/`.
   v0.1 assumed these files were already in the repository; they were not, leaving the
   source of truth outside version control and W1 acceptance criterion 1
   unsatisfiable. W1.1 is delivered on the W1 branch and blocks W2.
3. **W6 rewritten.** The v0.1 `insertAll` repository grep cannot detect the violation it
   targets (the .NET client exposes `InsertRow`/`InsertRows`/`InsertRowsAsync`) while
   failing on `CLAUDE.md`. Replaced by Gate A (forbidden NuGet package, load-bearing),
   Gate B (path-scoped symbol scan), Gate C (SA key scan), Gate D
   (`pull_request_target` ban). Architecture §7 is corrected to match during the W1.1
   import.
4. **W6.1 added** — explicit WIF attribute conditions and fork-PR workflow posture,
   required because the repository is public.
5. §6 now requires each CI gate to be proven failing, not merely passing on a clean tree.
6. Acceptance criteria renumbered 1–11 accordingly.
