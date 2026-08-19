# F0 — Completion note

**Date:** 2026-08-19 · **Spec:** [`F0-foundations.md`](F0-foundations.md) v0.7
**Status: F0 is not complete.** Seven of eleven acceptance criteria are met; four
require a GCP project that does not exist yet, and are listed in §3 with the
procedure to close them.

This note exists because the spec asks for one (§6): the gate proofs and the CI
run link are recorded here. It states what is done, what is not, and what the
evidence is — a phase that reports itself complete while an acceptance criterion
is open is the failure this project is written against.

## 1. Acceptance criteria

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Naming applied; zero occurrences of the pre-decision name | **met** | Gate E, running on every build over every non-ignored file |
| 2 | Scaffold on `main`; `CLAUDE.md`, `.claude/settings.json`, Apache-2.0 | **met** | Merged in PR #1 |
| 3 | W1.1: architecture and Brief imported, dataset renamed, §7 guardrail corrected, `README` precedence | **met** | PR #1; architecture now v0.4 |
| 4 | Repository public; `main` protection enabled **and** its scope recorded | **met** | [`runbooks/branch-protection.md`](../runbooks/branch-protection.md). Protection predated the runbook and was undocumented drift; required status checks are added after the first green run on `main` (§3.5) |
| 5 | ADR-0001..0005, 0002–0005 Accepted; ADR-0004 records the grep-insufficiency rationale | **met** | [`docs/adr/`](../adr/) |
| 6 | `docs/eval-plan.md` on `main`, `DRAFT — NOT FROZEN` | **met** | PR #6 |
| 7 | **Kill-switch live-fired**, evidence archived, billing re-attached | **open** | Configuration and procedure ready: [`runbooks/kill-switch.md`](../runbooks/kill-switch.md). §4 of that file is empty and says so |
| 8 | CI green on `main` via WIF; provider carries the repository+owner condition; zero exported SA keys | **partly met** | Pipeline green on PR #15 (run [32282075482](https://github.com/arslan-kursad/plumbline/actions/runs/32282075482)); WIF configuration written with the attribute condition; **no authenticated run has happened**, because the identity does not exist yet |
| 9 | Gates A–E active **and each proven to fail** | **met** | [`evidence/f0-gate-proofs.md`](../evidence/f0-gate-proofs.md); `prove-gates.sh` runs in CI on every build |
| 10 | `terraform plan` clean; state in the GCS backend | **open** | `fmt`/`validate` pass in CI; `plan` needs the project |
| 11 | GCP bill for the period: **$0.00** | **open** | No project, no bill. Not the same as a verified $0.00 |

## 2. What the phase produced beyond the checklist

Three defects were found in the specification itself while implementing it, and
each was fixed in the branch that found it rather than noted for later:

1. **The Terraform resource-type allowlist did not exist.** `CLAUDE.md` and W5
   both forbid resources "outside the allowlist (architecture §7)", and §7 named
   a list it never contained — so the plan guard was unimplementable as written.
   Architecture §7.1 now enumerates it, and the guard parses that section rather
   than keeping a copy.
2. **Two settings W6.4 mandates are paid features.** Secret scanning validity
   checks and non-provider patterns require GitHub Secret Protection; the API
   accepts the enabling request, returns 200, and changes nothing. The spec was
   requiring a purchase the zero-cost invariant forbids. Withdrawn in v0.7, with
   the residual F1 exposure stated rather than treated as covered.
3. **Gate D fired on its own documentation**, and the gate proof transcript
   tripped Gates C and E. Both fixed by making the gates more precise — workflow
   files rather than a whole directory, mechanical redaction of the transcript —
   never by an exclusion list. The gates also scan untracked-but-not-ignored
   files now: scanning only tracked files passes a violation locally until
   someone runs `git add`, and then fails it in CI.

Each is recorded in the F0 spec changelog (v0.6, v0.7) with its reasoning.

## 3. What is left, in order

Everything below needs a human: it requires creating a GCP project, linking a
billing account, and watching billing detach. None of it can be produced from
the repository.

1. **Merge the open pull requests** (#14, then #15, then this one). They are
   stacked in that order.
2. **Create the GCP project and link billing.** Prerequisites and the API-enabling
   step that must precede the first plan: [`runbooks/kill-switch.md`](../runbooks/kill-switch.md) §2.
3. **Apply Terraform** — `bootstrap/`, then the root module:
   [`infra/terraform/README.md`](../../infra/terraform/README.md). Closes criterion 10.
4. **Live-fire the kill-switch** and archive the evidence in §4 of its runbook,
   then re-attach billing. Closes criterion 7.
5. **Set the repository variables** so the CI plan job stops skipping:
   `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_CI_SERVICE_ACCOUNT`, `GCP_PROJECT_ID`,
   `GCP_STATE_BUCKET`, and the `GCP_BILLING_ACCOUNT_ID` secret. The Terraform
   outputs print the first two. Then add the required status check per
   [`runbooks/branch-protection.md`](../runbooks/branch-protection.md), and record the green
   run's URL in criterion 8 above. Closes criterion 8.
6. **Check the bill** at the end of the billing period. Closes criterion 11.

Tracked as an issue so it does not live only in this file.

## 4. Notes for whoever closes this

- **A skipped job is not a passing job.** `terraform plan (wif)` skips until the
  repository variables exist, and the pipeline is green either way. Criterion 8
  is closed by a specific authenticated run's URL, not by the absence of red.
- **Read settings back after writing them.** The two paid settings taught this
  the expensive way: the API reports success and changes nothing.
- **The Go and .NET jobs have not run in CI yet.** Path filtering applies to pull
  requests, and no pull request has touched those directories; on `main` every
  job runs, so the first push there is what proves W6.3's "all jobs green on
  empty scaffolds". Locally, the identical commands pass.
