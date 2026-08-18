# F0 — Foundations: Work Package Spec

**Version:** 0.1 · **Status:** Proposed (awaiting sign-off) · **Date:** 2026-08-18
**Phase budget:** ~8 h · **Executor:** Claude Code (implementation) + human (billing/manual steps)
**Repo target:** `docs/specs/F0-foundations.md`

---

## 0. Naming decision (RESOLVED)

Project name: **`plumbline`** (decided 2026-08-18, human sign-off). All derived names
follow from it and are fixed here:

- Repository: `plumbline`
- Go module: `github.com/arslan-kursad/plumbline/collector`
- .NET solutions: `Plumbline.Worker`, `Plumbline.Analytics`
- Container images: `collector`, `ingestion-worker`, `analytics-api` under the
  `plumbline` Artifact Registry repo
- BigQuery dataset: `plumbline` (replaces the pre-decision working name;
  underscores unnecessary, single word is a valid dataset ID)

Alignment task (part of W1 PR): update Project Brief and architecture.md §4.1 dataset
name; grep the docs tree for the old working name (hyphenated and underscored
variants) — zero occurrences after W1. This copy of the spec is itself aligned:
the old name is referred to only descriptively, never literally.

---

## 1. Purpose

Establish the project skeleton and the zero-cost safety envelope **before any pipeline
code exists**: repository scaffold with Claude Code governance files, ADR rationale
write-ups, a pre-registered evaluation plan draft, a GCP project whose billing
kill-switch has been **live-fired**, a Terraform skeleton, and a green CI pipeline
authenticated via Workload Identity Federation (no exported SA keys).

## 2. Out of scope

- Any collector / worker / analytics / eval implementation code (F1+).
- Terraform for Pub/Sub, BigQuery, Firestore, Cloud Run application services (F2).
  F0 Terraform covers only: state backend, provider pinning, kill-switch resources,
  project-level quota/guardrail settings.
- Freezing `eval-plan.md` (draft in F0; freeze is the F1 entry gate).
- Dashboards, SPA, load generator (F4).

## 3. Context files (read before starting)

- `docs/architecture.md` v0.1 — §7 (cost guardrails), §6.1 (WIF row), §8 (deployment).
- Project Brief — Phases (F0 DoD), Zero-cost invariants.
- ADR-0001 (Accepted) — scope constraint on all future work.

## 4. Work items

### W1 — Repository scaffold
Monorepo layout:

```
/collector/            # Go module (empty main + README stub)
/worker/               # .NET 8 (empty solution + project stubs)
/analytics/            # .NET 8 (empty solution + project stubs)
/normalization/mappings/v1.41/   # placeholder README, no YAML yet (F1)
/infra/terraform/      # W5
/docs/                 # architecture.md, adr/, specs/, runbooks/, eval-plan.md
/.github/workflows/    # W6
CLAUDE.md              # advisory contract for Claude Code (content: Appendix A)
.claude/settings.json  # enforced constraints (deny-list per Appendix A)
LICENSE, README.md (stub), .gitignore, .editorconfig
```

Constraints: everything in the repo is English-only without exception (code, comments,
identifiers, commits, branches, PRs, docs, logs, test names). Conventional Commits.

### W2 — ADR-0002..0005 rationale write-ups
Decisions are already fixed in architecture.md; each ADR adds context, alternatives
considered, and consequences. One file per ADR under `docs/adr/`, format of ADR-0001.
- ADR-0002: Pub/Sub contract & at-least-once + downstream dedup (arch §3.2–3.3).
- ADR-0003: mappings as in-repo versioned YAML, build-time embedded (arch §5).
- ADR-0004: zero-cost guardrails & kill-switch design (arch §7).
- ADR-0005: static JSON export as v0.1 SPA data path (arch §3.5).
Status moves Proposed → Accepted on PR merge after human review.

### W3 — `docs/eval-plan.md` draft (pre-registration)
Draft only; freezing is a separate, explicit human action gating F1 code. Must contain:
- The four success criteria from the Brief, made measurable (exact thresholds,
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
- WIF pool + provider bound to the repo (`main` + PR branches), no SA key JSON
  anywhere (CI grep gate asserts absence of `"private_key"` patterns).
- Pipeline `ci.yml`: path-filtered jobs — Go build/vet (collector), .NET build
  (worker, analytics), Terraform fmt/validate, English-only lint on docs is out of
  scope (manual review). All jobs green on empty scaffolds.
- CI grep gate from arch §7 ships now: fail on `insertAll` anywhere in the repo.

## 5. Acceptance criteria (Definition of Done)

1. Naming decision (`plumbline`) applied everywhere: architecture.md §4.1 dataset
   renamed, Brief updated, zero occurrences of the old working name in the repo.
2. Repo scaffold merged to `main`; `CLAUDE.md` + `.claude/settings.json` present.
3. ADR-0001..0005 in `docs/adr/`, 0002–0005 Accepted after review.
4. `docs/eval-plan.md` draft PR open (not frozen).
5. **Kill-switch live-fired**: billing detached by the function during the test,
   evidence archived, re-attach runbook written. Billing re-attached afterward.
6. CI pipeline green on `main` via WIF; zero exported SA keys in repo or GitHub
   secrets; `insertAll` grep gate active.
7. `terraform plan` clean; state in GCS backend.
8. GCP bill for the period: **$0.00**.

## 6. Test expectations

- No unit tests in F0 (no product code). Placeholder test targets may exist so CI
  jobs are real, but must not assert trivialities to fake coverage.
- Kill-switch: one documented live-fire with archived evidence — this is the test.
- CI: link to green run on `main` recorded in the F0 completion note.

---

## Appendix A — CLAUDE.md required content (created in W1)

Advisory contract for Claude Code; `.claude/settings.json` enforces the mechanical
subset (file-path deny rules, command deny-list). Minimum content:

- **Language:** English only in every repo artifact, no exceptions.
- **Cost invariants (hard):** never write an `insertAll` code path; never create
  Terraform outside the resource-type allowlist; Cloud Run always
  `min_instances=0`, `max_instances<=2`, us-central1; no topic-level Pub/Sub
  retention; Storage Write API is the only BigQuery write path.
- **Boundaries:** collector never parses span semantics; worker never mutates raw
  OTLP bytes before deserialization; mappings live only in
  `normalization/mappings/` (never Firestore, never env config).
- **Process:** one spec = one branch = one PR; Conventional Commits; golden-file
  tests accompany any normalization change; no scope beyond the active spec —
  discovered work is proposed back as a spec change, not silently implemented.
- **Docs:** `docs/` is the single source of truth; contradictions are raised, not
  resolved unilaterally.
