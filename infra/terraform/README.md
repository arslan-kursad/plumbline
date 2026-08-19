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
../../scripts/ci/terraform-plan-guard.sh plan.tfplan
terraform apply plan.tfplan
```

`terraform.tfvars` and `backend.hcl` are gitignored: they are environment
specific, not secret.

Then run the kill-switch live-fire — the F0 acceptance criterion that cannot be
satisfied on paper: `docs/runbooks/kill-switch.md`.

## Pinning

`.terraform.lock.hcl` is committed in both modules. It records the registry's
signed `zh:` checksums, which cover every published platform, so Linux CI and a
macOS maintainer verify the same packages against the same hashes. Upgrading a
provider is a deliberate `terraform init -upgrade` with the lock diff in the pull
request — never a deleted lock file.
