# infra/terraform

Terraform for the F0 footprint only: remote state, provider pinning, the billing
kill-switch chain, and the project-level BigQuery query quota. Application
infrastructure — Pub/Sub `traces`, BigQuery dataset and tables, Firestore, the
three Cloud Run services — is F2 and is deliberately absent here.

Every GCP resource in this project is Terraform-owned; nothing is hand-created
and drift is a bug (architecture §8). Resource types are restricted to the
allowlist in architecture §7.1, mechanically enforced by
`scripts/ci/terraform-plan-guard.sh`.

## Layout

| Path | Purpose |
| --- | --- |
| `bootstrap/` | Creates the GCS state bucket. Local state, run once. |
| `*.tf` | Root module: APIs, kill-switch chain, quota. GCS backend. |
| `../functions/billing-killswitch/` | Go source deployed by `killswitch.tf`. |

`bootstrap/` exists because the root module's backend is the bucket that
`bootstrap/` creates; a module cannot store its state in a bucket it has not made
yet. Its own state is local and disposable: the module describes one bucket and
re-running it against an existing bucket is a no-op after `terraform import`, or
simply unnecessary — the bucket is never destroyed.

## First run

Prerequisites are human-only (F0 spec W4): the GCP project exists, billing is
linked, and the operator holds Billing Account Administrator on the billing
account (the budget is a billing-account-level resource) plus Owner or equivalent
on the project.

```bash
cd infra/terraform/bootstrap
terraform init
terraform apply -var project_id=PROJECT_ID

cd ..
cp backend.hcl.example backend.hcl        # fill in the bucket name
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform plan -out plan.tfplan
../../scripts/ci/terraform-plan-guard.sh infra/terraform/plan.tfplan
terraform apply plan.tfplan
```

**The guard's argument is relative to the repository root, not to this
directory.** It runs `cd "$(git rev-parse --show-toplevel)"` before resolving the
path — it has to, because it parses the allowlist out of `docs/architecture.md`
§7.1 — so a bare `plan.tfplan` from here does not resolve and the guard refuses
with `no such plan file: plan.tfplan`. That message names the file rather than
the reason, so it reads like a missing artefact rather than a wrong invocation.
It is the same form `.github/workflows/deploy.yml` uses. This line said
`plan.tfplan` until 2026-09-05, and on that day the guard was skipped on a real
apply because of it — `docs/evidence/f2-killswitch-grpc-1831-redeploy-2026-09-05.md`.

`terraform.tfvars` and `backend.hcl` are gitignored: they are environment
specific, not secret.

Then run the kill-switch live-fire — the F0 acceptance criterion that cannot be
satisfied on paper: `docs/runbooks/kill-switch.md`.

## After the first apply — wiring CI to the project

The `terraform plan (wif)` job in `.github/workflows/ci.yml` skips until these
exist. Set them from the module's own outputs, so the values are read rather than
retyped:

```bash
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$(terraform output -raw workload_identity_provider)"
gh variable set GCP_CI_SERVICE_ACCOUNT         --body "$(terraform output -raw ci_service_account)"
gh variable set GCP_PROJECT_ID                 --body "$(terraform output -raw project_id)"
gh variable set GCP_STATE_BUCKET               --body "$(terraform output -raw state_bucket)"
gh secret   set GCP_BILLING_ACCOUNT_ID         --body "<billing account id>"
```

The billing account ID is a secret rather than a variable — not because it is a
credential, it is not, but because a workflow log is a public artifact on a public
repository and there is no reason to publish an account identifier in one.

Then re-run CI on `main` and confirm the plan job runs instead of skipping. **A
skipped job is not a passing job**: F0 acceptance criterion 8 is closed by a run
that actually authenticated.

## Pinning

`.terraform.lock.hcl` is committed in both modules. It records the registry's
signed `zh:` checksums, which cover every published platform, so Linux CI and a
macOS maintainer verify the same packages against the same hashes. Upgrading a
provider is a deliberate `terraform init -upgrade` with the lock diff in the pull
request — never a deleted lock file.
