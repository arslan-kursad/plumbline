# .github/workflows

Two workflows, and the split between them is the F2 governance model in file form:
`ci.yml` proves things and mutates nothing, `deploy.yml` is the only path that mutates
the cloud.

`ci.yml` — path-filtered Go, .NET, Terraform and end-to-end jobs, plus the invariant
gates, aggregated into a single `ci complete` status check.

| Job | Runs when | What it proves |
| --- | --- | --- |
| `invariant gates` | always | Gates A–F pass, **and** each is proven able to fail |
| `collector (go)` | `collector/`, `testdata/` | build, vet, `go test -race` |
| `worker and analytics (.net)` | `worker/`, `analytics/`, `normalization/`, `testdata/`, `third_party/` | build and `dotnet test` — golden files included |
| `local end-to-end` | anything the pipeline is made of | `make e2e`: fixtures in, rows out through the views, poison in the DLQ |
| `terraform static checks` | `infra/terraform/`, `scripts/ci/`, `docs/architecture.md` | fmt, validate, plan-guard self-test |
| `terraform plan (wif)` | same, and only with the GCP variables set | an authenticated plan, guarded |

Each path filter covers the job's *inputs*, not just its own directory. A fixture
change is a change to what the collector's byte-identity test and the golden files
assert, so it has to run them; a filter that misses its inputs is the skipped-and-green
failure this file already warns about further down.

Posture (F0 spec §W6.1, §W6.3):

- Triggered by `pull_request`, never `pull_request_target`. Gate D fails the
  build if that trigger ever appears in this directory.
- Top-level permissions are `contents: read`. Only `terraform plan (wif)` raises
  `id-token: write`, and that job additionally refuses to run for a pull request
  from a fork.
- Third-party actions are pinned to commit SHAs with the tag in a comment. A
  moving tag is a supply-chain decision made by someone else.
- No exported service account key: GCP access is a short-lived token from
  Workload Identity Federation.
- Path filtering applies to pull requests only. On `main` every job runs, so
  "green on `main`" means every job actually ran — a job whose configuration is
  broken would otherwise stay skipped and green until the phase that finally
  touches its directory.
- `terraform plan (wif)` stays skipped until the GCP repository variables exist.
  A skipped job proves nothing, which is why F0 acceptance criterion 8 is tied to
  a specific authenticated run recorded in the completion note.

- The end-to-end job runs on **every** pull request that touches the pipeline, not on
  `main` only. Actions minutes are unmetered on public repositories, and in F1 this job
  is the only place the compose path is exercised at all — the phase's development host
  cannot run containers — so a check deferred to `main` would report a pipeline
  regression to somebody who no longer has the change in front of them. Reasoning and
  measured runtime: `docs/specs/F1-decision-log.md` W6.4.

## `deploy.yml` — the gated apply path (F2 spec §2, decision D1)

| Job | Runs when | What it proves |
| --- | --- | --- |
| `preflight` | every dispatch | the ref is `main`, the GCP variables exist, and the `gcp-production` environment really carries a required reviewer |
| `plan` | after preflight | an authenticated plan, guarded, with the diff in the log and a fingerprint of it in the summary |
| `apply` | after the environment approval | the diff still matches what was approved, it applies, and the plan is clean afterwards |

Four properties are worth stating because each was a choice:

- **`workflow_dispatch` only.** Lane A authorizes self-merge, so a workflow that deployed
  on merge would turn every self-merge into a cloud mutation. A wave is armed by a person
  naming the wave and its issue.
- **Nothing is uploaded.** This repository is public and workflow artifacts are not masked
  the way logs are, so a plan file would publish every value it carries, including the
  billing account ID this repository keeps as a secret. The plan file never leaves the
  runner, and the approval is bound to the diff by a fingerprint — sorted `address action`
  pairs, hashed — which carries no attribute values at all.
- **The apply refuses a diff the reviewer did not see.** It re-plans, recomputes the
  fingerprint, and stops if it moved. Re-dispatching produces a fresh diff and a fresh
  approval; that is the correct response to a moved plan, not an obstacle to route around.
- **The environment check is load-bearing, and is proven able to fail.** Naming an
  environment that does not exist creates it on first use *without* protection rules, so
  the gate this whole workflow is built around would silently not be there. `preflight`
  refuses when it cannot see a required reviewer — including when it cannot read the
  environment at all, because an unverified gate is not a gate. The assertions live in
  `scripts/ci/environment-guard.sh` and run against six fixtures in the `invariant gates`
  job on every CI run: once the environment is configured correctly the check passes
  forever, so the only place it can be observed failing is against a fixture.

Branch protection requires `ci complete` only — see
`docs/runbooks/branch-protection.md` for why the aggregate exists and how to
recover if a broken workflow file deadlocks `main`.
