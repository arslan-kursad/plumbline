# F0 — Completion note

**Date:** 2026-08-19 · **Spec:** [`F0-foundations.md`](F0-foundations.md) v0.7
**Status: F0 is not complete.** Seven of eleven acceptance criteria are fully met,
one is partly met, and three require GCP work that has only just become possible —
the project now exists. §3 lists what remains, in the order it has to happen.

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
| 4 | Repository public; `main` protection enabled **and** its scope recorded | **met** | Public; PR required, force-push denied, `enforce_admins`; required check `ci complete` (strict) added 2026-08-21 after the first green `main` run, with the read-back and the log entry in [`runbooks/branch-protection.md`](../runbooks/branch-protection.md) |
| 5 | ADR-0001..0005, 0002–0005 Accepted; ADR-0004 records the grep-insufficiency rationale | **met** | [`docs/adr/`](../adr/) |
| 6 | `docs/eval-plan.md` on `main`, `DRAFT — NOT FROZEN` | **met** | PR #6 |
| 7 | **Kill-switch live-fired**, evidence archived, billing re-attached | **open** (#17) | Configuration and procedure ready: [`runbooks/kill-switch.md`](../runbooks/kill-switch.md). §4 of that file is empty and says so |
| 8 | CI green on `main` via WIF; provider carries the repository+owner condition; zero exported SA keys | **partly met** | CI green on `main` with **every job actually running** — run [32468242751](https://github.com/arslan-kursad/plumbline/actions/runs/32468242751). WIF configuration written with the attribute condition; **no authenticated run has happened**, because the identity does not exist yet |
| 9 | Gates A–E active **and each proven to fail** | **met** | [`evidence/f0-gate-proofs.md`](../evidence/f0-gate-proofs.md); `prove-gates.sh` runs in CI on every build |
| 10 | `terraform plan` clean; state in the GCS backend | **open** (#17) | `fmt`/`validate` pass in CI; `plan` needs the project |
| 11 | GCP bill for the period: **$0.00** | **open** (#17) | No project, no bill. Not the same as a verified $0.00 |

## 2. What the phase produced beyond the checklist

Five things were found while implementing the specification — three in the spec,
two in the implementation — and each was fixed in the branch that found it rather
than noted for later:

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

4. **The budget measured the wrong thing** (found in review, before #14 merged).
   The filter was `EXCLUDE_ALL_CREDITS`, which makes spend equal gross cost —
   but Always Free is a `FREE_TIER` credit against a non-zero gross line, not an
   absence of charge. The kill-switch would have detached billing on the first
   Cloud Run request in F2, with the invoice at $0.00 and no way for the system
   to undo it. Corrected to `INCLUDE_SPECIFIED_CREDITS` over `FREE_TIER` alone:
   ADR-0004 Amendment 1. **The live-fire could not have caught this** — it starts
   at Pub/Sub, and the defect was in how the budget computed the number the
   function reads.

5. **Four things would have failed at the first apply or the first authenticated
   CI run** (found by checking the configuration's assumptions against current
   platform behaviour, before running it rather than during):
   - The budget pinned `currency_code = "USD"`; the Budget API rejects a create
     whose currency differs from the billing account's. Now inherited.
   - Cloud Build builds Gen2 functions as the *default compute* service account,
     which exists only once the Compute Engine API is enabled — an API this
     project has no reason to enable. Replaced with a named build identity.
   - `cloudquotas`, `sts` and `iamcredentials` were not in the enabled-API list.
     The first fails the apply; the other two fail the CI authentication, after
     the apply looks clean.
   - The CI identity could not read the budget (a billing-account resource) or
     the quota preference, both of which `terraform plan` refreshes. It would
     have authenticated successfully and then failed on permissions.

Items 1–3 are recorded in the F0 spec changelog (v0.6, v0.7) with their
reasoning; item 4 is ADR-0004 Amendment 1; item 5 is in the pull requests that
made each change and in the first-apply table in
[`runbooks/kill-switch.md`](../runbooks/kill-switch.md) §2.

None of item 5 was found by a test. They were found by reading what each resource
actually calls — which is the only method available before a project exists, and
is worth naming as such rather than presenting as diligence.

6. **The first real apply found what reading could not.** Thirty-eight of forty
   resources created; the budget and the quota preference failed with a 403
   saying the quota project "is not set by default" and naming a consumer project
   belonging to Google's shared gcloud OAuth client. The ADC quota project *was*
   set — but the provider only sends it when `user_project_override` is
   configured, which it was not. Fixed in the provider block, with the callers'
   `serviceusage.services.use` grant that follows from it.

   This is the honest counterweight to item 5: a pre-flight pass over the
   configuration removes the failures that are visible in what the code calls.
   It does not remove the ones that live in how credentials are attributed, and
   the first apply was always going to be the thing that found those.

## 3. What is left, in order

Already done, and recorded here so the list below is only what is left: the F0
pull requests are merged, `main` is green with every job running, the required
status check is in place, and the GCP project has been created with billing
linked.

Everything below needs a human at a console: applying Terraform, watching billing
detach, and reading a bill. None of it can be produced from the repository.

1. **Enable the two APIs Terraform needs before it can enable the rest** —
   `cloudresourcemanager` and `serviceusage`. On a fresh project the first plan
   fails without them and the error reads like a bug in the configuration:
   [`runbooks/kill-switch.md`](../runbooks/kill-switch.md) §2.
2. **Confirm the pinned function runtime is still offered**
   (`gcloud functions runtimes list --region us-central1`). The pin is `go126`,
   which is generally available per the published support matrix — deprecation
   Feb/Mar 2027, decommission Aug/Sep 2027. Raising it past the function's
   `go.mod` language version is safe; lowering it below is not.
3. **Apply Terraform** — `bootstrap/`, then the root module:
   [`infra/terraform/README.md`](../../infra/terraform/README.md). Closes criterion 10.
4. **Live-fire the kill-switch** and archive the evidence in §4 of its runbook,
   then re-attach billing. Closes criterion 7. Note what it does not cover: the
   budget → notification segment is checked in F2, not here.
5. **Record Verification A**, the morning after the apply: Billing → Reports with
   the credit filters cleared, confirming a non-zero usage cost against a zero net
   total. It is the premise the budget's spend basis rests on (ADR-0004
   Amendment 1) and is currently supported by Google's documentation alone. It
   comes *after* the apply on purpose — an empty project produces no usage line,
   so both figures read zero and the check confirms nothing. Procedure and evidence
   slot: [`runbooks/kill-switch.md`](../runbooks/kill-switch.md) §1.
6. **Set the repository variables** so the CI plan job stops skipping:
   `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_CI_SERVICE_ACCOUNT`, `GCP_PROJECT_ID`,
   `GCP_STATE_BUCKET`, and the `GCP_BILLING_ACCOUNT_ID` secret. The Terraform
   outputs print the first two. Record the resulting green run's URL in criterion 8
   above. Closes criterion 8.
7. **Check the bill** at the end of the billing period. Closes criterion 11.

Tracked as [issue #17](https://github.com/arslan-kursad/plumbline/issues/17), so the
remaining work does not live only in this file.

## 4. Notes for whoever closes this

- **A skipped job is not a passing job.** `terraform plan (wif)` skips until the
  repository variables exist, and the pipeline is green either way. Criterion 8
  is closed by a specific authenticated run's URL, not by the absence of red.
- **Read settings back after writing them.** The two paid settings taught this
  the expensive way: the API reports success and changes nothing.
- **A green live-fire is not a green kill-switch.** It exercises Pub/Sub →
  function → detach and nothing upstream of that. The review that caught the
  spend-basis defect caught something no F0 test could have.
- **W6.3's "all jobs green on empty scaffolds" is now observed, not assumed.** On
  the first `main` run after the merges, every job ran — Go collector, kill-switch
  function, both .NET solutions, Terraform static checks, gates and their proofs —
  and passed. Only `terraform plan (wif)` skipped, for want of an identity.
